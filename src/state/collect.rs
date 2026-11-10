//! `state::collect` — build a [`BootState`] purely by reading Apple tools and firmware.
//!
//! Per `spec/build-spec.md`'s per-module contract: must not modify any system state or shell
//! out to anything mutating. Every subprocess call here goes through [`crate::wrapper::run`],
//! never `std::process` directly (CI-guarded).
//!
//! `target_container.security_mode` reading requires `bputil -d`, which itself requires root
//! when run from ordinary macOS (confirmed against this dev machine: `bputil -d` without
//! `sudo` fails with "The tool requires running as root"). This module calls it through
//! `sudo -n` (non-interactive) specifically so it can **never** block on, prompt for, or
//! receive a password — if there's no cached sudo credential, the call fails immediately and
//! `security_mode` degrades to `Unknown`, which `spec/contract-spec.md` explicitly allows
//! when `environment == MacOs`. This is a deliberate, narrower reading of "must not store,
//! prompt for, or transmit owner credentials" (golden rule 4): the `sudo` password here is
//! the local admin's login password, not the SEP-backed owner credential bputil asks for
//! during an actual `apply`/`revert` in 1TR — but `authorize`/`execute` are the modules that
//! own that distinction, not this one, so collect never risks blurring it by prompting.
//!
//! `evidence.raw_outputs` scope — confirmed on real hardware, not assumed: running `collect`
//! twice a few seconds apart showed the *security-relevant* reads (`csrutil
//! authenticated-root status`, `bputil -d`) are byte-identical, but `diskutil info /` and
//! `ioreg -rd1 -c IOPlatformExpertDevice` are not — both embed live, constantly-changing
//! counters (free space consumed, an `IOPlatformExpertDevice` "busy N ms" uptime figure) that
//! have nothing to do with boot security policy. Hashing those into the evidence bundle would
//! make the P1 exit gate ("running evaluate twice differs only in the timestamp",
//! `spec/phased-plan.md`) unsatisfiable through no fault in the parsing logic. Absent the
//! missing companion architecture document to say otherwise, this module therefore only
//! records security-relevant reads into `evidence.raw_outputs`; host-identification reads
//! (serial, volume group UUID, chip, macOS build) still go through the one audited wrapper
//! (so the CI guard against bypassing it still holds) but aren't persisted into the hashed
//! evidence set. Revisit if the architecture document specifies otherwise.

use crate::env;
use crate::state::{
    BootState, BootStateError, Evidence, Host, OtherContainer, RawOutput, SCHEMA_VERSION,
    SecurityMode, TargetContainer,
};
use crate::wrapper::{self, CommandRecord, WrapperError};
use time::OffsetDateTime;

