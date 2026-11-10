#!/usr/bin/env bash
# CI guard checks from spec/phased-plan.md's "CI gates" section (P0 exit gate):
#   1. No std::process call outside the audited wrapper (src/wrapper.rs).
#   2. No credential-shaped field anywhere in the codebase.
# A third standing guard — "no mutating path is reachable without is_mutation_allowed()
# returning true" — is enforced by tests (src/env.rs, src/wrapper.rs), not by grep, since it
# is a behavioural property, not a textual one.
#
# Run from the repo root (the-ant-experiment/). Exits non-zero on the first violation found.

set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

fail=0

echo "== Guard 1: Command::new / std::process::Command only inside src/wrapper.rs =="
# Matches the actual subprocess-spawning API, not doc-comment mentions of "std::process" or
# unrelated types like std::process::ExitCode. The `Command::new(` alternative is anchored
# on a non-identifier boundary `(^|[^A-Za-z0-9_])`, not just whitespace: a call written as
# `(Command::new("x"))`, `[Command::new("x")]`, or `foo(Command::new("x"))` is preceded by
# `(`, `[`, or nothing after an opening delimiter — none of which is whitespace — and a
# whitespace-only check missed all three (vuln_res/AUDIT.md §3's Guard 1 finding; see
# scripts/ci_guards_selftest.sh for the corpus this was verified against). The boundary
# still excludes a type name that merely ends in "Command" (e.g. `FooCommand::new(`), since
# the character immediately before "Command" there is an identifier character, not matched
# by `[^A-Za-z0-9_]`.
GUARD1_PATTERN='(std::process::Command|(^|[^A-Za-z0-9_])Command::new\()'
if grep -rnE --include='*.rs' "$GUARD1_PATTERN" src \
    | grep -v '^src/wrapper.rs:' \
    | grep -vE '^[^:]+:[0-9]+:[[:space:]]*//'; then
    echo "FAIL: a process was spawned outside src/wrapper.rs"
    fail=1
else
    echo "OK"
fi

echo
echo "== Guard 2: no credential-shaped field anywhere =="
# Case-insensitive match on identifier-ish tokens that would indicate the tool is holding
# an owner credential, which spec/build-spec.md's golden rule 4 and
# spec/contract-spec.md's NoCredentialHandling invariant both forbid outright. Matches on
# struct/field declarations and let-bindings; a plain string literal describing a CLI flag
# (e.g. "-p, --password") is not itself a stored credential field, so this only flags
# Rust binding/field syntax, not documentation strings. The type alternation also matches an
# `Option<...>`-wrapped credential-shaped field (`Option<String>` etc.) — the previous
# version only matched the bare types, missing exactly the shape an optional credential
# field would realistically take (vuln_res/AUDIT.md §3's Guard 2 finding).
GUARD2_TYPE_PATTERN='(Option<)?(String|&str|Vec<u8>|\[u8\])>?'
if grep -rnE --include='*.rs' "(let[[:space:]]+(mut[[:space:]]+)?|pub[[:space:]]+)?[a-zA-Z_][a-zA-Z0-9_]*[[:space:]]*:[[:space:]]*${GUARD2_TYPE_PATTERN}[[:space:]]*,?[[:space:]]*(//.*)?\$" src | grep -iE '(password|passwd|credential|secret|owner_pin|recovery_key)[a-zA-Z0-9_]*[[:space:]]*:'; then
    echo "FAIL: a credential-shaped field was found"
    fail=1
else
    echo "OK"
fi

exit "$fail"
