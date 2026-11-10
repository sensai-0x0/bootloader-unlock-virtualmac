# Phase 0 — Foundations: remaining steps

Status: CI, the audited wrapper, and the fixtures harness are implemented and passing
(`cargo test`, `cargo clippy --all-targets -- -D warnings`, `cargo fmt --check`,
`./scripts/ci_guards.sh`). Item 1 below is now done. Item 2 needs a human and is not
something an agent can complete unattended — it's left open on purpose, not forgotten.

## 1. ~~Prove the IMG4 parser against a real manifest, not just malformed input~~ — done

`src/state/img4.rs` currently only has negative tests (garbage bytes rejected). The P0
"IMG4 parser spike" workstream calls for proving the parser against a real manifest.

**You don't need to download an IPSW for this.** The `image4` crate we depend on ships its
own real signed IM4M test manifest, and it's already on disk once `cargo build` has run:

```
~/.cargo/registry/src/index.crates.io-*/image4-0.8.2/tests/data/apticket.der
```

(and `apticket_unsigned.der`, `test-cert.der`, `test-key.der` alongside it). The crate is
`MIT OR Apache-2.0` licensed, so vendoring a small fixture from it with attribution is fine.

Steps:
1. Copy `apticket.der` into `tests/fixtures/image4_apticket.der` (binary; add a line to
   `tests/fixtures/README.md`'s provenance table noting it's vendored from the `image4`
   crate's own test suite under MIT/Apache-2.0, not captured from a real device).
2. In `src/state/img4.rs`, add a positive test:
   ```rust
   #[test]
   fn parses_a_real_signed_manifest() {
       let der = include_bytes!("../../tests/fixtures/image4_apticket.der");
       let manifest = parse_manifest_der(der).expect("real manifest should parse");
       let facts = facts(&manifest).expect("body should decode");
       assert!(!facts.signature.is_empty());
       assert!(facts.property_count > 0);
   }
   ```
3. Remove the `#[allow(dead_code)]` on `ManifestFacts`/`facts`/`Img4Error::Decode` now that
   something calls them.
4. Update `src/state/img4.rs`'s module doc comment and `CLAUDE.md`'s "Deviations" entry for
   this item — the "not yet proven against a real manifest" caveat goes away.

Done: `tests/fixtures/image4_apticket.der` is vendored, `src/state/img4.rs` has
`parses_a_real_signed_manifest` passing against it, and `tests/fixtures/README.md`/
`CLAUDE.md` are updated. The `#[allow(dead_code)]` markers are now `cfg_attr(not(test),
allow(dead_code))` rather than removed outright — `parse_manifest_der`/`facts` are
genuinely exercised only by tests until `plans/phase-1.md` item 1's wiring into
`state::collect` lands, so a plain `cargo build` still can't reach them.

## 2. Capture a real `bputil -d` fixture (needs a human, but not an owner-credential one) — open

`bputil -d` requires root. `sudo -n bputil -d` (what `state/collect.rs` calls) will always
fail without a cached `sudo` session, which is correct and intentional — but it means there
is still no real captured fixture for `parse_security_mode` to be tested against, only the
keyword-based unit tests with inline strings in `src/state/collect.rs`.

Steps (human, at a terminal, on any Apple Silicon Mac — ordinary macOS, not 1TR):
1. `sudo bputil -d -j` (or without `-j` for text) and enter your **local admin** password
   when prompted — this is your everyday login password, not an owner/recovery credential,
   and bputil's own prompt handles it; nothing in this repo touches it.
2. Redact anything identifying (there likely isn't much in `-d` output beyond the policy
   itself, but check for a volume UUID and redact it the same way
   `tests/fixtures/README.md` describes for the other fixtures).
3. Save as `tests/fixtures/bputil_display_policy_REDACTED.txt` (and/or a `.json` twin if you
   used `-j`), and add it to the provenance table in `tests/fixtures/README.md`.
4. Add a fixture-driven test in `src/state/collect.rs` alongside
   `parses_real_system_profiler_fixture` that asserts `parse_security_mode` on this real
   output returns the mode you know to be correct for your machine at capture time.

Once this lands, if you're also willing to run `bputil -e` (display all policies) or test on
a second chip generation, drop those in too — per-generation coverage is formally a P5 item,
but there's no reason not to start the collection early if you're already at the terminal.
