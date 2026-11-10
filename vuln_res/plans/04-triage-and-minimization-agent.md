# 04 — Triage and minimization agent

Consumes whatever `03`'s sandboxed campaign produces (a pile of crashing inputs under
`fuzz/artifacts/<target>/`) and turns it into a small, ranked list of distinct, minimized,
scored bugs. This is the stage that makes "quickly evaluating vulnerabilities" actually
quick — without it, a human has to read raw crash dumps one at a time.

## Step 1 — Deduplicate

Multiple crashing inputs often hit the same underlying bug. Dedup by:
1. Running each crash under `cargo fuzz run <target> <crash-file>` and capturing the
   panic message / sanitizer report.
2. Hashing a normalized stack trace (top 3-5 frames, stripped of addresses) as the dedup
   key. Two crashes with the same top frames are the same bug until proven otherwise.

Output: one representative input per unique stack-hash, not one per raw crash file.

## Step 2 — Minimize

`cargo fuzz tmin <target> <crash-file>` for each deduped representative — libFuzzer's own
test-case minimizer, already part of the toolchain once `cargo fuzz` is installed. No
custom minimizer needed; this is a solved problem in the existing tool.

Output: the smallest input that still reproduces each distinct bug. **This minimized input
is the PoC** in this suite's vocabulary (see `plans/README.md`'s "What 'PoC' means" —
worth re-reading here specifically, since this is the stage that produces it).

## Step 3 — Classify

For each minimized crash, run it once more and bucket by what actually happened:
- **Memory-safety** (ASan report: heap overflow, use-after-free, etc.) — always highest
  priority regardless of anything else.
- **Panic / unwrap-on-None / index-out-of-bounds** — a Rust-safe crash (no memory
  corruption possible), but still a DoS against whatever calls this code path.
- **Hang / timeout** — resource-exhaustion shape (the deep-nesting/huge-array concern from
  `AUDIT.md` §1.2 would land here).
- **Silent logic divergence** (not a crash at all — this needs differential tests, not
  fuzzing; see note below) — a parse that *succeeds* but produces a wrong `BootState` or
  wrong `SecurityMode`. Fuzzing with only a "did it crash" oracle can't find this class on
  its own; pair it with the lint-style check in `01-static-analysis-and-dependency-agent.md`
  §1.3, or add a differential oracle (e.g. "does `plan()` ever treat a fuzzed-but-`Ok`
  `BootState` as permitting an `IllegalTransition`?") as a follow-up fuzz target once this
  pipeline is proven on the crash-only targets first.

## Step 4 — Score (the rubric from `plans/README.md`)

```
priority = reachability_weight × memory_safety_weight × blast_radius_weight
```

Concretely, as the triage agent computes it:

| Signal | How it's measured | Weight scale |
|---|---|---|
| Reachability | Is the target function called from `main.rs`'s CLI dispatch today, or only from `#[cfg(test)]`/dead-code-annotated paths? | 1 (test-only) – 3 (reachable from a real CLI subcommand) |
| Memory-safety | ASan report present? Panic only? Logic-only? | 1 (logic) – 2 (panic/hang) – 3 (memory-safety) |
| Blast radius | Does the corrupted/wrong value feed `SecurityMode`/`Environment`/a future `is_mutation_allowed()` check, or just a display string? | 1 (cosmetic) – 3 (security-decision-feeding) |

A 3×3×3 (reachable, memory-safety, security-decision-feeding) bug would be the rare,
"drop everything" case. Today's two known candidates from `AUDIT.md` score as:
- `img4::parse_manifest_der`: reachability 1 (not wired into production yet) — so even a
  real ASan finding here is "fix before wiring it in," not "drop everything."
- `cmd_verify`'s deserialization: reachability 3 (live CLI path) × memory-safety 2 (hang,
  not memory corruption, if it's the recursion/size issue) × blast radius 1 (doesn't feed
  a security decision, just fails the command) = moderate, worth a quick fix, not urgent.

This is deliberately a simple multiplicative score, not a CVSS-style rubric with a dozen
sub-factors — the point is a same-day sort, not a defensible-to-a-committee number.

## Output format

One markdown file per distinct, minimized, scored finding, written to
`vuln_res/sweep-reports/<sweep-id>/<target>-<stack-hash-prefix>.md` (inside that sweep's
own directory — see `../sweep-reports/README.md` for the storage layout), containing: a
short, plain-language description anyone can read without the technical detail, the
minimized PoC input (as a committed fixture, small enough to review by eye), the repro
command, the classification, the score, and the reachability trace. This is the handoff
artifact into `05-disclosure-and-fix-agent.md`.

## Exit gate

Running this agent against `fuzz/artifacts/` from a completed `03` campaign produces a
short (ideally single-digit) list of distinct, scored, minimized findings — not a raw dump
of however many thousand crashing inputs the fuzzer wrote to disk.
