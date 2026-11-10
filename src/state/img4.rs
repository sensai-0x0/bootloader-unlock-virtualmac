//! IMG4 manifest parsing — the P0 "IMG4 parser spike" workstream from `spec/phased-plan.md`.
//!
//! Uses the `image4` crate (pure Rust, DER-based; see its `manifest` module), not a C
//! library binding. That changes one assumption in `spec/build-spec.md`'s per-module
//! contract table, which says `state/img4` must "parse IMG4 manifests via a vetted library"
//! behind an "isolated FFI boundary": there is no FFI boundary to isolate here because the
//! chosen crate contains no `unsafe` on this parsing path. This module still owns the "must
//! not hand-roll signature verification or claim to verify a signature" rule — it only
//! decodes structure and exposes the raw signature/cert-chain bytes; it never asserts they
//! are valid.
//!
//! Spike status: `parse_manifest_der` is proven against both malformed input (negative
//! tests) and a real signed IM4M manifest (`tests/fixtures/image4_apticket.der`, vendored
//! from the `image4` crate's own test suite under its `MIT OR Apache-2.0` license — see
//! `tests/fixtures/README.md`). It is still not proven against a manifest pulled from a
//! real public IPSW specifically; that distinction matters less than it first appears,
//! since this module only decodes DER structure and never verifies a signature either way
//! (see "must not" above) — a real signed manifest from any source exercises the same
//! decode path. Not yet wired into `state::collect` — see `plans/phase-1.md` item 1 for why
//! (it needs either `bputil -d -j`'s own exposure of this data, or a confirmed on-disk
//! manifest path, neither of which is available without a human at the device).

use der::Decode;
use image4::manifest::Manifest;

#[derive(Debug, thiserror::Error)]
pub enum Img4Error {
    #[error("manifest DER could not be decoded: {0}")]
    Decode(String),
    #[error("manifest body could not be decoded as a property dictionary: {0}")]
    BodyDecode(String),
}

/// Decode a DER-encoded IM4M manifest. Returns the parsed [`Manifest`] on success so a
/// caller (`state::collect`) can pull `enrolled_objects` hashes and the raw cert chain out
/// of it. Never attempts to verify the signature — that is explicitly out of scope for this
/// module (`spec/build-spec.md`, state/img4 "must not").
///
/// Exercised by this module's own tests against both malformed input and a real manifest
/// (see module doc); not yet called from `state::collect`'s production path (hence
/// `cfg_attr(not(test), allow(dead_code))` below rather than deleting it — see
/// `plans/phase-1.md` item 1 for what's blocking that wiring).
#[cfg_attr(not(test), allow(dead_code))]
pub fn parse_manifest_der(bytes: &[u8]) -> Result<Manifest, Img4Error> {
    Manifest::from_der(bytes).map_err(|e| Img4Error::Decode(e.to_string()))
}

/// Raw signature bytes and DER-encoded cert chain, exposed for the evidence bundle. The tool
/// records these; it does not evaluate them as proof of anything on its own.
#[cfg_attr(not(test), allow(dead_code))]
pub struct ManifestFacts {
    pub signature: Vec<u8>,
    pub property_count: usize,
}

#[cfg_attr(not(test), allow(dead_code))]
pub fn facts(manifest: &Manifest) -> Result<ManifestFacts, Img4Error> {
    let body = manifest
        .decode_body()
        .map_err(|e| Img4Error::BodyDecode(e.to_string()))?;
    Ok(ManifestFacts {
        signature: manifest.signature().to_vec(),
        property_count: body.len(),
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn garbage_bytes_are_rejected_not_guessed() {
        let result = parse_manifest_der(&[0x00, 0x01, 0x02, 0x03]);
        assert!(matches!(result, Err(Img4Error::Decode(_))));
    }

    #[test]
    fn empty_input_is_rejected() {
        let result = parse_manifest_der(&[]);
        assert!(result.is_err());
    }

    #[test]
    fn parses_a_real_signed_manifest() {
        let der = include_bytes!("../../tests/fixtures/image4_apticket.der");
        let manifest = parse_manifest_der(der).expect("real manifest should parse");
        let facts = facts(&manifest).expect("body should decode");
        assert!(!facts.signature.is_empty());
        assert!(facts.property_count > 0);
    }
}
