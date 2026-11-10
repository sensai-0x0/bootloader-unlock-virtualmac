//! bputil-eval CLI entry point.
//!
//! Subcommand -> module mapping and exit codes follow `spec/build-spec.md`'s "Interface
//! contracts" table. `apply`, `verify`, and `revert` are P3/P4 work (not built in this pass —
//! see `spec/phased-plan.md`) and exist here only as honest stubs that say so, rather than
//! being silently absent from the CLI surface the spec defines.

mod authorize;
mod env;
mod execute;
mod plan;
mod report;
mod state;
mod verify;
mod wrapper;

use clap::{Parser, Subcommand};
use plan::TargetProfile;
use std::path::PathBuf;
use std::process::ExitCode;

/// Exit codes from `spec/build-spec.md`'s "Exit codes" section.
mod exit_code {
    pub const OK: u8 = 0;
    pub const PARSE_ERROR: u8 = 11;
    /// `verify` only: the fresh measurement differs from the baseline. Deliberately not
    /// 13 (`InvariantViolated`): that code means "a transition this tool performed broke
    /// an invariant — halt and disclose", whereas read-only drift is a detection finding
    /// to triage. Follows the diff(1)/cmp(1) convention: 1 = differences found.
    pub const DRIFT_DETECTED: u8 = 1;
    /// `verify` only: no drift was found, but the fresh read was not fully measured
    /// (e.g. no cached sudo, so `security_mode` is Unknown) — "no drift" would overclaim.
    pub const INCONCLUSIVE: u8 = 2;
}

/// Upper bound on a `verify --baseline <path>` input before it's even read into memory.
/// `cmd_verify` deserializes this file into a `BootState`, which this binary did not
/// necessarily produce itself (`vuln_res/AUDIT.md` §1.2) — e.g. a baseline someone emailed
/// you, or one fetched as part of an automated pipeline. A real `BootState` is a few KB at
/// most; 1 MiB is generous headroom while still bounding the memory a hostile, very large
/// (not necessarily deeply nested) JSON array could otherwise force this process to
/// allocate before `serde_json` ever gets a chance to reject it.
const MAX_BASELINE_FILE_BYTES: u64 = 1024 * 1024;

#[derive(Parser)]
#[command(
    name = "bputil-eval",
    version,
    about = "Boot-policy evaluation and owner-authorised unlock tool"
)]
struct Cli {
    #[command(subcommand)]
    command: Command,
}

#[derive(Subcommand)]
enum Command {
    /// Measure the current boot-chain trust state. Never mutates.
    Evaluate {
        #[arg(long)]
        json: bool,
    },
    /// Diff the current state against a target profile and print the resulting plan. Never mutates.
    Plan {
        #[arg(value_enum)]
        target: CliTargetProfile,
        #[arg(long)]
        json: bool,
    },
    /// Write the evidence bundle for a completed session.
    Report {
        #[arg(long, default_value = "./evidence")]
        out_dir: PathBuf,
        #[arg(long)]
        session_id: Option<String>,
    },
    /// Diff a baseline BootState (JSON, from a prior `evaluate --json`) against a fresh
    /// measurement. Read-only. Exit 0 = no drift on a measured read, 1 = drift,
    /// 2 = no drift but the fresh read was not fully measured, 11 = bad/foreign baseline. Full invariant assertion (`verify.assert_invariants` against
    /// an actual mutation) is P3 work; this subcommand only exercises the structural diff.
    Verify {
        #[arg(long)]
        baseline: PathBuf,
        #[arg(long)]
        json: bool,
    },
    /// P3: mutating, 1TR-only. Not implemented in this build.
    Apply,
    /// P3: mutating, 1TR-only. Not implemented in this build.
    Revert,
}

#[derive(Clone, clap::ValueEnum)]
enum CliTargetProfile {
    Full,
    ReducedKexts,
    PermissiveCustomKernel,
}

impl From<CliTargetProfile> for TargetProfile {
    fn from(value: CliTargetProfile) -> Self {
        match value {
            CliTargetProfile::Full => TargetProfile::Full,
            CliTargetProfile::ReducedKexts => TargetProfile::ReducedKexts,
            CliTargetProfile::PermissiveCustomKernel => TargetProfile::PermissiveCustomKernel,
        }
    }
}

