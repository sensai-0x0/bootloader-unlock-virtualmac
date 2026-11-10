//! `state::diff` — a structured [`BootState`] difference, shared by `plan` (P2) and `verify`
//! (P3) per `spec/phased-plan.md`'s Phase 2 workstream list.

use crate::state::BootState;
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct DiffEntry {
    pub path: String,
    pub before: String,
    pub after: String,
}

/// Compare two [`BootState`]s field by field and return every path that changed. Only the
/// fields that can legitimately differ across a transition are compared — `evidence` and
/// `captured_at` always differ and are intentionally excluded, matching the P1 exit-gate
/// expectation that "evaluate twice differs only in the timestamp" (i.e. nothing *else*
/// should show up in a no-op diff).
pub fn diff(before: &BootState, after: &BootState) -> Vec<DiffEntry> {
    let mut entries = Vec::new();

    macro_rules! compare {
        ($path:literal, $before_val:expr, $after_val:expr) => {
            if $before_val != $after_val {
                entries.push(DiffEntry {
                    path: $path.to_string(),
                    before: format!("{:?}", $before_val),
                    after: format!("{:?}", $after_val),
                });
            }
        };
    }

    compare!("environment", before.environment, after.environment);
    // posture_confidence is the field the evaluator's own binding guardrail exists for
    // ("honesty of state — must surface unmeasured louder",
    // reports/evaluator/evaluator-decisions-2026-11-11.md D2). Omitting it here would let a
    // confidence downgrade (or a baseline claiming a different confidence than a fresh read,
    // e.g. via `verify --baseline <path>` against an externally-authored file) pass through
    // this diff silently whenever target_container's other fields happen to still match —
    // exactly the "silent degradation without saying so" failure mode the field was added to
    // prevent. See vuln_res/sweep-reports/ for the finding this closes.
    compare!(
        "posture_confidence",
        before.posture_confidence,
        after.posture_confidence
    );
    compare!(
        "target_container.security_mode",
        before.target_container.security_mode,
        after.target_container.security_mode
    );
    compare!(
        "target_container.ssv_enabled",
        before.target_container.ssv_enabled,
        after.target_container.ssv_enabled
    );
    compare!(
        "target_container.allows_custom_kernel",
        before.target_container.allows_custom_kernel,
        after.target_container.allows_custom_kernel
    );
    compare!(
        "target_container.allows_third_party_kexts",
        before.target_container.allows_third_party_kexts,
        after.target_container.allows_third_party_kexts
    );
    compare!(
        "enrolled_objects",
        before.enrolled_objects,
        after.enrolled_objects
    );
    compare!(
        "other_containers",
        before.other_containers,
        after.other_containers
    );

    entries
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::env::Environment;
    use crate::state::{
        Evidence, Host, PostureConfidence, SCHEMA_VERSION, SecurityMode, TargetContainer,
    };

    fn state(security_mode: SecurityMode) -> BootState {
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
                security_mode,
                ssv_enabled: security_mode != SecurityMode::Permissive,
                allows_custom_kernel: security_mode == SecurityMode::Permissive,
                allows_third_party_kexts: security_mode != SecurityMode::Full,
            },
            enrolled_objects: vec![],
            other_containers: vec![],
            evidence: Evidence::default(),
        }
    }

    #[test]
    fn identical_states_diff_to_nothing() {
        let a = state(SecurityMode::Full);
        let b = state(SecurityMode::Full);
        assert!(diff(&a, &b).is_empty());
    }

    #[test]
    fn a_security_mode_change_is_reported_at_its_exact_paths() {
        let a = state(SecurityMode::Full);
        let b = state(SecurityMode::Reduced);
        let entries = diff(&a, &b);
        let paths: Vec<&str> = entries.iter().map(|e| e.path.as_str()).collect();
        assert!(paths.contains(&"target_container.security_mode"));
        assert!(paths.contains(&"target_container.allows_third_party_kexts"));
        assert_eq!(entries.len(), 2);
    }

    #[test]
    fn a_posture_confidence_change_is_reported_even_when_security_mode_is_unchanged() {
        // The gap this test closes: a baseline (e.g. an externally-authored file passed to
        // `verify --baseline <path>`, or a legacy pre-schema baseline that defaults to
        // Unmeasured) can claim a different posture_confidence than a fresh measurement
        // while target_container's fields all still match. Before this fix, diff() had no
        // comparison for posture_confidence at all, so this case produced zero diff
        // entries — silently hiding exactly the kind of confidence downgrade the field
        // exists to surface ("honesty of state — must surface unmeasured louder",
        // reports/evaluator/evaluator-decisions-2026-11-11.md D2).
        let mut a = state(SecurityMode::Full);
        a.posture_confidence = PostureConfidence::Measured;
        let mut b = state(SecurityMode::Full);
        b.posture_confidence = PostureConfidence::UntrustedRead;

        let entries = diff(&a, &b);
        let paths: Vec<&str> = entries.iter().map(|e| e.path.as_str()).collect();
        assert!(paths.contains(&"posture_confidence"));
        assert_eq!(entries.len(), 1);
    }
}
