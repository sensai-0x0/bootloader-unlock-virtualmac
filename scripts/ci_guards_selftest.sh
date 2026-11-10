#!/usr/bin/env bash
# Negative-test corpus for scripts/ci_guards.sh's own regexes — proves they actually catch
# the textual gaps vuln_res/AUDIT.md §3 found (a guard that's green against this repo's real
# tree today says nothing about whether it would catch a *future* mistake shaped like these).
# Not part of the normal CI gate (ci_guards.sh itself is); run this when either guard's
# pattern changes, to confirm the fix actually closes the gap it claims to.
#
# Each pattern string below is copied from ci_guards.sh, not re-derived — if they drift, this
# test is proving the wrong thing, so keep them in sync by hand (both files are small).

set -euo pipefail

fail=0

GUARD1_PATTERN='(std::process::Command|(^|[^A-Za-z0-9_])Command::new\()'
GUARD2_TYPE_PATTERN='(Option<)?(String|&str|Vec<u8>|\[u8\])>?'

check_matches() {
    local desc="$1" pattern="$2" line="$3"
    if echo "$line" | grep -qE "$pattern"; then
        echo "OK   (matched as expected): $desc"
    else
        echo "FAIL (did not match):       $desc -- $line"
        fail=1
    fi
}

check_does_not_match() {
    local desc="$1" pattern="$2" line="$3"
    if echo "$line" | grep -qE "$pattern"; then
        echo "FAIL (matched, should not): $desc -- $line"
        fail=1
    else
        echo "OK   (correctly excluded):  $desc"
    fi
}

echo "== Guard 1 corpus =="
check_matches "plain call"                    "$GUARD1_PATTERN" 'Command::new("ls")'
check_matches "whitespace-preceded"           "$GUARD1_PATTERN" '    Command::new("ls")'
check_matches "paren-preceded (the gap)"      "$GUARD1_PATTERN" '(Command::new("ls"))'
check_matches "bracket-preceded (the gap)"    "$GUARD1_PATTERN" '[Command::new("ls")]'
check_matches "fn-call-wrapped (the gap)"     "$GUARD1_PATTERN" 'foo(Command::new("ls"))'
check_matches "fully-qualified path"          "$GUARD1_PATTERN" 'let c = std::process::Command::new("ls");'
check_does_not_match "type merely named *Command" "$GUARD1_PATTERN" 'FooCommand::new("ls")'

echo
echo "== Guard 2 corpus (type half only; the credential-keyword grep is a separate, unchanged stage) =="
check_matches "bare String"                   "$GUARD2_TYPE_PATTERN" 'String'
check_matches "Option<String> (the gap)"      "$GUARD2_TYPE_PATTERN" 'Option<String>'
check_matches "Option<&str> (the gap)"        "$GUARD2_TYPE_PATTERN" 'Option<&str>'
check_matches "Option<Vec<u8>> (the gap)"     "$GUARD2_TYPE_PATTERN" 'Option<Vec<u8>>'

echo
# Full-pipeline check for Guard 2: a field this project would genuinely want flagged,
# proven against the actual two-stage pipeline (type-shape grep, then keyword grep), not
# just the type pattern in isolation.
echo "== Guard 2, full pipeline =="
sample_field='    owner_password: Option<String>,'
full_type_grep="(let[[:space:]]+(mut[[:space:]]+)?|pub[[:space:]]+)?[a-zA-Z_][a-zA-Z0-9_]*[[:space:]]*:[[:space:]]*${GUARD2_TYPE_PATTERN}[[:space:]]*,?[[:space:]]*(//.*)?\$"
if echo "$sample_field" | grep -E "$full_type_grep" | grep -qiE '(password|passwd|credential|secret|owner_pin|recovery_key)[a-zA-Z0-9_]*[[:space:]]*:'; then
    echo "OK   (matched as expected): Option<String>-wrapped credential field, full pipeline"
else
    echo "FAIL (did not match):       Option<String>-wrapped credential field, full pipeline -- $sample_field"
    fail=1
fi

echo
echo "== Guard 3 corpus (call-site and sudo-target extraction) =="
GUARD3_CALL_PATTERN='wrapper::run(_with_limits)?\(&\["[^"]+"'
GUARD3_SUDO_PATTERN='\["sudo"(, "-[^"]*")*, "[^"]+"'
check_matches "plain call site"               "$GUARD3_CALL_PATTERN" 'wrapper::run(&["bputil", "-d"])'
check_matches "bounded call site"             "$GUARD3_CALL_PATTERN" 'wrapper::run_with_limits(&["csrutil"], l)'
check_matches "sudo target after a flag"      "$GUARD3_SUDO_PATTERN" '["sudo", "-n", "bputil", "-d"]'
check_matches "sudo target, no flags"         "$GUARD3_SUDO_PATTERN" '["sudo", "kmutil"]'
check_does_not_match "unrelated string array" "$GUARD3_CALL_PATTERN" 'let v = ["bputil"];'

echo
if [ "$fail" -eq 0 ]; then
    echo "All guard regex self-tests passed."
else
    echo "One or more guard regex self-tests FAILED — a guard no longer catches a case it's meant to."
fi
exit "$fail"