#[derive(Debug, thiserror::Error)]
pub enum CollectError {
    #[error(transparent)]
    Env(#[from] env::EnvError),
    #[error(transparent)]
    Wrapper(#[from] WrapperError),
    #[error("could not determine the APFS volume group for the root volume from `diskutil info /`")]
    NoVolumeGroup,
    #[error("could not determine the device serial number from system_profiler")]
    NoSerial,
    #[error("could not determine SSV status from `csrutil authenticated-root status` (saw: {0:?})")]
    NoSsvStatus(String),
    #[error("collect() built an internally inconsistent BootState: {0}")]
    Invalid(#[from] BootStateError),
}

/// Collect a [`BootState`] for the given target volume (currently always the root volume;
/// multi-volume target selection is a P2+ concern). Never mutates. `s1 == s0` for any two
/// calls in a row, modulo `captured_at` — the P1 exit-gate "read-only proof" in
/// `spec/phased-plan.md`.
pub fn collect() -> Result<BootState, CollectError> {
    let mut raw_outputs = Vec::new();

    let environment = env::detect()?;
    let host_info = env::host()?;

    // Host-identification reads: audited via the wrapper, but not persisted into
    // evidence.raw_outputs — see this module's doc comment ("evidence.raw_outputs scope").
    let serial_record = wrapper::run(&["system_profiler", "SPHardwareDataType"])?;
    let serial_masked =
        extract_serial_masked(&serial_record.stdout).ok_or(CollectError::NoSerial)?;

    let diskutil_record = wrapper::run(&["diskutil", "info", "/"])?;
    let volume_group_uuid =
        extract_volume_group(&diskutil_record.stdout).ok_or(CollectError::NoVolumeGroup)?;

    // `diskutil apfs listVolumeGroups` embeds the same kind of volatile per-volume
    // "Capacity Consumed" counters as `diskutil info /` (confirmed on real hardware,
    // same reasoning as this module's doc comment) — host-identification-shaped, so
    // audited via the wrapper but not persisted into evidence.raw_outputs.
    let list_vg_record = wrapper::run(&["diskutil", "apfs", "listVolumeGroups"])?;
    let other_containers = extract_other_containers(&list_vg_record.stdout, &volume_group_uuid);

    // Security-relevant reads: recorded into evidence.raw_outputs.
    let ssv_record = wrapper::run(&["csrutil", "authenticated-root", "status"])?;
    let ssv_enabled = parse_ssv_enabled(&ssv_record.stdout)
        .ok_or_else(|| CollectError::NoSsvStatus(ssv_record.stdout.clone()))?;
    record(&mut raw_outputs, &ssv_record);

    // Non-interactive: never prompts, never blocks. Absence of a cached credential is a
    // normal, expected outcome here, not an error — it just means Unknown.
    let bputil_record = wrapper::run(&["sudo", "-n", "bputil", "-d"]);
    let security_mode = match &bputil_record {
        Ok(r) if r.exit_code == 0 => parse_security_mode(&r.stdout),
        _ => SecurityMode::Unknown,
    };
    if let Ok(r) = &bputil_record {
        record(&mut raw_outputs, r);
    }

    let (allows_third_party_kexts, allows_custom_kernel) = match security_mode {
        SecurityMode::Full | SecurityMode::Unknown => (false, false),
        SecurityMode::Reduced => (true, false),
        SecurityMode::Permissive => (true, true),
    };

    let state = BootState {
        schema_version: SCHEMA_VERSION,
        captured_at: now_rfc3339(),
        environment,
        host: Host {
            chip: host_info.chip,
            macos_build: host_info.macos_build,
            serial_masked,
        },
        target_container: TargetContainer {
            volume_group_uuid,
            security_mode,
            ssv_enabled,
            allows_custom_kernel,
            allows_third_party_kexts,
        },
        enrolled_objects: vec![],
        other_containers,
        evidence: Evidence { raw_outputs },
    };

    // A validation failure here means collect() built something internally inconsistent —
    // a bug in this function, not a caller error.
    super::validate(&state)?;

    Ok(state)
}

fn record(out: &mut Vec<RawOutput>, record: &CommandRecord) {
    out.push(RawOutput {
        command: record.argv.clone(),
        exit_code: record.exit_code,
        stdout_sha256: record.stdout_sha256.clone(),
    });
}

fn now_rfc3339() -> String {
    OffsetDateTime::now_utc()
        .format(&time::format_description::well_known::Rfc3339)
        .expect("RFC3339 formatting of the current time cannot fail")
}

/// `      Serial Number (system): DMFJD27H79` from `system_profiler SPHardwareDataType` →
/// last 4 chars only, per `contract-spec.md`'s `host.serial_masked` constraint. Chosen over
/// `ioreg -c IOPlatformExpertDevice` because the latter's output embeds a live uptime
/// counter (`busy N ms`) that changes every call — see this module's doc comment.
fn extract_serial_masked(system_profiler_output: &str) -> Option<String> {
    let line = system_profiler_output
        .lines()
        .find(|l| l.contains("Serial Number"))?;
    let serial = line.split(':').nth(1)?.trim();
    if serial.len() < 4 {
        return None;
    }
    Some(serial[serial.len() - 4..].to_string())
}

/// `   APFS Volume Group:         45C6EEFD-...` from `diskutil info /`.
fn extract_volume_group(diskutil_output: &str) -> Option<String> {
    let line = diskutil_output
        .lines()
        .find(|l| l.to_lowercase().contains("apfs volume group"))?;
    line.split(':').nth(1).map(|s| s.trim().to_string())
}

/// Every `Volume Group <uuid>` line from `diskutil apfs listVolumeGroups`, excluding the
/// target container's own group. `security_mode` for each is always `Unknown`: reading
/// another container's policy needs `bputil -d -v <that-uuid>` under `sudo`, which this
/// module already avoids prompting for even for the *target* container (see module doc) —
/// doing it per other-container would multiply that same non-interactive-sudo gamble with no
/// way to batch it, for a field (`spec/contract-spec.md`'s `OtherContainer.security_mode`)
/// that only exists so `verify`'s `SingleContainerTouched` invariant (P3) has something to
/// diff — it doesn't need to be populated with real policy data until that's wired up.
fn extract_other_containers(
    list_volume_groups_output: &str,
    target_vg: &str,
) -> Vec<OtherContainer> {
    list_volume_groups_output
        .lines()
        .filter_map(|line| {
            let idx = line.find("Volume Group ")?;
            let rest = &line[idx + "Volume Group ".len()..];
            let uuid = rest.split_whitespace().next()?;
            Some(uuid.to_string())
        })
        .filter(|uuid| uuid != target_vg)
        .map(|volume_group_uuid| OtherContainer {
            volume_group_uuid,
            security_mode: SecurityMode::Unknown,
        })
        .collect()
}

/// `Authenticated Root status: enabled` from `csrutil authenticated-root status` →
/// `Some(true)`/`Some(false)` on an exact, anchored match of the one status line;
/// `None` on anything else, so an unrecognised future wording fails closed instead of
/// silently guessing. Replaces an earlier whole-blob `.contains("enabled")` scan
/// (`vuln_res/sweep-reports/2026-11-10-001-recon-verification/ssv-enabled-contains-whole-blob.md`)
/// that had no fail-closed branch at all — this follows the same anchor-to-the-line
/// discipline `extract_volume_group`/`extract_serial_masked` already use below.
fn parse_ssv_enabled(csrutil_output: &str) -> Option<bool> {
    let line = csrutil_output
        .lines()
        .find(|l| l.to_lowercase().contains("status"))?;
    match line.split(':').nth(1)?.trim().to_lowercase().as_str() {
        "enabled" => Some(true),
        "disabled" => Some(false),
        _ => None,
    }
}

/// Best-effort parse of `bputil -d`'s "OS Type"-adjacent "Security Mode" line. Field names
/// are known to vary across macOS builds (see `env.rs` module doc and the per-generation
/// fixtures work scheduled for P5) — an unrecognised value degrades to `Unknown` rather than
/// guessing, consistent with "Deterministic parsing" in `spec/build-spec.md`.
fn parse_security_mode(bputil_output: &str) -> SecurityMode {
    let lower = bputil_output.to_lowercase();
    if lower.contains("security mode: full") || lower.contains("security mode (csec): 0") {
        SecurityMode::Full
    } else if lower.contains("permissive") {
        SecurityMode::Permissive
    } else if lower.contains("reduced") {
        SecurityMode::Reduced
    } else {
        SecurityMode::Unknown
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn extracts_last_four_of_serial() {
        let sample = "      Serial Number (system): DMFJD27H79";
        assert_eq!(extract_serial_masked(sample), Some("7H79".to_string()));
    }

    #[test]
    fn extracts_volume_group_uuid() {
        let sample = "   APFS Volume Group:         45C6EEFD-B3BB-4D5F-B572-D672089BCBBD\n";
        assert_eq!(
            extract_volume_group(sample),
            Some("45C6EEFD-B3BB-4D5F-B572-D672089BCBBD".to_string())
        );
    }

    #[test]
    fn missing_volume_group_line_yields_none() {
        assert_eq!(extract_volume_group("nothing relevant here"), None);
    }

    // Fixtures harness (spec/phased-plan.md P0 workstream): parse the real, redacted
    // captures committed under tests/fixtures/, not just inline strings.

    #[test]
    fn parses_real_system_profiler_fixture() {
        let fixture = include_str!("../../tests/fixtures/system_profiler_hardware_REDACTED.txt");
        // The redaction placeholder itself is what's parsed here, not a real serial — the
        // point of this test is proving the line format is parsed, not recovering a secret.
        assert_eq!(extract_serial_masked(fixture), Some("IAL>".to_string()));
    }

    #[test]
    fn parses_m6_firmware_template_system_profiler_fixture() {
        // Same line format, a second (M6-generation) chip — from
        // plans/research-environment.md's real IPSW research, not a live device (no M6
        // Mac exists to have run system_profiler on; see the fixture's own filename and
        // tests/fixtures/README.md for what "_FIRMWARE_TEMPLATE" means).
        let fixture =
            include_str!("../../tests/fixtures/system_profiler_hardware_M6_FIRMWARE_TEMPLATE.txt");
        assert_eq!(extract_serial_masked(fixture), Some("ARE>".to_string()));
    }

    #[test]
    fn parses_real_diskutil_fixture() {
        let fixture = include_str!("../../tests/fixtures/diskutil_info_root_REDACTED.txt");
        assert_eq!(
            extract_volume_group(fixture),
            Some("<REDACTED-UUID>".to_string())
        );
    }

    #[test]
    fn excludes_the_target_volume_group_and_parses_others() {
        // Hand-built, clearly not a real capture (see filename) — this dev machine only has
        // one real volume group, so the exclusion branch of extract_other_containers has
        // nothing real to exercise it. Structure matches
        // diskutil_apfs_listVolumeGroups_REDACTED.txt's real format.
        let synthetic =
            include_str!("../../tests/fixtures/diskutil_apfs_listVolumeGroups_SYNTHETIC_multi.txt");
        let others = extract_other_containers(synthetic, "22222222-2222-2222-2222-222222222222");
        assert_eq!(others.len(), 1);
        assert_eq!(
            others[0].volume_group_uuid,
            "44444444-4444-4444-4444-444444444444"
        );
        assert_eq!(others[0].security_mode, SecurityMode::Unknown);
    }

    #[test]
    fn parses_real_single_volume_group_fixture_and_finds_nothing_other_than_target() {
        let fixture =
            include_str!("../../tests/fixtures/diskutil_apfs_listVolumeGroups_REDACTED.txt");
        // Redaction zeroed every UUID, including the one real volume group — so with that
        // same zeroed UUID as the target, nothing "other" should be found.
        let others = extract_other_containers(fixture, "00000000-0000-0000-0000-000000000000");
        assert!(others.is_empty());
    }

    #[test]
    fn no_volume_group_lines_yields_empty() {
        assert!(extract_other_containers("nothing relevant here", "any-uuid").is_empty());
    }

    #[test]
    fn parses_real_csrutil_authenticated_root_enabled_fixture() {
        let fixture = include_str!("../../tests/fixtures/csrutil_authenticated_root_status.txt");
        assert_eq!(parse_ssv_enabled(fixture), Some(true));
    }

    #[test]
    fn recognises_disabled_status() {
        assert_eq!(
            parse_ssv_enabled("Authenticated Root status: disabled"),
            Some(false)
        );
    }

    #[test]
    fn trailing_unrelated_text_does_not_flip_the_anchored_result() {
        // The regression case this fix exists for: a line unrelated to the actual status
        // that happens to contain the substring "enabled" must NOT flip the result. The
        // old `stdout.to_lowercase().contains("enabled")` implementation would have
        // returned `true` here (wrong — status is actually disabled); anchoring to the
        // one line containing "status" and matching it exactly gives the correct `false`
        // regardless of what else appears in the output.
        let real_status_plus_unrelated_text = "Authenticated Root status: disabled\n\
             (root filesystem signing can be enabled via csrutil enable)";
        assert_eq!(
            parse_ssv_enabled(real_status_plus_unrelated_text),
            Some(false)
        );
    }

    #[test]
    fn a_status_line_with_an_unrecognised_value_fails_closed() {
        // Unlike the case above (a real status line plus unrelated trailing text), this
        // is the actual fail-closed case: the status line itself has a value that is
        // neither "enabled" nor "disabled" — e.g. a future macOS build renaming the
        // state. There is no safe guess here, so this must be `None`, not a silent
        // default in either direction.
        assert_eq!(
            parse_ssv_enabled("Authenticated Root status: partially-enabled"),
            None
        );
    }

    #[test]
    fn garbage_ssv_output_fails_closed() {
        assert_eq!(parse_ssv_enabled("nothing relevant here"), None);
    }

    #[test]
    fn unrecognised_bputil_output_is_unknown_not_guessed() {
        assert_eq!(
            parse_security_mode("garbage output from an unsupported build"),
            SecurityMode::Unknown
        );
    }

    #[test]
    fn permissive_keyword_is_recognised() {
        assert_eq!(
            parse_security_mode("Security Mode: Permissive"),
            SecurityMode::Permissive
        );
    }
}
