//! The single audited command wrapper.
//!
//! Per `spec/build-spec.md` ("Tech constraints") and `spec/phased-plan.md` (P0 exit gate),
//! this is the *only* place in the codebase allowed to call `std::process::Command`. Every
//! other module reaches a subprocess through [`run`], which always records argv, exit code,
//! and a hash of stdout, win or lose. CI greps the rest of `src/` for
//! `std::process::Command` and fails the build if it finds one outside this file.
//!
//! Hardening (`reports/offensive-robustness-2026-11-11.md`, Tier 0 items 1–3):
//!
//! - **Pinned binaries.** Callers name a tool by its bare name (`"bputil"`); this module
//!   resolves it to a fixed absolute path from [`ALLOWED_BINARIES`] and refuses anything
//!   not listed. A `PATH` lookup would let any user-writable directory earlier on `PATH`
//!   shadow `/usr/bin/bputil` with a fake that prints `Security Mode: Full` — a forgery
//!   needing no privilege at all (finding F1). For `sudo`, the command it runs is pinned
//!   the same way, so `sudo`'s own `PATH` search can't be used either.
//! - **Clean environment.** The child gets `env_clear()` plus a fixed `PATH` and `LC_ALL=C`,
//!   so neither `DYLD_*` injection nor a non-English locale reaches Apple's tools, and their
//!   English-keyed output stays parseable (F2).
//! - **Bounded execution.** A deadline and a stdout/stderr byte cap, so a hung or hostile
//!   tool can't block `evaluate` forever or exhaust memory (F3).

use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::io::Read;
use std::process::{Command, Stdio};
use std::thread;
use std::time::{Duration, Instant};

/// The only binaries this tool may execute, as `(bare name, absolute path)`.
/// `scripts/ci_guards.sh` checks every `wrapper::run(&["<name>", ...])` call site in
/// `src/` names an entry here, so a new tool is a reviewed change to this table — never
/// a silent runtime `PATH` lookup.
pub const ALLOWED_BINARIES: &[(&str, &str)] = &[
    ("bputil", "/usr/bin/bputil"),
    ("csrutil", "/usr/bin/csrutil"),
    ("sudo", "/usr/bin/sudo"),
    ("diskutil", "/usr/sbin/diskutil"),
    ("system_profiler", "/usr/sbin/system_profiler"),
    ("sysctl", "/usr/sbin/sysctl"),
    ("sw_vers", "/usr/bin/sw_vers"),
];

/// Test-only additions (harmless, ubiquitous binaries used to exercise the wrapper itself).
#[cfg(test)]
const TEST_ONLY_BINARIES: &[(&str, &str)] = &[
    ("echo", "/bin/echo"),
    ("env", "/usr/bin/env"),
    ("false", "/usr/bin/false"),
    ("sleep", "/bin/sleep"),
    ("yes", "/usr/bin/yes"),
];

/// The fixed environment every child sees. Nothing is inherited from the caller.
const CHILD_PATH: &str = "/usr/bin:/bin:/usr/sbin:/sbin";
const CHILD_LOCALE: &str = "C";

/// Execution bounds for one invocation.
#[derive(Debug, Clone, Copy)]
pub struct Limits {
    pub timeout: Duration,
    /// Cap applied to stdout and to stderr independently.
    pub max_output_bytes: usize,
}

impl Default for Limits {
    /// Generous for every tool this crate runs (`system_profiler SPHardwareDataType`, the
    /// slowest, takes ~1s; a `bputil -d` dump is a few KB).
    fn default() -> Self {
        Self {
            timeout: Duration::from_secs(30),
            max_output_bytes: 1024 * 1024,
        }
    }
}

const POLL_INTERVAL: Duration = Duration::from_millis(10);

/// The outcome of a single audited invocation. Every field here ends up in the evidence
/// bundle (`spec/contract-spec.md`'s `EvidenceComplete` invariant: "every invoked command,
/// its exit code and output hash").
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct CommandRecord {
    /// The argv actually executed, with every pinned binary already resolved to its
    /// absolute path — the record names what ran, not what was asked for.
    pub argv: Vec<String>,
    pub exit_code: i32,
    pub stdout: String,
    pub stderr: String,
    /// sha256 of stdout, hex-encoded. `contract-spec.md`'s `evidence.raw_outputs[]` constraint.
    pub stdout_sha256: String,
}

