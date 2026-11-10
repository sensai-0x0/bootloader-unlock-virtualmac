---
name: cargo-audit-cargo-deny-not-installed
type: dependency-check
description: cargo audit and cargo deny installed 2026-11-10 with user go-ahead; audit scan is clean (0 vulnerabilities, 66 crates)
updated: 2026-11-10
---

**Resolved, 2026-11-10:** user approved the host-level install; both tools are now on
this host (`~/.cargo/bin/cargo-audit`, `~/.cargo/bin/cargo-deny`), consistent with the
root `../../CLAUDE.md`'s "never impact the host machine without explicit go-ahead" rule —
asked first, installed only after approval.

`cargo audit` run against this repo's `Cargo.lock`: loaded 1439 advisories from
`RustSec/advisory-db`, scanned 66 crate dependencies, **exit 0, zero vulnerabilities
found**. This supersedes `vuln_res/AUDIT.md` §4's manual version-number read ("`time` is
past the versions affected by RUSTSEC-2020-0071") with an actual machine-verified
advisory-DB match — same conclusion, now confirmed rather than inferred.

`cargo deny check` (license/advisory/ban policy) has not yet been run — no
`deny.toml` exists in this repo yet, so a first run would need either a generated
default config or an explicit policy decision (which licenses/sources to allow) before
it produces a meaningful result. Left for a follow-up `vulnres-recon` sweep rather than
assuming a policy on the user's behalf.