fn main() -> ExitCode {
    let cli = Cli::parse();
    match cli.command {
        Command::Evaluate { json } => cmd_evaluate(json),
        Command::Plan { target, json } => cmd_plan(target.into(), json),
        Command::Report {
            out_dir,
            session_id,
        } => cmd_report(out_dir, session_id),
        Command::Verify { baseline, json } => cmd_verify(baseline, json),
        Command::Apply | Command::Revert => {
            eprintln!(
                "not implemented: mutating subcommands require the P3/P4 authorize/execute/verify \
                 pipeline, which is not part of this build (see spec/phased-plan.md)."
            );
            ExitCode::FAILURE
        }
    }
}

fn cmd_evaluate(json: bool) -> ExitCode {
    match state::collect::collect() {
        Ok(boot_state) => {
            if json {
                match serde_json::to_string_pretty(&boot_state) {
                    Ok(s) => println!("{s}"),
                    Err(e) => {
                        eprintln!("failed to serialise BootState: {e}");
                        return ExitCode::from(exit_code::PARSE_ERROR);
                    }
                }
            } else {
                println!("{boot_state:#?}");
                // Informational only — never part of the BootState schema. Derived fresh,
                // per env::is_mutation_allowed()'s contract.
                println!(
                    "\nmutation_allowed (live, this call): {}",
                    env::is_mutation_allowed()
                );
            }
            ExitCode::from(exit_code::OK)
        }
        Err(e) => {
            eprintln!("evaluate failed: {e}");
            ExitCode::from(exit_code::PARSE_ERROR)
        }
    }
}

fn cmd_plan(target: TargetProfile, json: bool) -> ExitCode {
    let baseline = match state::collect::collect() {
        Ok(b) => b,
        Err(e) => {
            eprintln!("could not establish a baseline to plan against: {e}");
            return ExitCode::from(exit_code::PARSE_ERROR);
        }
    };

    match plan::plan(&baseline, target) {
        Ok(planned) => {
            if json {
                println!("{}", serde_json::to_string_pretty(&planned).unwrap());
            } else {
                println!("{planned:#?}");
            }
            ExitCode::from(exit_code::OK)
        }
        Err(e) => {
            eprintln!("plan refused: {e}");
            ExitCode::from(exit_code::PARSE_ERROR)
        }
    }
}

fn cmd_verify(baseline_path: PathBuf, json: bool) -> ExitCode {
    let baseline = match load_baseline(&baseline_path) {
        Ok(b) => b,
        Err(e) => {
            eprintln!("{e}");
            return ExitCode::from(exit_code::PARSE_ERROR);
        }
    };

    let fresh = match state::collect::collect() {
        Ok(b) => b,
        Err(e) => {
            eprintln!("could not collect a fresh BootState to verify against: {e}");
            return ExitCode::from(exit_code::PARSE_ERROR);
        }
    };

    if let Err(e) = check_same_host(&baseline, &fresh) {
        eprintln!("refusing to compare: {e}");
        return ExitCode::from(exit_code::PARSE_ERROR);
    }

    let diff = state::diff::diff(&baseline, &fresh);
    let outcome = verify_outcome(&diff, &fresh);
    let rpt = report::Report {
        schema_version: state::SCHEMA_VERSION,
        session_id: format!(
            "verify-{}",
            time::OffsetDateTime::now_utc().unix_timestamp()
        ),
        baseline,
        result: Some(fresh),
        diff,
        // Full global-invariant assertion against a real transition is P3
        // (execute/verify.assert_invariants); this subcommand only proves the diff shape.
        invariants: vec![],
        exit_code: i32::from(outcome),
    };

    if json {
        println!("{}", serde_json::to_string_pretty(&rpt).unwrap());
    } else {
        println!("{} field(s) differ from baseline:", rpt.diff.len());
        for entry in &rpt.diff {
            println!("  {}: {} -> {}", entry.path, entry.before, entry.after);
        }
        if outcome == exit_code::INCONCLUSIVE {
            println!(
                "inconclusive: fresh posture_confidence is {:?}, not Measured",
                rpt.result.as_ref().map(|r| r.posture_confidence)
            );
        }
    }
    ExitCode::from(outcome)
}

