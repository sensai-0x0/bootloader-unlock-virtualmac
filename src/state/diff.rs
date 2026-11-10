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
    // A build change is either a legitimate update or a downgrade/rollback — either way a
    // drift worth surfacing, never silently equal (offensive-robustness report, F14).
    compare!(
        "host.macos_build",
        before.host.macos_build,
        after.host.macos_build
    );
    // A drop from Measured to a weaker read is itself a signal (e.g. the root read that
    // used to succeed now fails) and must not hide behind an unchanged Unknown mode.
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
    fn build_change_is_reported_as_drift() {
        let a = state(SecurityMode::Full);
        let mut b = a.clone();
        b.host.macos_build = "23A344".to_string();
        let d = diff(&a, &b);
        assert_eq!(d.len(), 1);
        assert_eq!(d[0].path, "host.macos_build");
    }

    #[test]
    fn confidence_drop_is_reported_as_drift() {
        let mut a = state(SecurityMode::Full);
        a.posture_confidence = PostureConfidence::Measured;
        let mut b = a.clone();
        b.posture_confidence = PostureConfidence::UntrustedRead;
        assert_eq!(diff(&a, &b)[0].path, "posture_confidence");
    }
}
