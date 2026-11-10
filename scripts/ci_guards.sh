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
# unrelated types like std::process::ExitCode.
if grep -rnE --include='*.rs' '(std::process::Command|[[:space:]]Command::new\()' src \
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
# Rust binding/field syntax, not documentation strings.
if grep -rnE --include='*.rs' '(let[[:space:]]+(mut[[:space:]]+)?|pub[[:space:]]+)?[a-zA-Z_][a-zA-Z0-9_]*[[:space:]]*:[[:space:]]*(String|&str|Vec<u8>|\[u8\])[[:space:]]*,?[[:space:]]*(//.*)?$' src | grep -iE '(password|passwd|credential|secret|owner_pin|recovery_key)[a-zA-Z0-9_]*[[:space:]]*:'; then
    echo "FAIL: a credential-shaped field was found"
    fail=1
else
    echo "OK"
fi

exit "$fail"
