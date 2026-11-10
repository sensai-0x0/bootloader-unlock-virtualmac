---
name: cargo-audit-cargo-deny-not-installed
type: dependency-check
description: cargo audit and cargo deny are absent from this host; dependency advisory scan hasn't run yet
updated: 2026-11-10
---

Confirmed absent from `PATH` on this host as of 2026-11-10 (`which cargo-audit`,
`cargo audit --version`, `which cargo-fuzz`, `cargo fuzz --version` all failed to
resolve). Neither tool has been installed, per the root `../../CLAUDE.md`'s "never
impact the host machine" rule and this folder's own restatement of it — installing
either is a host-level change that needs explicit user go-ahead first, not assumed.

So: `Cargo.toml`'s dependency set (`image4 0.8.2`, `der 0.7`, `time 0.3.36`, `clap
4.5.20`, `serde 1.0.214`, `serde_json 1.0.132`, `thiserror 2.0.3`, `sha2 0.10.8`, `hex
0.4.3`) has **not** been checked against the RustSec advisory database by this suite.
`vuln_res/AUDIT.md` §4's assessment ("`time` is past the versions affected by
RUSTSEC-2020-0071") is a manual read of the version number, not a machine-verified
check. First real `vulnres-recon` sweep that gets `cargo audit`/`cargo deny` approved and
installed should update this entry with an actual scan result.
