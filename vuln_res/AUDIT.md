# Security audit — bputil-eval (as of 2026-11-10)

Scope: the Rust source under `../src/`, the CI guard script (`../scripts/ci_guards.sh`),
the dependency set (`../Cargo.toml`/`Cargo.lock`), and the repo's data footprint outside
the binary (`../research/`). This is a defensive code review — nothing here was run
against a real device, and no exploit was constructed against anything. Per
`CLAUDE.md` in this folder, findings against Apple's own platform security are out of
scope by design; what follows is about this repo's own code and its blast radius.

All file:line references are against the commit at HEAD (`1b37d16`) when this audit was
written; re-check line numbers if the code has moved.

## Summary

The codebase is small (1,853 lines across 11 files), already has 43 passing tests, a
working CI guard against bypassing the audited subprocess wrapper, and a genuinely
good security property: every mutation path is gated behind `env::is_mutation_allowed()`
and nothing mutating is implemented yet (P3+ is stubbed). That's the right place to be
before shipping `apply`/`revert`. The findings below are not "this tool is broken" — they're
the kind of thing a vuln-research pass is supposed to surface *before* P3 lands, while the
cost of fixing them is still low.

Three categories, ordered by what a research-agent suite should go after first:

1. **Parser robustness (highest value for fuzzing)** — `state/img4.rs`'s DER decode path
   and `main.rs`'s `verify --baseline <path>` JSON deserialization are the two places this
   binary parses bytes it did not produce itself. Neither has been fuzzed; both are good,
   cheap fuzz targets because they're already pure functions with no side effects.
2. **Brittle text-parsing of security-relevant state (logic risk, not memory-safety)** —
   several places decide a security-relevant fact (`Environment`, `SecurityMode`) by
   substring-matching free-form CLI output. This is a correctness/robustness risk the
   project's own docs already partially acknowledge; it's worth a systematic review, not
   just the one instance they flagged.
3. **CI guard coverage gaps** — the two textual guards in `ci_guards.sh` are regexes, and
   regexes have blind spots. Worth hardening before P3 adds more surface for a mutating
   code path to slip past them.

Plus one standing item inherited from the repo root, re-flagged here because it's directly
relevant to anything `vuln_res/` touches: real Apple firmware and an 18.8 GB IPSW already
sit on this host's disk, unresolved. See "Inherited host-impact item" below.

## 1. Parser robustness

### 1.1 `state/img4.rs::parse_manifest_der` — unfuzzed DER decode of untrusted bytes

`parse_manifest_der` (`src/state/img4.rs:44`) calls `Manifest::from_der` from the
`image4` crate, and `facts()` (`:57`) calls `manifest.decode_body()`. Both are exactly the
shape of function a fuzzer is good at: pure, deterministic, no I/O, parse arbitrary bytes.
Today they're exercised only by three unit tests — malformed input, empty input, and one
real signed manifest fixture (`tests/fixtures/image4_apticket.der`). That's enough to prove
the happy/sad path works, but not enough to find the kind of bug fuzzing finds: an
unusual-but-valid-looking DER length field that causes a large allocation, a decode that
recurses deeper than expected, or a panic in `image4`/`der` itself on a byte pattern no one
thought to write a unit test for.

