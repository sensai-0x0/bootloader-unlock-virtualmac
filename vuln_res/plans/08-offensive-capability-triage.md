# 08 — Offensive-capability improvement triage (H/M/L)

**Status:** researched proposal — web-verified 2026-11-11, grounded in the suite's own
agents/plans/stores. Nothing here is built; nothing here loosens `../CLAUDE.md`'s scope
line. "Offensive capability" throughout means **the suite's proven ability to find,
reproduce, and prove impact of bugs in code this project owns or can legitimately
analyze** — the same discipline Pwn2Own- and AIxCC-caliber teams use as *technique*
(see `07-ttp-informed-research-posture.md`), applied only to `bputil-eval`'s source and
dependency graph, executed only in registered disposable environments. Any item that
would require touching Apple's platform, a real device, or the host is not triaged here;
it goes to the refusal list.

## 1. Method

- **Repo sweep (2026-11-11):** all seven `.claude/agents/vulnres-*.md`, plans 00–07,
  `../AUDIT.md`, `../CLAUDE.md`, all four `projects/*` proposals, the sweep/knowledge
  stores, and the `src/` under analysis (1,853 lines at audit baseline; 2,182 with tests
  at time of writing).
- **Web verification (2026-11-11):** the search integration was unavailable (HTTP 402),
  so verification used direct fetches of authoritative primary sources:
  - `github.com/rust-fuzz/cargo-fuzz` — README confirmed: `init/add/run/tmin/cmin/coverage`;
    nightly toolchain + sanitizers; x86-64/Aarch64 Unix only.
  - `github.com/model-checking/kani` — README confirmed: bit-precise model checker for
    Rust (safety UB, panics, overflow, `kani::any()` proof harnesses, function
    contracts), GitHub Action, ASE 2026 paper — mature and maintained.
  - `github.com/eurecom-s3/symcc` (master README) — confirmed: compiler-based concolic
    execution; **best-effort maintenance only; Rust unsupported (tracked in issue #1)**.
  - `github.com/ossf/fuzz-introspector` — README confirmed: fuzzer performance/blocker
    analysis (coverage, hit frequency, entry points), OSS-Fuzz integration.
  - `github.com/LaurieWired/GhidraMCP` — README confirmed: MCP server for Ghidra incl.
    **headless mode via PyGhidra** (import/analyze a binary with no Ghidra GUI).
  - Semgrep MCP (official `semgrep/mcp` README) — confirmed: the server is now
    **shipped inside the official `semgrep` binary** (`uvx semgrep-mcp`); tools:
    `semgrep_scan`, `semgrep_scan_with_custom_rule`, `get_abstract_syntax_tree`;
    5,000+ registry rules.
  - `codeql.github.com/docs` supported-languages page — confirmed: **CodeQL now supports
    Rust (editions 2021 and 2024)** with a dedicated query/library pack including
    dataflow; requires `rustup`/`cargo`; nightly-only features unsupported.
  - `github.com/rustsec/rustsec` `cargo-audit` README — confirmed plus a new companion:
    **`reachsec`** (`github.com/xizheyin/reachsec`) for function-level reachability
    context on advisories.

## 2. Baseline: where the offensive capability actually stands

Honest inventory so the triage below is relative:

| Capability | State |
|---|---|
| Static recon + semantic lint (contains()-pattern) | **Proven twice** — two real findings found & fixed via the lint methodology (`sweep-reports/2026-11-*`) |
| Dependency/SBOM scanning | **Blocked** — `cargo audit`/`cargo deny` absent from host; knowledge entry records the gap |
| Fuzzing | **Designed, never executed** — targets specced (`plan 02`), no `fuzz/` workspace exists, no corpus committed |
| Sandboxed execution | **Framework built, registry empty** — `knowledge/environments/` has schema but zero registered profiles |
| Triage / scoring | **Proven on static findings, never on fuzzer output** — 9/9 rubric used twice |
| Exploit-dev / chaining | **Never exercised** — agent exists, strict rules written, zero PoCs produced |
| Environment-hygiene auditing (ATT&CK-lens) | Specced in plan `03`/`07` §5, never run |
| Web-pattern research loop | Skill exists (`vulnres-pattern-analysis`), used at least once |

**Conclusion the triage acts on:** the suite's offensive ceiling is currently bounded by
*execution debt* (the designed-but-never-run pipeline), not by missing ideas. The highest
priority items are those that close that debt with the cheapest, most standard tooling;
tool novelty comes after.

## 3. Integration mechanisms (how agents actually use these tools)

Four lanes, each with a distinct approval model. Every item in §4 names its lane.

- **Lane A — host CLI, ask-first.** The current model (`vulnres-recon`'s stance):
  install `cargo-audit` etc. on the host with explicit user approval per tool.
  Cheap for pure-Rust cargo subcommands; remains the fallback, not the default.
- **Lane B — disposable-environment canonical image (recommended primary lane).**
  One prebuilt, versioned, **network-isolated, resource-capped container image**
  containing the whole research toolchain (cargo-fuzz + nightlies + sanitizers, Kani,
  cargo-audit/deny/semgrep-cli/CodeQL CLI, lldb) — registered as one or more
  `knowledge/environments/` profiles per `SCHEMA.md`. Approvals collapse to two events
  the user gates once: "approve creating this image" and "approve each run" (per the
  standing per-action approval rule). Kills the recurring install-ask friction that is
  currently blocking recon and fuzz-harness entirely. Image digest gets pinned in the
  profile (see M5) so a PoC is reproducible against a named toolchain.
- **Lane C — MCP servers for interactive agent tooling.** For tools whose workflow is
  iterative/conversational (semgrep MCP; Ghidra headless MCP if ever needed):
  registered per-environment in the MCP config, stdio transport, never exposed to the
  network. The agent's existing output contracts (`sweep-reports`, `knowledge/`) stay
  authoritative — MCP only changes how the tool is reached, not where findings go.
- **Lane D — CI / scheduled hooks.** Deterministic checks don't need an agent at all:
  CodeQL analysis, `cargo deny check advisories --sort advisory-id` schedule,
  `clippy`/`fmt`/`ci_guards.sh` (already wired). Results land as SARIF/artifacts the
  recon agent consumes rather than re-derives.

Guardrail note for every lane: target restriction (owned code only), disposable-execution
rule, and corpus-provenance boundary (`research/` firmware = structural reference only)
apply to **all four lanes identically**; no lane weakens another. Amplify the existing
`ci_guards.sh` self-test (`scripts/ci_guards_selftest.sh`) pattern: every new lane or
tool gets a negative-test proving it *would* catch a concrete violation shape.

## 4. The triage

### Priority legend

- **H** — does one of: unblocks the designed-but-never-executed core pipeline, converts
  a proven-manual detection technique into an automatic one, or establishes exhaustive
  (rather than sampling) evidence about the code. High capability-per-effort.
- **M** — meaningful capability gain, moderate effort, or value contingent on an H item
  landing first.
- **L** — real but currently gated: blocked by upstream support, hardware access, or
  diminishing returns at this target's size. Explicit revisit trigger named.

### HIGH

| # | Item | Lane | Effort |
|---|---|---|---|
| H1 | Execute the fuzzing pipeline end-to-end (Project 01 steps 1–4) | B | 1–2 sessions |
| H2 | Canonical disposable-environment research image + two environment profiles | B | 1 session |
| H3 | `cargo audit` + `cargo deny` + `reachsec` on `Cargo.lock`, activated for recon | B then D | hours |
| H4 | CodeQL Rust queries encoding the security-relevant-parsing taint patterns | D then A | 1–2 sessions |
| H5 | Kani proof harnesses for the state machine and validity predicates | B | 1–2 sessions |

**H1 — Run the first real campaign, then triage what comes back.**
`vulnres-fuzz-harness` scaffolds `fuzz/` (both specced targets, seed corpora per plan
02), `vulnres-environment-runner` executes a bounded campaign (minutes→hours) inside the
H2 image, `vulnres-triage` scores whatever returns — including
`cargo fuzz tmin` minimization and the documented "nothing crashed" outcome — and
`vulnres-disclosure` closes one finding-to-PR cycle (or records a clean run). This
single item converts five designed stages into one proven loop and is the suite's stated
exit gap (`plan 06`, Project 01's success metric). Integration: `cargo fuzz run/tmin/cmin`
exactly as verified above; nightly toolchain lives **in the image**, not the host.
Exit criterion: one 10-minute-per-target campaign completes end-to-end, either clean
(artifacts + knowledge entry) or producing a fuzzer-confirmed scored finding.

**H2 — Build the canonical research image.**
One Dockerfile (or Tart/container per whichever provider the user picks) with pinned
toolchain versions, no network at run time, CPU/memory caps per `SCHEMA.md` — landed as
1–2 environment profiles (`fuzzing`, `static-analysis`; `exploit-dev` added later with
its own approval, per the runner's existing rule). The image is the *only* new
host-level footprint in this entire triage, and it's one item instead of one per tool.
Exit criterion: `vulnres-environment-runner` can instantiate it from a profile and
smoke-run both fuzz targets inside it.

**H3 — Dependency-intelligence, finally.**
`cargo audit` (RustSec) + `cargo deny` (advisories, licenses, `image4`/`der` being
niche low-download crates per `AUDIT.md` §4) — plus the newly surfaced **`reachsec`**
companion for function-level reachability of any advisory hit, which feeds the triage
rubric's reachability factor with data instead of judgment. Run first in-lane-B
(session-approved), then move to a Lane-D schedule so recon stops being fully blocked.
Exit criterion: `knowledge/` entry records first advisory-DB snapshot date; two
consecutive runs diffable.

**H4 — CodeQL for Rust as the home of the contains()-lint.**
CodeQL's Rust extraction (editions 2021+2024 confirmed, incl. `clap` and `serde`
modeling — both direct dependencies here) makes the suite's most valuable manual
technique mechanizable: a dataflow query tracing *parsed CLI-tool stdout → security
enum construction (`Environment`/`SecurityMode`) → gate decision* flags
`env.rs:72` and `collect.rs:203-208`-shaped patterns semantically instead of regex, and
catches future variants (aligned line-anchored matches, state machines) automatically.
Queries are committed in-repo (`vuln_res/codeql/`), run in Lane D (CI) and exported as
SARIF; `vulnres-recon` consumes the SARIF and credits/dedupes against prior sweeps same
as any other finding source. This also directly addresses `AUDIT.md` §3's regex gaps in
`ci_guards.sh` at the semantic layer.
Exit criterion: one in-repo query reproduces both known §2 findings at HEAD and
correctly fires on a deliberately-planted third instance.

**H5 — Kani proofs on the tool's security-relevant logic.**
Fuzzing samples inputs; Kani **exhaustively** verifies bounded properties. Highest-value
targets, all already pure functions with spec-level predicates in-repo:
`plan::is_permitted` (prove `IllegalTransition` unreachable for all inputs of the
mode/profile space — direct reinforcement of the `SingleContainerTouched`/transition
invariants); `state::validate` (prove each `BootStateError` firing condition is
complete, i.e. no inconsistent state passes validation); the wrapper's
hash-recording path. Kani runs in Lane B (Linux/mac), cheap on this codebase's tiny
functions. Counterexamples slot directly into the triage classifier's
"logic-divergence" category with an actual witness input.
Exit criterion: `plan()`'s strictness is proven or a real counterexample exists —
either result is a finding worth recording.

### MEDIUM

| # | Item | Lane | Effort |
|---|---|---|---|
| M1 | Semgrep (+official MCP) with custom rules as the lint's second home | C then B | 1 session |
| M2 | Harness telemetrics + corpus-diversity loop | B | 1 session |
| M3 | PoC engineering stack (deterministic re-run script + lldb automation) | B | 1 session |
| M4 | Structured minimization for JSON inputs beyond `tmin` | B | 1 session |
| M5 | Pin reproducibility: digests in env profiles + hash-chained artifacts | B | hours |
| M6 | Automate chain-composition pre-screening (CodeQL callgraph × findings index) | D then A | 1 session |

**M1 — Semgrep as the portable lint home.** Its MCP server (now shipped in the official
binary) gives agents `semgrep_scan_with_custom_rule`/AST access interactively; the rules
can express exactly the `contains()`/credential-shape checks `AUDIT.md` §2–§3 describes,
including type-alias/`Option<String>` shapes the textual guard misses. Value is partly
redundant with H4 (CodeQL) — keep both: Semgrep is lighter and rule-portable (feeds
Product 2's triage-as-a-service pitch verbatim), CodeQL is deeper dataflow. Gate: land
after H4 so the two rule-sets are written against a single namespace of findings.

**M2 — Make the campaign self-improving.** `cargo fuzz coverage` + a fuzz-introspector
pass per target (verified above) recorded into `knowledge/`: reachable-block coverage,
unreached entry points, "blocking" constructs — then act on it (new seeds: DER
fuzzing dictionaries for length fields/tags, structurally-valid manifest roundtrips
generated via the `image4` crate itself, mutated `BootState` fixtures). This is what
turns "ran 10 minutes, nothing crashed" into "ran 10 minutes, the fuzzer never reached
parse loop N" — the difference between a clean result and a coverage-limited result.

**M3 — Engineer PoCs as software (per plan 07 §4).** A tiny committed
`fuzz/repro.py`/`repro.sh` + deterministic runner: given a minimized crash artifact,
rebuilds the instrumented binary in the profiled environment, re-runs under ASan, and
captures the reproducible report into `sweep-reports/` — plus scripted `lldb` sessions
(run-to-crash, frame capture) so exploit-dev has a real debugger the way Naptime's
agents do. Effort small; value scales with every future finding.

**M4 — JSON-aware minimization.** `tmin` byte-shrinks; but for the
`boot_state_deserialize` target a structure-preserving minimizer (shrink
arrays/deep-nesting while keeping parseable JSON) produces much more legible PoCs for a
serde bug (proves *which field shape* triggers). Small pure-Python/Rust tool; direct
quality benefit to the second fuzz target's output.

**M5 — Reproducibility as a first-class property.** Pin the H2 image digest and
toolchain versions in every environment profile; hash-chain crash artifacts/PoCs on
commit (the repo's own `report.rs` pattern). Cheap now, decisive later for any
"prove this PoC is the same bug we found" moment, up to and including coordinated
disclosure.

**M6 — Automate the chaining check.** Triage step 5 ("check for composition with other
open findings") is currently prose-and-judgment. M6 makes it a joiner: CodeQL call
graph + `findings-index.md` reachability data → automated candidate chain list handed
to `vulnres-exploit-dev` per its existing triage-confirmed-only contract. First time two
findings genuinely chain, the tooling already exists; until then it costs almost
nothing to run.

### LOW (parked, with explicit revisit triggers)

| # | Item | Park reason | Revisit trigger |
|---|---|---|---|
| L1 | Symbolic execution (SymCC/SymQEMU) | Upstream best-effort only; **Rust unsupported** (confirmed, issue #1) | Rust support lands upstream or a C dependency enters the graph |
| L2 | LibAFL / AFL++ persistent-mode migration | libFuzzer throughput is nowhere near the bottleneck for a target this small | A campaign demonstrably limited by exec-rate |
| L3 | Binary RE for dependency crates (GhidraMCP headless) | Dependency graph is **pure Rust, no unsafe C bindings today** (`AUDIT.md` §5: no `unsafe` on the IMG4 path); nothing to RE yet | First C/FFI dependency enters `Cargo.lock` (then it becomes M/G) |
| L4 | LLM-hypothesis-directed fuzzing (PBFuzz-style) | Requires a stable campaign loop and crash pool that don't exist yet | H1/M2 proven; at least N campaigns run |
| L5 | Fuzzing the 1TR-detection formatting against real 1TR | Needs physical hardware + a human in 1TR — permanently human-gated | P3 hardware round-trip work happens (root repo's gate) |
| L6 | Environment-hygiene ATT&CK audit of new environment types (plan 03/07 §5) | Only relevant when new environment profiles get created | Every new environment-type onboarding (run it then; it's cheap) |

## 5. Explicitly out of scope (unchanged, restated once)

Real firmware/`iBoot*.im4p`/`kernelcache` under `research/` — structural reference only;
never a fuzz corpus membership for Apple-targeting, never a RE/exploit target, with
GhidraMCP or any other tool. Signature-verification bypass, SEP/Boot ROM fault-injection,
Activation Lock/MDM/FileVault circumvention, remote/at-scale operation: all remain on the
refusal list. Any *technique* imported here (from Pwn2Own writeups, AIxCC systems, or a
MCP-wrapped tool's registry) undergoes the same technique-vs-target scope check
`vulnres-pattern-analysis` already applies — generic class knowledge in,
Apple-platform-specific application out.

## 6. Suggested execution order

1. **H2** (image) → **H1** (first campaign) — this closes the suite's central execution
   debt and exercises every stage agent against real output.
2. **H3** in parallel (unblocks recon; independent of campaign).
3. **H4** + **H5** in either order after H2 exists (both want the image).
4. M-items land as they become load-bearing (M1 after H4; M2 immediately after H1;
   M3/M5 with the first real finding; M4/M6 opportunistically).
5. L-items: revisit only on their named triggers — include this table in the pattern-
   analysis skill's next sweep so nothing here silently rots.

## 7. Decision requests for the owner

1. **Lane B image approval:** one prebuilt network-isolated research image (vs. per-tool
   host installs under Lane A) — this single yes unblocks H1, H2, H3, H5.
2. **First campaign approval:** a one-off bounded run per H1's exit criterion
   (still per-action approved by the standing rule; this is the pre-notification the
   orchestrator already owes you).
3. **CI schedule approval:** Land-D hooks (CodeQL + `cargo deny` cadence) in the
   monorepo's existing CI convention.
4. Optional: whether to fold any of this into `projects/01-continuous-fuzz-bug-hunter`'
   build order (it already matches steps 1–4; this triage mainly adds the H3–H6 layer
   around it).
