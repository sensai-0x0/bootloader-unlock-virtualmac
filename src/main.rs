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
}

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
    /// measurement. Read-only. Full invariant assertion (`verify.assert_invariants` against
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
    let baseline_json = match std::fs::read_to_string(&baseline_path) {
        Ok(s) => s,
        Err(e) => {
            eprintln!("could not read baseline {}: {e}", baseline_path.display());
            return ExitCode::from(exit_code::PARSE_ERROR);
        }
    };
    let baseline: state::BootState = match serde_json::from_str(&baseline_json) {
        Ok(b) => b,
        Err(e) => {
            eprintln!(
                "baseline {} is not a valid BootState: {e}",
                baseline_path.display()
            );
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

    let diff = state::diff::diff(&baseline, &fresh);
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
        exit_code: 0,
    };

    if json {
        println!("{}", serde_json::to_string_pretty(&rpt).unwrap());
    } else {
        println!("{} field(s) differ from baseline:", rpt.diff.len());
        for entry in &rpt.diff {
            println!("  {}: {} -> {}", entry.path, entry.before, entry.after);
        }
    }
    ExitCode::from(exit_code::OK)
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
