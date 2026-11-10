//! The single audited command wrapper.
//!
//! Per `spec/build-spec.md` ("Tech constraints") and `spec/phased-plan.md` (P0 exit gate),
//! this is the *only* place in the codebase allowed to call `std::process::Command`. Every
//! other module reaches a subprocess through [`run`], which always records argv, exit code,
//! and a hash of stdout+stderr, win or lose. CI greps the rest of `src/` for
//! `std::process::Command` and fails the build if it finds one outside this file.

use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::process::Command;

/// The outcome of a single audited invocation. Every field here ends up in the evidence
/// bundle (`spec/contract-spec.md`'s `EvidenceComplete` invariant: "every invoked command,
/// its exit code and output hash").
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct CommandRecord {
    pub argv: Vec<String>,
    pub exit_code: i32,
    pub stdout: String,
    pub stderr: String,
    /// sha256 of stdout, hex-encoded. `contract-spec.md`'s `evidence.raw_outputs[]` constraint.
    pub stdout_sha256: String,
}

/// Errors from trying to launch a process at all (binary missing, no permission, etc.),
/// as distinct from the process running and returning a non-zero exit code — that is a
/// normal [`CommandRecord`] with `exit_code != 0`, not an [`Err`].
#[derive(Debug, thiserror::Error)]
pub enum WrapperError {
    #[error("failed to spawn {argv0}: {source}")]
    Spawn {
        argv0: String,
        #[source]
        source: std::io::Error,
    },
}

/// Run `argv` to completion and return a full [`CommandRecord`].
///
/// This never panics on a non-zero exit — a mutating caller (`execute::run`) decides what a
/// non-zero exit means for its `PlannedTransition`; this function only observes and records.
pub fn run(argv: &[&str]) -> Result<CommandRecord, WrapperError> {
    let argv0 = argv.first().copied().unwrap_or_default();
    let output = Command::new(argv0)
        .args(&argv[1..])
        .output()
        .map_err(|source| WrapperError::Spawn {
            argv0: argv0.to_string(),
            source,
        })?;

    let stdout = String::from_utf8_lossy(&output.stdout).into_owned();
    let stderr = String::from_utf8_lossy(&output.stderr).into_owned();
    let stdout_sha256 = hex::encode(Sha256::digest(&output.stdout));

    Ok(CommandRecord {
        argv: argv.iter().map(|s| s.to_string()).collect(),
        exit_code: output.status.code().unwrap_or(-1),
        stdout,
        stderr,
        stdout_sha256,
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn records_argv_exit_code_and_hash() {
        let record = run(&["echo", "-n", "hello"]).expect("echo should spawn");
        assert_eq!(record.argv, vec!["echo", "-n", "hello"]);
        assert_eq!(record.exit_code, 0);
        assert_eq!(record.stdout, "hello");
        assert_eq!(record.stdout_sha256, hex::encode(Sha256::digest(b"hello")));
    }

    #[test]
    fn records_nonzero_exit_without_erroring() {
        // `false` always exits 1; the wrapper must report this as data, not as an Err.
        let record = run(&["false"]).expect("false should spawn");
        assert_eq!(record.exit_code, 1);
    }

    #[test]
    fn spawn_failure_is_an_error_not_a_panic() {
        let result = run(&["this-binary-does-not-exist-anywhere-on-path"]);
        assert!(matches!(result, Err(WrapperError::Spawn { .. })));
    }

    #[test]
    fn hash_is_deterministic_for_same_output() {
        let a = run(&["echo", "-n", "deterministic"]).unwrap();
        let b = run(&["echo", "-n", "deterministic"]).unwrap();
        assert_eq!(a.stdout_sha256, b.stdout_sha256);
    }
}