This is not wired into `state::collect`'s production path yet (`#[cfg_attr(not(test),
allow(dead_code))]` at `:43`, `:50`, `:56`) — which is actually the best time to fuzz it:
any crash found now is a pure library/glue bug, with zero risk of interacting with a real
device.

**Recommendation:** `vuln_res/plans/02-fuzzing-harness-agent.md` — a `cargo fuzz` target
wrapping `parse_manifest_der` + `facts`, seeded from the existing fixture plus any
publicly-available sample IM4M manifests, run under ASan.

### 1.2 `main.rs::cmd_verify` — `serde_json::from_str::<BootState>` on a user-supplied file

`src/main.rs:174` deserializes an arbitrary file (`--baseline <path>`) into `BootState`
with no size cap and no depth cap beyond what `serde_json` itself enforces. `BootState`
(`src/state/mod.rs`) contains nested `Vec`s (`enrolled_objects`, `other_containers`,
`evidence.raw_outputs`), so a crafted JSON file with deep nesting or very large arrays is
a cheap local denial-of-service vector (stack exhaustion or memory exhaustion) against
whoever runs `verify` against a file they didn't produce themselves — e.g. a baseline
someone emailed you, or a baseline fetched as part of an automated pipeline.

Severity is low in practice (this is a local CLI tool, not a network service, and the
project's own threat model doesn't include "run verify against a baseline from an
untrusted party" today) — but it's exactly the kind of boundary `spec/build-spec.md`'s
"validate all external data" principle (mirrored in the root `CLAUDE.md`'s global coding
rules) is about, and it costs almost nothing to harden: a size check on the file before
parsing, and/or `serde_json`'s own recursion-limit configuration.

**Recommendation:** add to `vuln_res/plans/02-fuzzing-harness-agent.md`'s target list —
fuzz `cmd_verify`'s deserialization path directly (or `BootState`'s `Deserialize` impl in
isolation) with arbitrary bytes, and open a small hardening PR against `main.rs` (file-size
guard before `read_to_string`) as a first "found and fixed" proof of the pipeline in
`vuln_res/plans/04-disclosure-and-fix-agent.md`.

## 2. Brittle text-parsing of security-relevant state

This project already acknowledges one instance of this risk in its own doc comments
(`src/env.rs:1-18`, `src/state/collect.rs:197-200`): Apple's CLI tool output format for
`bputil -d` isn't guaranteed stable, so the code **fails closed** when it can't positively
confirm a state. That design choice is correct and should be preserved. But the specific
matching logic is worth a second look, because substring matching on free-text output is
a known class of bug (a string being a *superset* match for the wrong reason):

- `src/env.rs:72`: `os_type_line.to_lowercase().contains("one true recoveryos")`. If a
  future macOS build's "OS Type" line reads something like `"OS Type: NOT one true
  recoveryOS (fallback)"` — a negation Apple's own string formatting could plausibly add —
  this still matches and misclassifies a fallback-recovery environment as `OneTrueRecovery`.
  Today's two real-world strings ("one true recoveryOS" / "ordinary recovery OS") don't
  collide, so this isn't exploitable *yet*, but it's a parsing pattern that will eventually
  need a real state machine or anchored match (e.g. `line.trim() ==` against a known-good
  set) rather than `contains`, especially since `env.rs`'s own doc comment already flags
  that this string "has not been 100% consistent across OS builds."
