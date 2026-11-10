//! Environment detection: macOS vs One True Recovery (1TR), chip, and macOS build.
//!
//! [`is_mutation_allowed`] is the single gate `apply`/`execute`/`revert` MUST consult before
//! doing anything else (`spec/contract-spec.md`, `env.is_mutation_allowed()`). It is derived
//! fresh from the live system on every call — never cached across a reboot, never
//! overridable by a flag or environment variable (same doc, same section).
//!
//! Detection note (no companion architecture doc is present in this repo to specify the
//! exact mechanism, so this was originally a researched best-effort, not an invented guess
//! — see `CLAUDE.md`): the fallback branch below was written expecting `bputil -d` to
//! print an "OS Type" line reading "one true recoveryOS" when paired, or "ordinary
//! recovery OS" in fallback recovery.
//!
//! **Confirmed wrong, not just speculative (`progress/milestones.md`'s 2026-11-10 M10
//! entry; `vuln_res/sweep-reports/` for the finding this was escalated from):** against
//! real `bputil` v0.1.14, the "OS Type" line reads `"macOS (overriden)"` in every captured
//! state this project has ever measured — including inside a confirmed, paired 1TR-
//! equivalent recovery environment (verified independently via `whoami == root` and the
//! absence of `Finder.app`; see `tests/fixtures/bputil_d_permissive_VM_VIRTUALIZED.txt`,
//! captured from exactly that environment). It never once reads "one true recoveryOS". The
//! fallback branch below therefore cannot currently succeed at all: whenever
//! `finder_app_present()` is false, `detect()` always returns
//! `Err(UnconfirmedRecoveryVariant)`, meaning [`is_mutation_allowed`] is always `false` —
//! even inside genuine, owner-present 1TR.
//!
//! This fails closed (the safe direction — golden rule 1 in `spec/build-spec.md`: never let
//! a mutation proceed on an unknown environment), so nothing here is a security hole. But it
//! is a confirmed functional gap: as written, this module can never actually authorize a P3
//! mutation, on any real hardware or VM, regardless of who's present or how legitimate the
//! request is. **Deliberately not "fixed" by substituting a new guessed string** — this
//! project's own discipline (see every other parsing fix in `vuln_res/sweep-reports/`) is
//! "confirmed, not guessed," and no alternative distinguishing text has been confirmed yet.
//! What *is* confirmed working is the `finder_app_present()` primary check and the
//! `whoami`/`Finder.app` combination as an *independent* recovery-environment signal — but
//! that combination doesn't by itself distinguish paired 1TR from ordinary fallback
//! recovery, which was the fallback branch's whole job. Resolving this for real needs
//! either the still-missing companion architecture document, or deliberate research inside
//! a VM to capture what "OS Type" (or some other field) actually reads in a confirmed
//! *fallback* (non-paired) recovery environment, to find a real distinguishing signal
//! rather than inventing one. Blocks P3's `authorize`/`execute` from ever succeeding until
//! resolved — tracked as an escalated finding, not a silent gap.

use crate::wrapper::{self, WrapperError};
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum Environment {
    MacOs,
    OneTrueRecovery,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct Host {
    pub chip: String,
    pub macos_build: String,
}

#[derive(Debug, thiserror::Error)]
pub enum EnvError {
    #[error("could not launch a detection command: {0}")]
    Wrapper(#[from] WrapperError),
    #[error(
        "detected a recovery environment but could not confirm it is one true recoveryOS \
         (saw: {detail}); refusing to classify as either MacOs or OneTrueRecovery"
    )]
    UnconfirmedRecoveryVariant { detail: String },
    #[error("chip or macOS build could not be read: {0}")]
    HostFieldUnreadable(String),
}

/// Detect the live environment. Never cached, never takes a hint from the caller.
pub fn detect() -> Result<Environment, EnvError> {
    if finder_app_present() {
        return Ok(Environment::MacOs);
    }

    // No Finder.app => some minimal (Recovery/Installer-like) runtime. The fallback check
    // below is confirmed non-functional against real `bputil` v0.1.14 output — see this
    // module's doc comment for the evidence. Kept as written (rather than guessing a
    // replacement) because it still fails closed, which is the safe direction.
    let record = wrapper::run(&["bputil", "-d"])?;
    if record.exit_code != 0 {
        return Err(EnvError::UnconfirmedRecoveryVariant {
            detail: format!(
                "bputil -d exited {} (no Finder.app present)",
                record.exit_code
            ),
        });
    }

    let os_type_line = record
        .stdout
        .lines()
        .find(|line| line.contains("OS Type"))
        .unwrap_or("");

    if is_one_true_recovery_os_type_line(os_type_line) {
        Ok(Environment::OneTrueRecovery)
    } else {
        Err(EnvError::UnconfirmedRecoveryVariant {
            detail: os_type_line.to_string(),
        })
    }
}

