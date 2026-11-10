//! The `BootState` model and its validity predicate.
//!
//! Field shapes and constraints are taken verbatim from `spec/contract-spec.md`'s "Data
//! contracts" section. `ValidBootState` is enforced on construction (`collect::collect`) and
//! on deserialisation — an inconsistent reading is a parse error (exit 11), never a guess,
//! per that document and `spec/build-spec.md`'s state/collect "must not" column.

pub mod collect;
pub mod diff;
pub mod img4;

use crate::env::Environment;
use serde::{Deserialize, Serialize};
use time::OffsetDateTime;

pub const SCHEMA_VERSION: u32 = 1;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum SecurityMode {
    Full,
    Reduced,
    Permissive,
    Unknown,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum Signer {
    Apple,
    SepLocalPolicy,
    Unknown,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum ObjectRole {
    Llb,
    IBoot,
    KernelCache,
    AuxKc,
    CustomBootObject,
}

/// How trustworthy the ambience measurement of this `BootState` is.
///
/// From the evaluator decision table's "Build next" item 1
/// (`reports/evaluator/evaluator-decisions-2026-11-11.md`): a consumer must be able to
/// distinguish "measured Full" from "unmeasured", because silent `Unknown` degradation
/// (missing sudo, unparseable tool output) otherwise reduces detection fidelity without
/// saying so. The honesty rule the decision attaches: the field must make *unmeasured*
/// louder, not quieter.
///
/// Not yet derived by `state::collect` — the wiring is phase-1's next follow-up. Until
/// then the serde default below makes every legacy `schema_version` 1 baseline
/// deserialise to the most conservative variant, so nothing overclaims confidence.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum PostureConfidence {
    /// `security_mode` and the derived booleans were measured directly from Apple tool
    /// output this collection (wired into `state::collect` — see above).
    Measured,
    /// Derived from weaker secondary signals (e.g. `csrutil`-only or partially
    /// degraded parses); direction of the indicator is readable, precision is not.
    UntrustedRead,
    /// Nothing may be claimed about this ambient's measurement confidence.
    Unmeasured,
}

fn default_posture_confidence() -> PostureConfidence {
    PostureConfidence::Unmeasured
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct Host {
    pub chip: String,
    pub macos_build: String,
    /// At most the last 4 characters of the serial — never the full serial
    /// (`contract-spec.md`, `host.serial_masked`).
    pub serial_masked: String,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct EnrolledObject {
    pub role: ObjectRole,
    /// 96 lowercase hex characters (sha384).
    pub sha384: String,
    pub signer: Signer,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct TargetContainer {
    pub volume_group_uuid: String,
    pub security_mode: SecurityMode,
    pub ssv_enabled: bool,
    pub allows_custom_kernel: bool,
    pub allows_third_party_kexts: bool,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct OtherContainer {
    pub volume_group_uuid: String,
    pub security_mode: SecurityMode,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct RawOutput {
    pub command: Vec<String>,
    pub exit_code: i32,
    pub stdout_sha256: String,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize, Default)]
pub struct Evidence {
    pub raw_outputs: Vec<RawOutput>,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct BootState {
    pub schema_version: u32,
    /// RFC3339, must not be in the future.
    pub captured_at: String,
    pub environment: Environment,
    /// See [`PostureConfidence`]. Defaults to [`PostureConfidence::Unmeasured`] on
    /// deserialisation so pre-schema-addition baselines stay readable and never
    /// upgrade their own confidence claim.
    #[serde(default = "default_posture_confidence")]
    pub posture_confidence: PostureConfidence,
    pub host: Host,
    pub target_container: TargetContainer,
    pub enrolled_objects: Vec<EnrolledObject>,
    pub other_containers: Vec<OtherContainer>,
    pub evidence: Evidence,
}

#[derive(Debug, Clone, PartialEq, Eq, thiserror::Error)]
pub enum BootStateError {
    #[error("captured_at `{0}` is not valid RFC3339 or lies in the future")]
    InvalidCapturedAt(String),
    #[error("host.chip must be non-empty")]
    EmptyChip,
    #[error("host.macos_build must be non-empty")]
    EmptyMacosBuild,
    #[error("host.serial_masked must be at most 4 characters, got `{0}`")]
    SerialTooLong(String),
    #[error("security_mode is Unknown but environment is not MacOs")]
    UnknownModeOutsideMacOs,
    #[error("ssv_enabled is true but security_mode is Permissive")]
    PermissiveWithSsvEnabled,
    #[error("allows_custom_kernel is true but security_mode is not Permissive")]
    CustomKernelOutsidePermissive,
    #[error("allows_third_party_kexts is true but security_mode is Full")]
    ThirdPartyKextsUnderFull,
    #[error("enrolled object sha384 `{0}` is not 96 lowercase hex characters")]
    BadSha384(String),
    #[error("enrolled object has role CustomBootObject but signer is not SepLocalPolicy")]
    CustomBootObjectWrongSigner,
    #[error("other_containers entry `{0}` shares the target container's volume_group_uuid")]
    OtherContainerNotDisjoint(String),
}

/// `ValidBootState(s)` from `spec/contract-spec.md`: every field constraint, plus internal
/// consistency between `security_mode` and the derived `allows_*` booleans. An inconsistent
/// reading (e.g. Permissive with `ssv_enabled == true`) is NOT clamped to something sane —
/// it means the tool misread the device, so it is reported as an error, not silently fixed.
pub fn validate(state: &BootState) -> Result<(), BootStateError> {
    let captured_at = OffsetDateTime::parse(
        &state.captured_at,
        &time::format_description::well_known::Rfc3339,
    )
    .map_err(|_| BootStateError::InvalidCapturedAt(state.captured_at.clone()))?;
    if captured_at > OffsetDateTime::now_utc() {
        return Err(BootStateError::InvalidCapturedAt(state.captured_at.clone()));
    }

    if state.host.chip.is_empty() {
        return Err(BootStateError::EmptyChip);
    }
    if state.host.macos_build.is_empty() {
        return Err(BootStateError::EmptyMacosBuild);
    }
    if state.host.serial_masked.len() > 4 {
        return Err(BootStateError::SerialTooLong(
            state.host.serial_masked.clone(),
        ));
    }

    let tc = &state.target_container;
    if tc.security_mode == SecurityMode::Unknown && state.environment != Environment::MacOs {
        return Err(BootStateError::UnknownModeOutsideMacOs);
    }
    if tc.security_mode == SecurityMode::Permissive && tc.ssv_enabled {
        return Err(BootStateError::PermissiveWithSsvEnabled);
    }
    if tc.allows_custom_kernel && tc.security_mode != SecurityMode::Permissive {
        return Err(BootStateError::CustomKernelOutsidePermissive);
    }
    if tc.allows_third_party_kexts && tc.security_mode == SecurityMode::Full {
        return Err(BootStateError::ThirdPartyKextsUnderFull);
    }

    for obj in &state.enrolled_objects {
        let is_valid_sha384 = obj.sha384.len() == 96
            && obj
                .sha384
                .bytes()
                .all(|b| b.is_ascii_hexdigit() && !b.is_ascii_uppercase());
        if !is_valid_sha384 {
            return Err(BootStateError::BadSha384(obj.sha384.clone()));
        }
        if obj.role == ObjectRole::CustomBootObject && obj.signer != Signer::SepLocalPolicy {
            return Err(BootStateError::CustomBootObjectWrongSigner);
        }
    }

    for other in &state.other_containers {
        if other.volume_group_uuid == tc.volume_group_uuid {
            return Err(BootStateError::OtherContainerNotDisjoint(
                other.volume_group_uuid.clone(),
            ));
        }
    }

    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    fn valid_full_state() -> BootState {
        BootState {
            schema_version: SCHEMA_VERSION,
            captured_at: "2026-01-01T00:00:00Z".to_string(),
            environment: Environment::MacOs,
            posture_confidence: PostureConfidence::Measured,
            host: Host {
                chip: "Apple M2 Pro".to_string(),
                macos_build: "24A335".to_string(),
                serial_masked: "WXYZ".to_string(),
            },
            target_container: TargetContainer {
                volume_group_uuid: "AAAA-TARGET".to_string(),
                security_mode: SecurityMode::Full,
                ssv_enabled: true,
                allows_custom_kernel: false,
                allows_third_party_kexts: false,
            },
            enrolled_objects: vec![],
            other_containers: vec![OtherContainer {
                volume_group_uuid: "BBBB-OTHER".to_string(),
                security_mode: SecurityMode::Full,
            }],
            evidence: Evidence::default(),
        }
    }

    #[test]
    fn well_formed_full_state_is_valid() {
        assert!(validate(&valid_full_state()).is_ok());
    }

    #[test]
    fn legacy_baseline_without_posture_confidence_deserialises_as_unmeasured() {
        // A pre-schema-addition baseline (see
        // `evidence/vm-sec-research-25D125/baseline_reduced.json`): no
        // `posture_confidence` key. It must remain readable, and must not upgrade
        // its own confidence claim — the serde default is Unmeasured, exactly the
        // honesty rule the decision table attaches ("make unmeasured louder").
        let legacy = serde_json::json!({
            "schema_version": 1,
            "captured_at": "2026-01-01T00:00:00Z",
            "environment": "MacOs",
            "host": { "chip": "Apple M2 Pro", "macos_build": "24A335", "serial_masked": "WXYZ" },
            "target_container": {
                "volume_group_uuid": "AAAA-TARGET",
                "security_mode": "Full",
                "ssv_enabled": true,
                "allows_custom_kernel": false,
                "allows_third_party_kexts": false
            },
            "enrolled_objects": [],
            "other_containers": [],
            "evidence": { "raw_outputs": [] }
        });
        let parsed: BootState = serde_json::from_value(legacy).expect("legacy baseline parses");
        assert_eq!(parsed.posture_confidence, PostureConfidence::Unmeasured);
        assert!(
            parsed.captured_at.contains("2026"),
            "fields survive round-trip"
        );
    }

    #[test]
    fn postured_confidence_variant_does_not_break_validate() {
        for variant in [
            PostureConfidence::Measured,
            PostureConfidence::UntrustedRead,
            PostureConfidence::Unmeasured,
        ] {
            let mut s = valid_full_state();
            s.posture_confidence = variant;
            assert!(validate(&s).is_ok());
        }
    }

    #[test]
    fn serialisation_carries_posture_confidence() {
        let s = valid_full_state();
        let json = serde_json::to_string(&s).expect("serialises");
        assert!(json.contains("posture_confidence"));
    }

    #[test]
    fn permissive_with_ssv_enabled_is_rejected() {
        let mut s = valid_full_state();
        s.target_container.security_mode = SecurityMode::Permissive;
        s.target_container.ssv_enabled = true;
        assert_eq!(validate(&s), Err(BootStateError::PermissiveWithSsvEnabled));
    }

    #[test]
    fn custom_kernel_outside_permissive_is_rejected() {
        let mut s = valid_full_state();
        s.target_container.allows_custom_kernel = true;
        assert_eq!(
            validate(&s),
            Err(BootStateError::CustomKernelOutsidePermissive)
        );
    }

    #[test]
    fn unknown_mode_in_1tr_is_rejected() {
        let mut s = valid_full_state();
        s.environment = Environment::OneTrueRecovery;
        s.target_container.security_mode = SecurityMode::Unknown;
        assert_eq!(validate(&s), Err(BootStateError::UnknownModeOutsideMacOs));
    }

    #[test]
    fn unknown_mode_in_macos_is_allowed() {
        let mut s = valid_full_state();
        s.target_container.security_mode = SecurityMode::Unknown;
        assert!(validate(&s).is_ok());
    }

    #[test]
    fn non_disjoint_other_container_is_rejected() {
        let mut s = valid_full_state();
        s.other_containers[0].volume_group_uuid = s.target_container.volume_group_uuid.clone();
        assert!(matches!(
            validate(&s),
            Err(BootStateError::OtherContainerNotDisjoint(_))
        ));
    }

    #[test]
    fn bad_sha384_length_is_rejected() {
        let mut s = valid_full_state();
        s.enrolled_objects.push(EnrolledObject {
            role: ObjectRole::IBoot,
            sha384: "deadbeef".to_string(),
            signer: Signer::Apple,
        });
        assert!(matches!(validate(&s), Err(BootStateError::BadSha384(_))));
    }

    #[test]
    fn custom_boot_object_must_be_sep_signed() {
        let mut s = valid_full_state();
        s.enrolled_objects.push(EnrolledObject {
            role: ObjectRole::CustomBootObject,
            sha384: "a".repeat(96),
            signer: Signer::Apple,
        });
        assert_eq!(
            validate(&s),
            Err(BootStateError::CustomBootObjectWrongSigner)
        );
    }

    #[test]
    fn future_captured_at_is_rejected() {
        let mut s = valid_full_state();
        s.captured_at = "2999-01-01T00:00:00Z".to_string();
        assert!(matches!(
            validate(&s),
            Err(BootStateError::InvalidCapturedAt(_))
        ));
    }
}
