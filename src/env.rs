//! Environment detection: macOS vs One True Recovery (1TR), chip, and macOS build.
//!
//! [`is_mutation_allowed`] is the single gate `apply`/`execute`/`revert` MUST consult before
//! doing anything else (`spec/contract-spec.md`, `env.is_mutation_allowed()`). It is derived
//! fresh from the live system on every call — never cached across a reboot, never
//! overridable by a flag or environment variable (same doc, same section).
//!
//! Detection note (no companion architecture doc is present in this repo to specify the
//! exact mechanism, so this is a researched best-effort, not an invented guess — see
//! `CLAUDE.md`): `bputil -d` prints an "OS Type" line reading "one true recoveryOS" when
//! paired, or "ordinary recovery OS" in fallback recovery. Fallback recovery lacks Startup
//! Security Utility and is deliberately NOT treated as mutation-eligible here, even though
//! `spec/contract-spec.md`'s two-variant `Environment` enum doesn't name it: a state this
//! module can't positively confirm as `OneTrueRecovery` must fail closed, per golden rule 1
//! in `spec/build-spec.md` ("let a mutation proceed on an unknown environment" is the one
//! thing `env` must never do). This mechanism should be validated against real 1TR hardware
//! before P3 ships — a MacRumors forum report cited in research for this module suggests
//! `bputil -d`'s OS Type string has not been 100% consistent across OS builds.

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

    // No Finder.app => some minimal (Recovery/Installer-like) runtime. Apple's own tool is
    // the most direct signal for which kind, per `bputil`'s documented "OS Type" field.
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

    if os_type_line.to_lowercase().contains("one true recoveryos") {
        Ok(Environment::OneTrueRecovery)
    } else {
        Err(EnvError::UnconfirmedRecoveryVariant {
            detail: os_type_line.to_string(),
        })
    }
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
}
