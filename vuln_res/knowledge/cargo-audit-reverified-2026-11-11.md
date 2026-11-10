---
name: cargo-audit-reverified-2026-11-11
type: dependency-check
description: cargo audit re-run against the current Cargo.lock (unchanged since the initial commit), still 0 vulnerabilities, now against 1446 advisories; cargo deny check attempted for the first time and found a license-policy config gap, not a vulnerability
updated: 2026-11-11
---

Corrects this task's own briefing, which assumed `cargo audit`/`cargo deny` were "absent
from this host today" — that was true as of `../AUDIT.md`'s 2026-11-10 writing, but both
were already installed with user approval later that same day
([[cargo-audit-cargo-deny-not-installed]]). No new install was needed or performed this
sweep.

- `git log --oneline -- Cargo.lock` shows exactly one commit ever touched the lockfile
  (the initial P0 import) — dependencies have not moved since the 2026-11-10 scan.
- `cargo audit`: loaded 1446 advisories (up from 1439 on 2026-11-10 — the upstream
  RustSec DB itself grew), scanned the same 66 crate dependencies, **exit 0, zero
  vulnerabilities**. Re-confirms [[cargo-audit-cargo-deny-not-installed]]'s conclusion
  against a fresher advisory snapshot.
- `cargo deny check` (first run ever against this repo — the prior sweep noted no
  `deny.toml` exists and left it for a follow-up): ran successfully without a config file
  present. Result: **advisories ok, bans ok, sources ok, licenses FAILED** — two
  dependencies (`windows-sys` v0.61.2 and `zmij` v1.0.23, both MIT/Apache-2.0-licensed,
  both already-known crates in this tree) are rejected because `cargo-deny`'s *default*
  policy without an explicit `[licenses] allow` list permits nothing. This is a missing
  policy declaration, not a real license-compliance problem — both crates carry
  standard, unproblematic OSS licenses.

**Recommendation, not performed this sweep:** add a `deny.toml` at the repo root with an
explicit `[licenses] allow = ["MIT", "Apache-2.0", ...]` list (enumerate the actual set
seen in this run) so `cargo deny check licenses` has a real policy to evaluate against
instead of failing on "nothing is allow-listed yet." Not done here because the repo root
is outside this agent's scoped write directories for this task (`src/`, `scripts/`,
`tests/fixtures/`, `vuln_res/` only) — left for the next sweep or a direct user/maintainer
action.