/// Read, bound, parse and validate an untrusted baseline file. A baseline is input this
/// binary may not have produced (`vuln_res/AUDIT.md` §1.2), so it gets the same validity
/// predicate as a fresh measurement plus a schema-version check — a baseline claiming a
/// state `collect()` could never produce must not anchor a "no drift" verdict (F12, F13).
fn load_baseline(path: &std::path::Path) -> Result<state::BootState, String> {
    let shown = path.display();
    let meta =
        std::fs::metadata(path).map_err(|e| format!("could not stat baseline {shown}: {e}"))?;
    if meta.len() > MAX_BASELINE_FILE_BYTES {
        return Err(format!(
            "baseline {shown} is {} bytes, over the {MAX_BASELINE_FILE_BYTES}-byte limit for a \
             BootState file; refusing to read it",
            meta.len()
        ));
    }
    let text = std::fs::read_to_string(path)
        .map_err(|e| format!("could not read baseline {shown}: {e}"))?;
    let baseline: state::BootState = serde_json::from_str(&text)
        .map_err(|e| format!("baseline {shown} is not a valid BootState: {e}"))?;
    if baseline.schema_version != state::SCHEMA_VERSION {
        return Err(format!(
            "baseline {shown} has schema_version {}, this build reads only {}",
            baseline.schema_version,
            state::SCHEMA_VERSION
        ));
    }
    state::validate(&baseline)
        .map_err(|e| format!("baseline {shown} fails the BootState validity predicate: {e}"))?;
    Ok(baseline)
}

/// A baseline from another machine or another volume group says nothing about this one;
/// comparing against it would let a clean foreign baseline mask local drift (F14).
fn check_same_host(baseline: &state::BootState, fresh: &state::BootState) -> Result<(), String> {
    let pairs = [
        (
            "host.serial_masked",
            &baseline.host.serial_masked,
            &fresh.host.serial_masked,
        ),
        ("host.chip", &baseline.host.chip, &fresh.host.chip),
        (
            "target_container.volume_group_uuid",
            &baseline.target_container.volume_group_uuid,
            &fresh.target_container.volume_group_uuid,
        ),
    ];
    match pairs.iter().find(|(_, b, f)| b != f) {
        Some((field, b, f)) => Err(format!(
            "baseline was captured on a different host/container ({field}: {b} vs {f})"
        )),
        None => Ok(()),
    }
}

fn verify_outcome(diff: &[state::diff::DiffEntry], fresh: &state::BootState) -> u8 {
    if !diff.is_empty() {
        exit_code::DRIFT_DETECTED
    } else if fresh.posture_confidence != state::PostureConfidence::Measured {
        exit_code::INCONCLUSIVE
    } else {
        exit_code::OK
    }
}

