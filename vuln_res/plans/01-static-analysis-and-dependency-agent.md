# 01 — Static analysis & dependency agent

The fastest, cheapest stage. No campaign, no sandbox — just running tools that already
exist against code that already exists, plus one custom agent for the project-specific
pattern `AUDIT.md` §2 found (brittle substring-matching of security-relevant CLI output).

## Components

### 1.1 Dependency/SBOM scan (`cargo audit` + `cargo deny`)

Neither tool is installed on this host today (confirmed during the audit). Installing
them is a host-level change — **ask the user first**, per the root `CLAUDE.md`'s "never
impact the host machine" rule and this folder's own restatement of it. Once approved:

- `cargo audit` against `Cargo.lock` — checks the pinned `image4`, `der`, `time`, `clap`,
  `serde`, `thiserror`, `sha2`, `hex` versions against the RustSec advisory database.
- `cargo deny check advisories bans licenses` — same advisory check plus a license-
  compliance pass (useful since this is an MIT-licensed tool with an eye toward being
  shared).
- Run as a one-shot first, then wire into CI (`06-orchestration-and-scheduling.md`) on a
  schedule — dependency advisories get published after the fact, so this needs to be
  periodic, not just a one-time check.

**Agent role:** a narrow "dependency-auditor" agent whose only job is: run the scan,
parse the output, and open one finding per new advisory with the affected crate, the
advisory ID, whether `bputil-eval` actually calls the vulnerable code path (not just
whether the crate is in the dependency tree), and a suggested `Cargo.toml` version bump.

### 1.2 `cargo clippy --all-targets -- -D warnings` + `cargo fmt --check`

Already part of the project's own CI per `CLAUDE.md`'s "Commands" section — nothing new
to build here, just confirm it's still wired into whatever runs this suite's checks
(`06-orchestration-and-scheduling.md`).

### 1.3 The project-specific static check: security-relevant `contains()` matches

`AUDIT.md` §2 found that `env.rs` and `state/collect.rs` both decide a security-relevant
enum value (`Environment`, `SecurityMode`) via `str::contains()` against multi-line CLI
tool output, which is a substring-match — not an anchored, structured parse. This is a
reusable pattern worth a standing check rather than a one-time fix, because P3/P4 will add
more CLI-output parsing (`authorize`, `execute`, `verify`'s real invariant assertions) that
could reintroduce the same shape of bug.

**Build this as a small custom lint agent**, not a generic grep one-liner, because the
judgment call ("is this match feeding a security-relevant type?") needs more context than
a regex has:

1. Agent reads every `wrapper::run(...)` call site and traces where its `CommandRecord`'s
   `stdout`/`stderr` flows.
2. Flags any flow that ends in a `.contains(...)` test feeding a value assigned into a
   field of `Environment`, `SecurityMode`, or (once P3 lands) anything gating
   `is_mutation_allowed()`.
3. For each flagged site, check: is there a fail-closed `else` branch (good, like
   `env.rs`'s `UnconfirmedRecoveryVariant`), or does an unmatched/mismatched case silently
   fall through to a default (bad, like the gap in `parse_security_mode`'s checking the
   whole blob instead of the one relevant line)?
4. Emit one finding per flagged site with a suggested fix shape: anchor to the specific
   line (`.lines().find(|l| l.starts_with("Security Mode"))` style, matching what
   `extract_volume_group`/`extract_serial_masked` in the same file already do correctly)
   rather than scanning the whole output blob.

This doubles as a **regression test generator**: for each site it clears, it can propose
a unit test fixture with a deliberately-adjacent-but-wrong string (e.g. `"Rebuilding:
permissive mode support (not active)"`) to prove the parser doesn't false-positive on it —
closing exactly the gap `AUDIT.md` §2 described.

### 1.4 CI-guard hardening (`scripts/ci_guards.sh`)

Per `AUDIT.md` §3, both regex guards have a syntax gap. Fix:

- Guard 1: broaden `[[:space:]]Command::new\(` to a non-identifier-boundary match (e.g.
  ``(^|[^A-Za-z0-9_])Command::new\(``) so a call preceded by `(`, `[`, `,`, etc. is still
  caught.
- Guard 2: either loosen the type-pattern alternation to also match `Option<String>` /
  `Option<&str>` / `Option<Vec<u8>>`, or (better, since regexes will always have a blind
  spot here) add a second, AST-aware check using `syn` to parse every struct/enum field
  declaration and flag credential-shaped names regardless of exact type wrapping.
- Add a **negative-test corpus**: a small fixture file (not compiled into the binary,
  just sitting under `scripts/ci_guard_fixtures/`) containing deliberately-evasive examples
  of both violations, with a test asserting the guard script's exit code is non-zero
  against each one. This is what turns "the guard passes" into "the guard was proven to
  catch the thing it's for."

## Exit gate

- `cargo audit`/`cargo deny` run once (after explicit host-install approval) with zero
  unaddressed advisories, or each addressed advisory has a tracked follow-up.
- The security-relevant-`contains()` lint agent has run once against the current codebase
  and either found nothing new beyond `AUDIT.md`'s two documented instances, or those two
  have fix PRs opened.
- `ci_guards.sh`'s negative-test corpus exists and both guards correctly fail against it.
