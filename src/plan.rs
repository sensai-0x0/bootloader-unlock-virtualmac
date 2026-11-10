//! `plan` — diff the current [`BootState`] against a target profile and emit a
//! `PlannedTransition`, as data. Never executes anything (`spec/build-spec.md`'s state/plan
//! "must not": "Execute anything").
//!
//! Command flags below are taken from this machine's installed `bputil --help` (v0.1.14),
//! not invented: `-f/--full-security`, `-g/--reduced-security`, `-k/--enable-kexts`,
//! `-n/--permissive-security`, `-c/--disable-kernel-ctrr`, `-s/--disable-ssv`, and
//! `-v/--vuid <uuid>`. The `kmutil configure-boot -c <path> -v <volume>` invocation for the
//! custom-kernel enrolment is the worked example verbatim from `spec/build-spec.md`'s
//! `PlannedTransition` sample, since this module doesn't independently know the custom boot
//! object's path — that detail belongs to the missing companion architecture document and
//! is left as a placeholder (`<custom-boot-object-path>`) rather than guessed.
//!
//! State-machine note: `spec/contract-spec.md` describes "the only legal transitions" as a
//! diagram that isn't present in this repo's extracted text (only the sentence introducing
//! it survived). Absent that diagram, this module models the conservative, spec-consistent
//! reading implied by the phased plan's own round-trip tests ("full → reduced → full",
//! "full → permissive → full"): `Full` can go to either mutating profile; `ReducedKexts` and
//! `PermissiveCustomKernel` can only go back to `Full`. There is deliberately no direct
//! `ReducedKexts <-> PermissiveCustomKernel` edge. Revisit this once the architecture
//! document is available — this is a modeled choice, not a transcribed one.