fn cmd_report(out_dir: PathBuf, session_id: Option<String>) -> ExitCode {
    let baseline = match state::collect::collect() {
        Ok(b) => b,
        Err(e) => {
            eprintln!("could not collect a BootState for this report: {e}");
            return ExitCode::from(exit_code::PARSE_ERROR);
        }
    };

    let session_id = session_id
        .unwrap_or_else(|| format!("eval-{}", time::OffsetDateTime::now_utc().unix_timestamp()));

    let rpt = report::Report {
        schema_version: state::SCHEMA_VERSION,
        session_id,
        baseline,
        result: None,
        diff: vec![],
        invariants: vec![],
        exit_code: 0,
    };

    match report::write_bundle(&rpt, &out_dir) {
        Ok(path) => {
            println!("{}", path.display());
            ExitCode::from(exit_code::OK)
        }
        Err(e) => {
            eprintln!("could not write evidence bundle: {e}");
            ExitCode::from(exit_code::PARSE_ERROR)
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::io::Write;

    // vuln_res/AUDIT.md §1.2: `verify --baseline <path>` deserializes a file this binary
    // didn't necessarily produce itself, with no size cap before `serde_json` ever sees it —
    // a cheap local DoS vector (large-allocation) against a baseline file from an untrusted
    // source. This proves the size guard actually rejects an oversized file before any JSON
    // parsing is attempted, rather than just trusting the constant exists.
    #[test]
    fn oversized_baseline_file_is_rejected_before_parsing() {
        let dir = tempfile::tempdir().unwrap();
        let path = dir.path().join("huge_baseline.json");
        let mut f = std::fs::File::create(&path).unwrap();
        // Deliberately not valid JSON — if the size guard didn't fire first, this would
        // fail with a JSON parse error instead, which the exit code alone can't
        // distinguish from a correctly-functioning size guard. The content itself doesn't
        // matter; only that it's never read past the metadata check.
        let chunk = vec![b'a'; 4096];
        let chunks_needed = (MAX_BASELINE_FILE_BYTES as usize / chunk.len()) + 1;
        for _ in 0..chunks_needed {
            f.write_all(&chunk).unwrap();
        }
        drop(f);
        assert!(std::fs::metadata(&path).unwrap().len() > MAX_BASELINE_FILE_BYTES);

        let result = cmd_verify(path, false);
        assert_eq!(result, ExitCode::from(exit_code::PARSE_ERROR));
    }

    #[test]
    fn missing_baseline_file_is_a_clean_error_not_a_panic() {
        let result = cmd_verify(
            PathBuf::from("/nonexistent/path/does-not-exist.json"),
            false,
        );
        assert_eq!(result, ExitCode::from(exit_code::PARSE_ERROR));
    }

    fn write_baseline(dir: &std::path::Path, value: &serde_json::Value) -> PathBuf {
        let path = dir.join("baseline.json");
        std::fs::write(&path, serde_json::to_vec(value).unwrap()).unwrap();
        path
    }

    fn good_baseline_json() -> serde_json::Value {
        serde_json::json!({
            "schema_version": 1,
            "captured_at": "2026-01-01T00:00:00Z",
            "environment": "MacOs",
            "posture_confidence": "Measured",
            "host": { "chip": "Apple M2 Pro", "macos_build": "24A335", "serial_masked": "WXYZ" },
            "target_container": {
                "volume_group_uuid": "AAAA", "security_mode": "Full", "ssv_enabled": true,
                "allows_custom_kernel": false, "allows_third_party_kexts": false
            },
            "enrolled_objects": [],
            "other_containers": [],
            "evidence": { "raw_outputs": [] }
        })
    }

    #[test]
    fn a_well_formed_baseline_loads() {
        let dir = tempfile::tempdir().unwrap();
        assert!(load_baseline(&write_baseline(dir.path(), &good_baseline_json())).is_ok());
    }

    #[test]
    fn committed_evidence_baseline_still_loads() {
        // A real baseline from the VM round trip must survive the stricter loader.
        let rel = "evidence/vm-sec-research-25D125/baseline_reduced.json";
        let path = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join(rel);
        if let Err(e) = load_baseline(&path) {
            panic!("{rel}: {e}");
        }
    }

    #[test]
    fn baseline_failing_the_validity_predicate_is_refused() {
        let dir = tempfile::tempdir().unwrap();
        let mut v = good_baseline_json();
        v["target_container"]["security_mode"] = "Permissive".into(); // with SSV on
        assert!(load_baseline(&write_baseline(dir.path(), &v)).is_err());
        let mut v = good_baseline_json();
        v["captured_at"] = "2999-01-01T00:00:00Z".into();
        assert!(load_baseline(&write_baseline(dir.path(), &v)).is_err());
    }

    #[test]
    fn baseline_with_foreign_schema_version_is_refused() {
        let dir = tempfile::tempdir().unwrap();
        let mut v = good_baseline_json();
        v["schema_version"] = 999.into();
        let err = load_baseline(&write_baseline(dir.path(), &v)).unwrap_err();
        assert!(err.contains("schema_version"), "{err}");
    }

    #[test]
    fn baseline_with_unknown_fields_is_refused() {
        let dir = tempfile::tempdir().unwrap();
        let mut v = good_baseline_json();
        v["verdict"] = "trust me".into();
        assert!(load_baseline(&write_baseline(dir.path(), &v)).is_err());
    }

    fn parsed(v: serde_json::Value) -> state::BootState {
        serde_json::from_value(v).unwrap()
    }

    #[test]
    fn baseline_from_another_host_or_container_is_refused() {
        let fresh = parsed(good_baseline_json());
        for (ptr, val) in [
            ("/host/serial_masked", "ABCD"),
            ("/host/chip", "Apple M1"),
            ("/target_container/volume_group_uuid", "BBBB"),
        ] {
            let mut v = good_baseline_json();
            *v.pointer_mut(ptr).unwrap() = val.into();
            assert!(check_same_host(&parsed(v), &fresh).is_err(), "{ptr}");
        }
        assert!(check_same_host(&fresh, &fresh).is_ok());
    }

    #[test]
    fn verify_outcome_distinguishes_ok_drift_and_inconclusive() {
        let measured = parsed(good_baseline_json());
        assert_eq!(verify_outcome(&[], &measured), exit_code::OK);

        let mut v = good_baseline_json();
        v["posture_confidence"] = "UntrustedRead".into();
        assert_eq!(verify_outcome(&[], &parsed(v)), exit_code::INCONCLUSIVE);

        let drift = [state::diff::DiffEntry {
            path: "target_container.security_mode".into(),
            before: "Full".into(),
            after: "Reduced".into(),
        }];
        assert_eq!(verify_outcome(&drift, &measured), exit_code::DRIFT_DETECTED);
    }
}