/// Errors from trying to launch or bound a process, as distinct from the process running
/// and returning a non-zero exit code — that is a normal [`CommandRecord`] with
/// `exit_code != 0`, not an [`Err`].
#[derive(Debug, thiserror::Error)]
pub enum WrapperError {
    #[error("refusing to run `{0}`: not in the wrapper's pinned-binary allowlist")]
    NotAllowed(String),
    #[error("refusing to run an empty argv")]
    EmptyArgv,
    #[error("failed to spawn {argv0}: {source}")]
    Spawn {
        argv0: String,
        #[source]
        source: std::io::Error,
    },
    #[error("{argv0} did not finish within {timeout:?}; killed")]
    Timeout { argv0: String, timeout: Duration },
    #[error("{argv0} produced more than {limit} bytes of output; killed")]
    OutputTooLarge { argv0: String, limit: usize },
    #[error("i/o error while supervising {argv0}: {source}")]
    Io {
        argv0: String,
        #[source]
        source: std::io::Error,
    },
}

fn lookup(name: &str) -> Option<&'static str> {
    let found = ALLOWED_BINARIES.iter().find(|(n, _)| *n == name);
    #[cfg(test)]
    let found = found.or_else(|| TEST_ONLY_BINARIES.iter().find(|(n, _)| *n == name));
    found.map(|(_, path)| *path)
}

/// Resolve every executable position in `argv` to its pinned absolute path. For `sudo`,
/// the first non-flag argument is the command sudo will run, and is pinned too.
fn resolve(argv: &[&str]) -> Result<Vec<String>, WrapperError> {
    let (&argv0, rest) = argv.split_first().ok_or(WrapperError::EmptyArgv)?;
    let pinned0 = lookup(argv0).ok_or_else(|| WrapperError::NotAllowed(argv0.to_string()))?;
    let mut resolved = vec![pinned0.to_string()];
    let mut command_pinned = argv0 != "sudo";
    for &arg in rest {
        if !command_pinned && !arg.starts_with('-') {
            let pinned = lookup(arg).ok_or_else(|| WrapperError::NotAllowed(arg.to_string()))?;
            resolved.push(pinned.to_string());
            command_pinned = true;
        } else {
            resolved.push(arg.to_string());
        }
    }
    if !command_pinned {
        // `sudo` with no command (e.g. `sudo -n -v`) is not something this tool ever does.
        return Err(WrapperError::NotAllowed(
            "sudo without a pinned command".to_string(),
        ));
    }
    Ok(resolved)
}

/// Run `argv` to completion under [`Limits::default`] and return a full [`CommandRecord`].
///
/// This never panics on a non-zero exit — a mutating caller (`execute::run`) decides what a
/// non-zero exit means for its `PlannedTransition`; this function only observes and records.
pub fn run(argv: &[&str]) -> Result<CommandRecord, WrapperError> {
    run_with_limits(argv, Limits::default())
}

/// [`run`] with explicit bounds.
pub fn run_with_limits(argv: &[&str], limits: Limits) -> Result<CommandRecord, WrapperError> {
    let resolved = resolve(argv)?;
    let argv0 = resolved[0].clone();

    let mut child = Command::new(&resolved[0])
        .args(&resolved[1..])
        .env_clear()
        .env("PATH", CHILD_PATH)
        .env("LC_ALL", CHILD_LOCALE)
        .env("LANG", CHILD_LOCALE)
        .stdin(Stdio::null())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .map_err(|source| WrapperError::Spawn {
            argv0: argv0.clone(),
            source,
        })?;

    let stdout_reader = spawn_capped_reader(child.stdout.take(), limits.max_output_bytes);
    let stderr_reader = spawn_capped_reader(child.stderr.take(), limits.max_output_bytes);

    let status = wait_with_deadline(&mut child, &argv0, limits.timeout)?;

    let stdout = join_reader(stdout_reader, &argv0)?;
    let stderr = join_reader(stderr_reader, &argv0)?;
    if stdout.len() > limits.max_output_bytes || stderr.len() > limits.max_output_bytes {
        return Err(WrapperError::OutputTooLarge {
            argv0,
            limit: limits.max_output_bytes,
        });
    }

    Ok(CommandRecord {
        argv: resolved,
        exit_code: status.code().unwrap_or(-1),
        stdout_sha256: hex::encode(Sha256::digest(&stdout)),
        stdout: String::from_utf8_lossy(&stdout).into_owned(),
        stderr: String::from_utf8_lossy(&stderr).into_owned(),
    })
}

type Reader = Option<thread::JoinHandle<std::io::Result<Vec<u8>>>>;

/// Read at most `cap + 1` bytes (the extra byte is how an overflow is detected), then drop
/// the pipe so a runaway writer gets `SIGPIPE` instead of blocking forever.
fn spawn_capped_reader<R: Read + Send + 'static>(pipe: Option<R>, cap: usize) -> Reader {
    pipe.map(|p| {
        thread::spawn(move || {
            let mut buf = Vec::new();
            p.take(cap as u64 + 1).read_to_end(&mut buf)?;
            Ok(buf)
        })
    })
}