/// The fallback-recovery-classification check, pulled out as a pure function so its
/// (currently confirmed non-functional — see this module's doc comment) behavior is
/// directly testable against real captured text, not just asserted in prose.
fn is_one_true_recovery_os_type_line(os_type_line: &str) -> bool {
    os_type_line.to_lowercase().contains("one true recoveryos")
}

/// True only if the live environment is confirmed `OneTrueRecovery`. Any detection failure,
/// including an environment we can't classify at all, yields `false` — never `true` on
/// doubt. Callers in `authorize`/`execute` MUST call this and abort on `false` before any
/// other work (`spec/contract-spec.md`, "contract for callers").
pub fn is_mutation_allowed() -> bool {
    matches!(detect(), Ok(Environment::OneTrueRecovery))
}

/// Chip identifier (e.g. "Apple M2 Pro") and the running macOS build (e.g. "24A335").
/// Read-only; used to select per-generation fixtures and to populate `BootState.host`.
pub fn host() -> Result<Host, EnvError> {
    let chip_record = wrapper::run(&["sysctl", "-n", "machdep.cpu.brand_string"])?;
    let build_record = wrapper::run(&["sw_vers", "-buildVersion"])?;

    let chip = chip_record.stdout.trim().to_string();
    let macos_build = build_record.stdout.trim().to_string();

    if chip.is_empty() {
        return Err(EnvError::HostFieldUnreadable(
            "chip (machdep.cpu.brand_string)".into(),
        ));
    }
    if macos_build.is_empty() {
        return Err(EnvError::HostFieldUnreadable(
            "macos_build (sw_vers -buildVersion)".into(),
        ));
    }

    Ok(Host { chip, macos_build })
}

fn finder_app_present() -> bool {
    std::path::Path::new("/System/Library/CoreServices/Finder.app").exists()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn mutation_not_allowed_when_detection_errors() {
        // We can't force a real detection error portably in a unit test without mocking the
        // wrapper (P3 will introduce a trait for that). What we *can* assert here: on this
        // CI/dev machine (ordinary macOS), is_mutation_allowed must be false.
        if finder_app_present() {
            assert!(!is_mutation_allowed());
        }
    }

    #[test]
    fn detect_returns_macos_when_finder_present() {
        if finder_app_present() {
            assert_eq!(detect().unwrap(), Environment::MacOs);
        }
    }

    // Confirmed-gap coverage (this module's doc comment; vuln_res/sweep-reports/). The
    // assertion below documents *current, confirmed-real* behavior, not desired behavior —
    // if this test ever starts failing because someone introduces a working distinguishing
    // signal, that's progress, and the doc comment above (and the corresponding vuln_res
    // finding) should be updated to say the gap is closed, not this test "fixed" back.
    #[test]
    fn real_os_type_line_from_a_confirmed_paired_1tr_environment_does_not_match() {
        // tests/fixtures/bputil_d_permissive_VM_VIRTUALIZED.txt was captured from a VM
        // environment independently confirmed to be paired 1TR recovery — via `whoami`
        // returning `root` with no login prompt, and the absence of
        // `/System/Library/CoreServices/Finder.app` — not inferred from this very check.
        // Its "OS Type" line nonetheless reads "macOS (overriden)", not "one true
        // recoveryOS": the fallback branch's assumed distinguishing string does not occur
        // here, even in the one case it most needs to.
        let fixture = include_str!("../tests/fixtures/bputil_d_permissive_VM_VIRTUALIZED.txt");
        let os_type_line = fixture
            .lines()
            .find(|line| line.contains("OS Type"))
            .expect("fixture has an OS Type line");
        assert!(
            !is_one_true_recovery_os_type_line(os_type_line),
            "if this now returns true, the confirmed-gap finding is stale — update the \
             module doc comment and vuln_res finding instead of leaving this assertion as \
             a silently-passing coincidence"
        );
    }
}