- `src/state/collect.rs:203-208` (`parse_security_mode`): same pattern, four `contains`
  checks in sequence (`"security mode: full"`, `"permissive"`, `"reduced"`) against
  lower-cased full stdout, not just the relevant line. A device/model string, a localized
  build, or a future `bputil` verbose-mode addition that happens to contain the substring
  `"permissive"` anywhere in its output (e.g. in a help/description string bundled into
  `-d`'s output) would misclassify `SecurityMode` silently — and `SecurityMode` is the
  single field `plan()` (`src/plan.rs:83`) uses to decide what's "legal" to transition to.
  This doesn't currently fail closed the way `env.rs`'s version does — there's no
  "unrecognised, treat as error" branch ahead of the `contains` chain, only after it
  (the final `else => Unknown` only catches zero matches, not a wrong match caused by
  checking the whole blob instead of one line).

**Recommendation:** `vuln_res/plans/01-static-analysis-and-dependency-agent.md` should
include a standing grep/semantic rule that flags any new `contains(...)` match against
CLI output feeding a `SecurityMode`/`Environment`/other security-relevant enum, and ask
for either an anchored per-line match or an explicit allow-list test. This is a cheap,
high-value static check to automate rather than re-review by hand every time `collect.rs`
or `env.rs` changes.

## 3. CI guard coverage gaps (`scripts/ci_guards.sh`)

Both guards are correct for the cases they were written against, and both have a grep
syntax gap worth closing before P3 adds more subprocess call sites:

- **Guard 1** (`scripts/ci_guards.sh:16-17`) matches `Command::new(` only when preceded by
  whitespace (`[[:space:]]Command::new\(`) or by the full `std::process::Command` path.
  A call written as `(Command::new("x"))`, `[Command::new("x")]`, or
  `foo(Command::new("x"))` — preceded by `(`, `[`, or nothing after an opening delimiter,
  not whitespace — would not match either alternative and would slip past the guard
  undetected. This is the exact textual gap the guard exists to close, so it's worth
  closing the regex itself (e.g. requiring any non-identifier boundary, `(^|[^A-Za-z0-9_])`,
  rather than specifically whitespace).
- **Guard 2** (`scripts/ci_guards.sh:29`) only matches credential-shaped fields whose type
  is exactly `String | &str | Vec<u8> | [u8]` on a single line ending at `$`. A field typed
  `Option<String>`, a type alias, or a declaration whose type wraps to the next line would
  not match, while still being exactly the kind of credential-shaped field golden rule 4
  and the `NoCredentialHandling` invariant are meant to catch.

Neither gap has been exploited — there is no credential field in the codebase today, and
no subprocess call outside `wrapper.rs`. This is a "the guard is weaker than it looks"
finding, worth fixing precisely because the guard is supposed to be the thing that catches
a mistake in P3/P4 (`authorize`/`execute`), which is unwritten today and is where a
credential-shaped field would be most likely to first appear.

**Recommendation:** `vuln_res/plans/01-static-analysis-and-dependency-agent.md` — treat
`ci_guards.sh` itself as a reviewed artifact, with its own negative-test corpus (inputs
that *should* be caught and currently aren't), not just a script trusted because it's green.

## 4. Dependency surface

`Cargo.toml` pulls in `image4` (0.8.2) and `der` (0.7) for IMG4/DER parsing — both are
niche, lower-download crates relative to `serde`/`clap`, which generally means less
real-world fuzzing has already happened against them upstream. `time` (0.3.36) is well
past the versions affected by the historical `RUSTSEC-2020-0071` segfault advisory, but
this hasn't been machine-verified against the current advisory database in this repo.

**Recommendation:** `vuln_res/plans/01-static-analysis-and-dependency-agent.md` — run
`cargo audit` / `cargo deny` against `Cargo.lock` on a schedule. Neither tool is installed
on this host today (confirmed: `cargo-audit`/`cargo-fuzz` both absent from `PATH`), so
installing them is a host-level change that needs the same stop-and-ask the root
`CLAUDE.md` requires — this audit does not install them, it only identifies them as the
right tools for the job.

## 5. Things that are *not* findings (confirmed, not just assumed)

Worth stating explicitly so a future pass doesn't re-litigate these:

- `wrapper::run` (`src/wrapper.rs:43`) uses `Command::new(argv0).args(&argv[1..])` —
  argv-array execution, never a shell string. There is no shell-injection surface here;
  every `argv` passed in is a `&[&str]` literal at the call site, not concatenated from
  user input anywhere in this codebase.
- No module outside `wrapper.rs` calls `std::process` (confirmed by `ci_guards.sh` passing
  today, and by direct `grep` across `src/`), so the "one audited subprocess" invariant
  currently holds in practice, independent of the regex gaps noted in §3.
- No credential-shaped field exists in the codebase today (confirmed by `grep -iE
  '(password|passwd|credential|secret|owner_pin|recovery_key)'` across `src/` returning
  nothing beyond doc-comment prose).
- `plan()` (`src/plan.rs:82`) never executes anything — it returns data (`PlannedTransition`)
  and every test (`src/plan.rs:217-367`) confirms the state machine only permits the
  documented edges (`Full -> {Reduced, Permissive}`, both back to `Full` only).

## Inherited host-impact item (not new, but directly in `vuln_res/` scope)

The root `CLAUDE.md` already flags, unresolved: `blacktop/ipsw` and `tart` installed via
Homebrew, plus two macOS restore images downloaded to this host's disk. Confirmed still
present during this audit:

- `research/ipsw_downloads/UniversalMac_26.3_25D125_Restore.ipsw` — **18.8 GB**
- `research/26B7124__MacOS/Firmware/all_flash/` — real, extracted Apple firmware
  (`iBoot.j804.RELEASE.im4p`, `iBoot.j833ct.RELEASE.im4p`, `iBootData*.im4p`,
  `DeviceTree*.im4p`) and a real `kernelcache.release.Mac18,1_2`.

This matters directly for `vuln_res/`: these are real firmware binaries, already on disk,
already structurally similar to what a fuzzer corpus would want to seed from. `vuln_res/
CLAUDE.md` names this path explicitly and permits reading these files for *structural*
corpus-seeding only (confirming a parser handles real-world byte layouts) — never as an
attack target. That line is easy to blur by accident once a fuzzing agent exists and is
looking for "real" inputs, so it's called out here too, not just in the root file. The
cleanup decision itself (keep or remove `blacktop/ipsw`, `tart`, and the cached images)
is still the user's to make and is unchanged by this audit.
