---
id: 2026-11-11-001-host-independent-parsing-hardening/ci-guards-regex-boundary-gaps
target: scripts/ci_guards.sh (pre-fix, both guards)
source: static-analysis (re-derived from vuln_res/AUDIT.md §3, not previously fixed)
status: fixed
score: n/a (tooling/process finding, not a bug in the shipped binary — scored like the
  other operational entry in this index, `agent-registry-not-live-this-session`)
discovered_by: vulnres-recon-style static review (prior sweep, `vuln_res/AUDIT.md` §3);
  fixed in this sweep
sweep: ../INDEX.md#2026-11-11-001-host-independent-parsing-hardening
discovered_at: 2026-11-10 (AUDIT.md); fixed 2026-11-11
---

## Short description

Both of `scripts/ci_guards.sh`'s textual guards had a regex gap that would let exactly the
thing they're meant to catch slip through undetected, in specific shapes. Neither gap has
ever been exploited (no violating code exists in this repo today), but a guard that's
*weaker than it looks* is itself a finding — it's supposed to be the thing that catches a
mistake in the not-yet-written P3/P4 mutation modules (`authorize`/`execute`), which is
exactly where a credential-shaped field or an un-wrapped subprocess call would be most
likely to first appear.

## Technical detail

**Guard 1** (`Command::new\(` / `std::process::Command` detection) required the call to be
preceded by whitespace or the fully-qualified path. `(Command::new("x"))`,
`[Command::new("x")]`, or `foo(Command::new("x"))` — preceded by `(`, `[`, or nothing after
an opening delimiter, none of which is whitespace — would not match either alternative.

**Guard 2** (credential-shaped field detection) only matched a field whose type was exactly
`String | &str | Vec<u8> | [u8]`. A field typed `Option<String>` — a very plausible shape
for an optional credential field — would not match, despite being exactly the kind of
field golden rule 4 and the `NoCredentialHandling` invariant exist to catch.

## Reproduction

`scripts/ci_guards_selftest.sh` (new in this sweep) is the reproduction: it runs both
guards' exact regexes (copied verbatim from `ci_guards.sh`, not re-derived, so the test
proves the deployed pattern) against a small corpus of lines, including every gap case
above, and asserts each one is caught. Run it directly:

```
$ ./scripts/ci_guards_selftest.sh
```

Against the pre-fix regexes, the "(the gap)"-labeled cases in that script's output would
have failed to match (confirmed by hand before writing the fix — the corpus lines are
taken directly from `AUDIT.md` §3's own examples).

## Classification

- **Type:** guard/tooling weakness (the guard itself, not the code it guards)
- **Reachability:** n/a — no violating code exists in this repo today; this is about
  whether a *future* mistake would be caught
- **Blast radius:** n/a — same reasoning

## Resolution

**Fixed directly:**

- Guard 1's `Command::new\(` alternative now uses a non-identifier-boundary check
  (`(^|[^A-Za-z0-9_])Command::new\(`) instead of requiring literal whitespace — catches all
  three gap shapes while still correctly excluding a type that merely *ends* in "Command"
  (e.g. `FooCommand::new(`, where the preceding character is an identifier character).
- Guard 2's type alternation now also matches `Option<String>`/`Option<&str>`/
  `Option<Vec<u8>>`/`Option<[u8]>` via `(Option<)?(String|&str|Vec<u8>|\[u8\])>?`, not just
  the four bare types.
- `scripts/ci_guards_selftest.sh` added: a negative-test corpus proving both fixes actually
  close the described gaps (not part of the normal CI gate — `ci_guards.sh` itself is; this
  is run manually when either guard's pattern changes, per `AUDIT.md` §3's own
  recommendation to "treat `ci_guards.sh` itself as a reviewed artifact, with its own
  negative-test corpus").
- Verified: `./scripts/ci_guards.sh` still green against this repo's real tree,
  `./scripts/ci_guards_selftest.sh` all-pass against the new corpus.
