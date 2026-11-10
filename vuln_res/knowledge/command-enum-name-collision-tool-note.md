---
name: command-enum-name-collision-tool-note
type: tool-note
description: main.rs's clap Subcommand enum is named Command, textually colliding with std::process::Command in grep output
updated: 2026-11-10
---

`src/main.rs:40` defines `enum Command { Evaluate, Plan, Report, Verify, Apply, Revert }`
— clap's `Subcommand` enum, deliberately named `Command` for ergonomic
`Command::Evaluate { .. }` matching in `main()`. This is unrelated to
`std::process::Command`, but a plain `grep -n 'Command::'` across `src/` returns both
the real subprocess spawn (`src/wrapper.rs:45`) and every CLI dispatch arm
(`src/main.rs:95-102`) in the same result set, which takes a moment of reading to
untangle.

`scripts/ci_guards.sh`'s Guard 1 regex (`[[:space:]]Command::new\(`) is unaffected — it
specifically requires the `::new(` constructor call, which the enum variants never use —
so this is **not** a guard false-positive today. It's purely a static-analysis-review
cost: anyone (human or agent) doing the same independent "every `Command::` usage" sweep
`vuln_res/AUDIT.md` §3 and this session's own verification ran will hit the same
need-to-disambiguate moment. Worth knowing going in, not worth renaming the enum over —
that's a larger, unrelated refactor with its own review cost or reviewed and rejected.