use crate::state::{BootState, SecurityMode};
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum TargetProfile {
    Full,
    ReducedKexts,
    PermissiveCustomKernel,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct PlannedCommand {
    pub argv: Vec<String>,
    pub authoritative_source: String,
    pub expected_effect: String,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct Requires {
    pub environment: String,
    pub owner_credentials: bool,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct PlannedTransition {
    pub schema_version: u32,
    pub from_mode: SecurityMode,
    pub to_profile: TargetProfile,
    pub target_volume_group: String,
    pub commands: Vec<PlannedCommand>,
    pub consequences: Vec<String>,
    pub invariants_to_check: Vec<String>,
    pub requires: Requires,
}

#[derive(Debug, Clone, PartialEq, Eq, thiserror::Error)]
pub enum PlanError {
    #[error("{from_mode:?} -> {to_profile:?} is not a permitted transition")]
    IllegalTransition {
        from_mode: SecurityMode,
        to_profile: TargetProfile,
    },
    #[error("current security_mode is Unknown; cannot plan from an unmeasured state")]
    UnknownFromMode,
}

fn is_permitted(from: SecurityMode, to: TargetProfile) -> bool {
    matches!(
        (from, to),
        (SecurityMode::Full, TargetProfile::Full)
            | (SecurityMode::Full, TargetProfile::ReducedKexts)
            | (SecurityMode::Full, TargetProfile::PermissiveCustomKernel)
            | (SecurityMode::Reduced, TargetProfile::Full)
            | (SecurityMode::Permissive, TargetProfile::Full)
    )
}

/// `plan(volume, target) -> PlannedTransition` from `spec/contract-spec.md`. `baseline` is
/// the current, already-collected [`BootState`] for the container being planned against.
pub fn plan(baseline: &BootState, target: TargetProfile) -> Result<PlannedTransition, PlanError> {
    let from_mode = baseline.target_container.security_mode;
    if from_mode == SecurityMode::Unknown {
        return Err(PlanError::UnknownFromMode);
    }
    if !is_permitted(from_mode, target) {
        return Err(PlanError::IllegalTransition {
            from_mode,
            to_profile: target,
        });
    }

    let vuid = baseline.target_container.volume_group_uuid.clone();
    let mutates = from_mode != target_to_mode(target);

    let commands = if mutates {
        commands_for(target, &vuid)
    } else {
        vec![]
    };
    let consequences = if mutates {
        consequences_for(target)
    } else {
        vec![]
    };

    Ok(PlannedTransition {
        schema_version: crate::state::SCHEMA_VERSION,
        from_mode,
        to_profile: target,
        target_volume_group: vuid,
        commands,
        consequences,
        invariants_to_check: vec![
            "SingleContainerTouched".to_string(),
            "Reversible".to_string(),
            "MeasuredTruth".to_string(),
            mode_specific_invariant(target),
        ],
        requires: Requires {
            environment: "OneTrueRecovery".to_string(),
            owner_credentials: mutates,
        },
    })
}

fn target_to_mode(target: TargetProfile) -> SecurityMode {
    match target {
        TargetProfile::Full => SecurityMode::Full,
        TargetProfile::ReducedKexts => SecurityMode::Reduced,
        TargetProfile::PermissiveCustomKernel => SecurityMode::Permissive,
    }
}

fn mode_specific_invariant(target: TargetProfile) -> String {
    match target {
        TargetProfile::Full => "FullSecurityRestored".to_string(),
        TargetProfile::ReducedKexts => "ThirdPartyKextsAllowedUnderReduced".to_string(),
        TargetProfile::PermissiveCustomKernel => "CustomKernelAllowedUnderPermissive".to_string(),
    }
}

fn commands_for(target: TargetProfile, vuid: &str) -> Vec<PlannedCommand> {
    let source = "bputil --help (installed v0.1.14), confirmed on this host".to_string();
    match target {
        TargetProfile::Full => vec![PlannedCommand {
            argv: vec![
                "bputil".to_string(),
                "-f".to_string(),
                "-v".to_string(),
                vuid.to_string(),
            ],
            authoritative_source: source,
            expected_effect: "security_mode -> Full; ssv_enabled -> true; third-party kexts and custom kernel disallowed".to_string(),
        }],
        TargetProfile::ReducedKexts => vec![PlannedCommand {
            argv: vec![
                "bputil".to_string(),
                "-g".to_string(),
                "-k".to_string(),
                "-v".to_string(),
                vuid.to_string(),
            ],
            authoritative_source: source,
            expected_effect: "security_mode -> Reduced; third-party kexts trusted via SEP-signed AuxKC".to_string(),
        }],
        TargetProfile::PermissiveCustomKernel => vec![
            PlannedCommand {
                argv: vec![
                    "bputil".to_string(),
                    "-n".to_string(),
                    "-c".to_string(),
                    "-s".to_string(),
                    "-v".to_string(),
                    vuid.to_string(),
                ],
                authoritative_source: source,
                expected_effect: "security_mode -> Permissive; kernel CTRR disabled; SSV disabled (contract-spec requires ssv_enabled == false whenever Permissive)".to_string(),
            },
            PlannedCommand {
                argv: vec![
                    "kmutil".to_string(),
                    "configure-boot".to_string(),
                    "-c".to_string(),
                    "<custom-boot-object-path>".to_string(),
                    "-v".to_string(),
                    vuid.to_string(),
                ],
                authoritative_source: "spec/build-spec.md PlannedTransition worked example (verbatim)".to_string(),
                expected_effect: "enrols the custom boot object; must verify as signer == SepLocalPolicy".to_string(),
            },
        ],
    }
}

fn consequences_for(target: TargetProfile) -> Vec<String> {
    match target {
        TargetProfile::Full => vec![
            "SSV re-enabled".to_string(),
            "SIP fully enforced".to_string(),
            "any CustomBootObject enrolment is dropped".to_string(),
        ],
        TargetProfile::ReducedKexts => vec![
            "third-party kernel extensions become trusted if SEP-signed".to_string(),
            "SIP remains enabled; SSV remains enabled".to_string(),
        ],
        TargetProfile::PermissiveCustomKernel => vec![
            "SSV off".to_string(),
            "kernel CTRR (code read-only enforcement) disabled".to_string(),
            "a custom kernel/boot object may be enrolled and will boot without full Apple signing"
                .to_string(),
        ],
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::env::Environment;
    use crate::state::{Evidence, Host, PostureConfidence, SCHEMA_VERSION, TargetContainer};

    fn baseline_with_mode(mode: SecurityMode) -> BootState {
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
                volume_group_uuid: "VUID-1234".to_string(),
                security_mode: mode,
                ssv_enabled: mode != SecurityMode::Permissive,
                allows_custom_kernel: mode == SecurityMode::Permissive,
                allows_third_party_kexts: mode != SecurityMode::Full,
            },
            enrolled_objects: vec![],
            other_containers: vec![],
            evidence: Evidence::default(),
        }
    }

    #[test]
    fn full_to_reduced_kexts_is_permitted_and_uses_bputil_flags() {
        let baseline = baseline_with_mode(SecurityMode::Full);
        let p = plan(&baseline, TargetProfile::ReducedKexts).unwrap();
        assert_eq!(p.commands.len(), 1);
        assert_eq!(p.commands[0].argv[0], "bputil");
        assert!(p.commands[0].argv.contains(&"-g".to_string()));
        assert!(p.commands[0].argv.contains(&"-k".to_string()));
        assert_eq!(p.requires.environment, "OneTrueRecovery");
        assert!(p.requires.owner_credentials);
    }

    #[test]
    fn full_to_permissive_includes_kmutil_enrolment() {
        let baseline = baseline_with_mode(SecurityMode::Full);
        let p = plan(&baseline, TargetProfile::PermissiveCustomKernel).unwrap();
        assert_eq!(p.commands.len(), 2);
        assert_eq!(p.commands[1].argv[0], "kmutil");
    }

    #[test]
    fn reduced_to_permissive_direct_edge_is_rejected() {
        let baseline = baseline_with_mode(SecurityMode::Reduced);
        let result = plan(&baseline, TargetProfile::PermissiveCustomKernel);
        assert!(matches!(result, Err(PlanError::IllegalTransition { .. })));
    }

    #[test]
    fn reduced_to_full_is_a_revert_with_bputil_full_flag() {
        let baseline = baseline_with_mode(SecurityMode::Reduced);
        let p = plan(&baseline, TargetProfile::Full).unwrap();
        assert!(p.commands[0].argv.contains(&"-f".to_string()));
    }

    #[test]
    fn planning_from_unknown_mode_is_refused() {
        let baseline = baseline_with_mode(SecurityMode::Unknown);
        assert_eq!(
            plan(&baseline, TargetProfile::Full),
            Err(PlanError::UnknownFromMode)
        );
    }

    #[test]
    fn every_argv0_is_an_allowed_tool() {
        let allowed = ["bputil", "kmutil", "csrutil"];
        for (mode, target) in [
            (SecurityMode::Full, TargetProfile::ReducedKexts),
            (SecurityMode::Full, TargetProfile::PermissiveCustomKernel),
        ] {
            let baseline = baseline_with_mode(mode);
            let p = plan(&baseline, target).unwrap();
            for cmd in &p.commands {
                assert!(
                    allowed.contains(&cmd.argv[0].as_str()),
                    "disallowed tool: {}",
                    cmd.argv[0]
                );
            }
        }
    }

    #[test]
    fn a_noop_plan_has_no_commands_and_does_not_require_credentials() {
        let baseline = baseline_with_mode(SecurityMode::Full);
        let p = plan(&baseline, TargetProfile::Full).unwrap();
        assert!(p.commands.is_empty());
        assert!(!p.requires.owner_credentials);
    }

    // Golden-file tests (spec/phased-plan.md's P2 exit gate: "Golden-file plans correct per
    // profile"). Each fixture under tests/fixtures/plans/ was generated from plan() itself
    // against the fixed baseline below and then committed — these tests catch any future
    // change to commands_for/consequences_for/plan() that silently changes what gets
    // planned, by diffing against that frozen snapshot rather than re-deriving it inline.
    fn assert_matches_golden_file(mode: SecurityMode, target: TargetProfile, fixture_path: &str) {
        let baseline = baseline_with_mode(mode);
        let planned = plan(&baseline, target).unwrap();
        let actual = serde_json::to_value(&planned).unwrap();
        let expected: serde_json::Value = serde_json::from_str(fixture_path).unwrap();
        assert_eq!(
            actual, expected,
            "plan output no longer matches the committed golden file"
        );
    }

    #[test]
    fn golden_full_to_reduced_kexts() {
        assert_matches_golden_file(
            SecurityMode::Full,
            TargetProfile::ReducedKexts,
            include_str!("../tests/fixtures/plans/full_to_reduced_kexts.json"),
        );
    }

    #[test]
    fn golden_full_to_permissive_custom_kernel() {
        assert_matches_golden_file(
            SecurityMode::Full,
            TargetProfile::PermissiveCustomKernel,
            include_str!("../tests/fixtures/plans/full_to_permissive_custom_kernel.json"),
        );
    }

    #[test]
    fn golden_reduced_to_full_revert() {
        assert_matches_golden_file(
            SecurityMode::Reduced,
            TargetProfile::Full,
            include_str!("../tests/fixtures/plans/reduced_to_full_revert.json"),
        );
    }

    #[test]
    fn golden_permissive_to_full_revert() {
        assert_matches_golden_file(
            SecurityMode::Permissive,
            TargetProfile::Full,
            include_str!("../tests/fixtures/plans/permissive_to_full_revert.json"),
        );
    }
}