fn join_reader(reader: Reader, argv0: &str) -> Result<Vec<u8>, WrapperError> {
    let Some(handle) = reader else {
        return Ok(Vec::new());
    };
    let io_err = |source| WrapperError::Io {
        argv0: argv0.to_string(),
        source,
    };
    handle
        .join()
        .map_err(|_| io_err(std::io::Error::other("output reader thread panicked")))?
        .map_err(io_err)
}

fn wait_with_deadline(
    child: &mut std::process::Child,
    argv0: &str,
    timeout: Duration,
) -> Result<std::process::ExitStatus, WrapperError> {
    let deadline = Instant::now() + timeout;
    loop {
        let polled = child.try_wait().map_err(|source| WrapperError::Io {
            argv0: argv0.to_string(),
            source,
        })?;
        if let Some(status) = polled {
            return Ok(status);
        }
        if Instant::now() >= deadline {
            // Best effort: the child may have exited between try_wait and kill.
            let _ = child.kill();
            let _ = child.wait();
            return Err(WrapperError::Timeout {
                argv0: argv0.to_string(),
                timeout,
            });
        }
        thread::sleep(POLL_INTERVAL);
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn records_argv_exit_code_and_hash() {
        let record = run(&["echo", "-n", "hello"]).expect("echo should spawn");
        assert_eq!(record.argv, vec!["/bin/echo", "-n", "hello"]);
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
    fn unlisted_binary_is_refused_before_any_spawn() {
        let result = run(&["this-binary-does-not-exist-anywhere-on-path"]);
        assert!(matches!(result, Err(WrapperError::NotAllowed(_))));
    }

    #[test]
    fn path_like_argv0_is_refused_not_executed() {
        // Callers may not smuggle their own path past the allowlist.
        assert!(matches!(
            run(&["/tmp/bputil", "-d"]),
            Err(WrapperError::NotAllowed(_))
        ));
        assert!(matches!(
            run(&["./bputil"]),
            Err(WrapperError::NotAllowed(_))
        ));
    }

    #[test]
    fn empty_argv_is_an_error() {
        assert!(matches!(run(&[]), Err(WrapperError::EmptyArgv)));
    }

    #[test]
    fn every_allowlisted_binary_is_an_absolute_path() {
        for (name, path) in ALLOWED_BINARIES {
            assert!(path.starts_with('/'), "{name} -> {path} is not absolute");
            assert!(
                path.ends_with(name),
                "{name} -> {path} names a different tool"
            );
        }
    }

    #[test]
    fn sudo_target_is_pinned_too() {
        let resolved = resolve(&["sudo", "-n", "bputil", "-d"]).unwrap();
        assert_eq!(
            resolved,
            vec!["/usr/bin/sudo", "-n", "/usr/bin/bputil", "-d"]
        );
    }

    #[test]
    fn sudo_with_unlisted_target_is_refused() {
        assert!(matches!(
            resolve(&["sudo", "-n", "sh", "-c", "id"]),
            Err(WrapperError::NotAllowed(_))
        ));
        assert!(matches!(
            resolve(&["sudo", "-n", "-v"]),
            Err(WrapperError::NotAllowed(_))
        ));
    }

    #[test]
    fn child_sees_only_the_fixed_environment() {
        // The test process itself has HOME, USER, PATH etc.; none of it may reach a child.
        let record = run(&["env"]).expect("env runs");
        let mut vars: Vec<&str> = record.stdout.lines().collect();
        vars.sort_unstable();
        assert_eq!(
            vars,
            vec!["LANG=C", "LC_ALL=C", "PATH=/usr/bin:/bin:/usr/sbin:/sbin"]
        );
    }

    #[test]
    fn hung_child_is_killed_at_the_deadline() {
        let started = Instant::now();
        let result = run_with_limits(
            &["sleep", "5"],
            Limits {
                timeout: Duration::from_millis(200),
                max_output_bytes: 1024,
            },
        );
        assert!(matches!(result, Err(WrapperError::Timeout { .. })));
        assert!(started.elapsed() < Duration::from_secs(4));
    }

    #[test]
    fn runaway_output_is_capped_and_refused() {
        let result = run_with_limits(
            &["yes"],
            Limits {
                timeout: Duration::from_secs(10),
                max_output_bytes: 64 * 1024,
            },
        );
        assert!(matches!(result, Err(WrapperError::OutputTooLarge { .. })));
    }

    #[test]
    fn hash_is_deterministic_for_same_output() {
        let a = run(&["echo", "-n", "deterministic"]).unwrap();
        let b = run(&["echo", "-n", "deterministic"]).unwrap();
        assert_eq!(a.stdout_sha256, b.stdout_sha256);
    }
}
