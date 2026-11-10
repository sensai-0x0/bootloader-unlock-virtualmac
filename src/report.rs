//! `report` — write the reproducible, hash-chained evidence bundle.
//!
//! Shape matches `spec/build-spec.md`'s `Report` interface contract and
//! `spec/contract-spec.md`'s `ValidReport`/`EvidenceComplete`. `write_bundle` is the only
//! writer; it never omits raw outputs or tool versions (the state/collect module already
//! captures those into `BootState.evidence.raw_outputs`, which this module persists
//! verbatim).

use crate::state::BootState;
use crate::state::diff::DiffEntry;
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::fs;
use std::io::Write;
use std::path::{Path, PathBuf};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct InvariantResult {
    pub name: String,
    pub held: bool,
    pub detail: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Report {
    pub schema_version: u32,
    pub session_id: String,
    pub baseline: BootState,
    /// `None` iff the session was evaluate-only.
    pub result: Option<BootState>,
    pub diff: Vec<DiffEntry>,
    pub invariants: Vec<InvariantResult>,
    pub exit_code: i32,
}

#[derive(Debug, thiserror::Error)]
pub enum ReportError {
    #[error("exit_code is 0 but at least one invariant did not hold: {0}")]
    InvalidZeroExitWithFailedInvariant(String),
    #[error(
        "session_id `{0}` must be 1-{MAX_SESSION_ID_LEN} characters of [A-Za-z0-9_-] \
         (it becomes a directory name)"
    )]
    InvalidSessionId(String),
    #[error(transparent)]
    Io(#[from] std::io::Error),
    #[error(transparent)]
    Json(#[from] serde_json::Error),
}

const MAX_SESSION_ID_LEN: usize = 64;

/// `session_id` is joined onto `out_dir`; without this, `../x` or an absolute path would
/// write outside it (offensive-robustness report, F11).
fn validate_session_id(id: &str) -> Result<(), ReportError> {
    let ok = (1..=MAX_SESSION_ID_LEN).contains(&id.len())
        && id
            .bytes()
            .all(|b| b.is_ascii_alphanumeric() || b == b'_' || b == b'-');
    if ok {
        Ok(())
    } else {
        Err(ReportError::InvalidSessionId(id.to_string()))
    }
}

/// `ValidReport(r)` from `spec/contract-spec.md`: if `exit_code == 0` then every
/// `invariants[].held == true`. A `Report` with `exit_code == 0` but any `held == false` is
/// itself invalid — treated as `InvariantViolated`, not written as a passing report.
pub fn validate(report: &Report) -> Result<(), ReportError> {
    if report.exit_code == 0
        && let Some(failed) = report.invariants.iter().find(|i| !i.held)
    {
        return Err(ReportError::InvalidZeroExitWithFailedInvariant(
            failed.name.clone(),
        ));
    }
    Ok(())
}

/// Write `report` as a hash-chained evidence bundle under `out_dir/<session_id>/`.
///
/// Bundle layout: `report.json` (the full [`Report`], pretty-printed for human review) and
/// `report.sha256` (the hex sha256 of `report.json`'s bytes, so tampering with the report
/// after the fact is detectable). This is a minimal first cut of `EvidenceComplete` — P3
/// onward will extend it with one file per raw command capture as sessions start producing
/// more of them than `BootState.evidence.raw_outputs` alone.
pub fn write_bundle(report: &Report, out_dir: &Path) -> Result<PathBuf, ReportError> {
    validate(report)?;
    validate_session_id(&report.session_id)?;

    // `create_dir` (not `_all`) for the session itself: an existing bundle is never
    // overwritten, and the directory is known to be one this call just made.
    fs::create_dir_all(out_dir)?;
    let session_dir = out_dir.join(&report.session_id);
    fs::create_dir(&session_dir)?;

    let json = serde_json::to_vec_pretty(report)?;
    write_new(&session_dir.join("report.json"), &json)?;

    let hash = hex::encode(Sha256::digest(&json));
    write_new(&session_dir.join("report.sha256"), hash.as_bytes())?;

    Ok(session_dir)
}

fn write_new(path: &Path, bytes: &[u8]) -> Result<(), ReportError> {
    let mut f = fs::OpenOptions::new()
        .write(true)
        .create_new(true)
        .open(path)?;
    f.write_all(bytes)?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::env::Environment;
    use crate::state::{
        Evidence, Host, PostureConfidence, SCHEMA_VERSION, SecurityMode, TargetContainer,
    };

    fn sample_baseline() -> BootState {
        BootState {
            schema_version: SCHEMA_VERSION,
            captured_at: "2026-01-01T00:00:00Z".to_string(),
            environment: Environment::MacOs,
            posture_confidence: PostureConfidence::Unmeasured,
            host: Host {
                chip: "Apple M2 Pro".to_string(),
                macos_build: "24A335".to_string(),
                serial_masked: "WXYZ".to_string(),
            },
            target_container: TargetContainer {
                volume_group_uuid: "AAAA".to_string(),
                security_mode: SecurityMode::Full,
                ssv_enabled: true,
                allows_custom_kernel: false,
                allows_third_party_kexts: false,
            },
            enrolled_objects: vec![],
            other_containers: vec![],
            evidence: Evidence::default(),
        }
    }

    #[test]
    fn zero_exit_with_failed_invariant_is_rejected() {
        let report = Report {
            schema_version: 1,
            session_id: "s1".to_string(),
            baseline: sample_baseline(),
            result: None,
            diff: vec![],
            invariants: vec![InvariantResult {
                name: "SingleContainerTouched".to_string(),
                held: false,
                detail: "two containers differed".to_string(),
            }],
            exit_code: 0,
        };
        assert!(matches!(
            validate(&report),
            Err(ReportError::InvalidZeroExitWithFailedInvariant(_))
        ));
    }

    #[test]
    fn write_bundle_produces_report_json_and_hash() {
        let dir = tempfile::tempdir().unwrap();
        let report = Report {
            schema_version: 1,
            session_id: "test-session".to_string(),
            baseline: sample_baseline(),
            result: None,
            diff: vec![],
            invariants: vec![],
            exit_code: 0,
        };
        let bundle_path = write_bundle(&report, dir.path()).unwrap();
        assert!(bundle_path.join("report.json").exists());
        assert!(bundle_path.join("report.sha256").exists());

        let json = fs::read(bundle_path.join("report.json")).unwrap();
        let expected_hash = hex::encode(Sha256::digest(&json));
        let stored_hash = fs::read_to_string(bundle_path.join("report.sha256")).unwrap();
        assert_eq!(stored_hash, expected_hash);
    }

    fn report_with_id(id: &str) -> Report {
        Report {
            schema_version: 1,
            session_id: id.to_string(),
            baseline: sample_baseline(),
            result: None,
            diff: vec![],
            invariants: vec![],
            exit_code: 0,
        }
    }

    #[test]
    fn traversal_and_absolute_session_ids_are_refused() {
        let dir = tempfile::tempdir().unwrap();
        for bad in [
            "../escape",
            "/abs/path",
            "a/b",
            "",
            ".",
            "..",
            &"x".repeat(65),
        ] {
            assert!(
                matches!(
                    write_bundle(&report_with_id(bad), dir.path()),
                    Err(ReportError::InvalidSessionId(_))
                ),
                "session_id {bad:?} should be refused"
            );
        }
    }

    #[test]
    fn an_existing_bundle_is_never_overwritten() {
        let dir = tempfile::tempdir().unwrap();
        write_bundle(&report_with_id("once"), dir.path()).unwrap();
        let second = write_bundle(&report_with_id("once"), dir.path());
        assert!(matches!(second, Err(ReportError::Io(_))));
    }
}
