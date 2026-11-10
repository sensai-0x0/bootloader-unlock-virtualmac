# projects/ — extending bputil-eval toward a live bug hunter and other security-critical roles

**The brief:** take what this repo has already proven — a read-only boot-security
evaluator (P0–P2, done), one fully evidenced end-to-end mutation round-trip against a
disposable VM (M8/M9/M10, `Full → Reduced → Full → Permissive`), and a designed-but-never-run
vulnerability-research agent suite (`vuln_res/`) — and extend it into something that runs
*continuously* and covers *more security-critical roles*, not just a one-shot CLI.

**Method:** every proposal below was drafted using an APT-mindset lens — ask what a
patient, well-resourced adversary would want (continuous visibility, fleet-scale
coverage, automated exploit chaining, defenders who are slow to notice drift) — then
**invert** that into a defensive capability this project could legitimately build. No
proposal here contains, or is informed by, actual offensive technique detail against
Apple's platform; the lens is a prioritization tool, not an attack brief.

**The hard boundary, restated because it matters more here than anywhere else in this
repo:** nothing in `projects/` authorizes offensive action against Apple's platform
security (Boot ROM/SEP/iBoot/signature verification), any device this user doesn't own,
or any host-level footprint beyond this repo. Every single proposal is scoped to this
project's own code, this user's own owned/enrolled hardware, and explicit, per-action
sign-off for anything that executes code, touches a live target, or runs on a schedule.
**Every file here is a proposal for the user to approve — nothing in this folder is wired
into `.claude/agents/` or scheduled to run.** That's a deliberate, separate decision.

## The seven proposals

| # | Name | Kind | One-line pitch | Effort | Impact | Risk | Builds on |
|---|---|---|---|---|---|---|---|
| 1 | [Continuous Fuzz Bug Hunter](./01-continuous-fuzz-bug-hunter/PROPOSAL.md) | Project | Turn the already-designed, never-run `vuln_res/` fuzzing pipeline into a real scheduled cadence against this repo's own parsers. | M | M | M | `vulnres-fuzz-harness`, `-environment-runner`, `-triage`, `-disclosure` (built, unrun) |
| 2 | [Gated Mutation Engine](./02-gated-mutation-engine/PROPOSAL.md) | Project | Build the still-stubbed `authorize`/`execute`/`verify.assert_invariants` (P3) now that the VM round-trip proved the mechanism, keeping the human in the loop for exactly the one step the golden rules reserve for them. | L | L | L | `spec/contract-spec.md`, M8–M10 evidence, `plan.rs` |
| 3 | [Fleet Boot-State Drift Watch](./03-fleet-drift-watch/PROPOSAL.md) | Project | Schedule the already-proven read-only `evaluate`/`verify` across N owned, enrolled Macs to catch boot-security drift fleet-wide. | M | M | M | `evaluate`/`verify`/`state/diff.rs` (P1/P2, done) |
| 4 | [Agentic Serving Layer](./04-agentic-serving-layer/PROPOSAL.md) | Project | Serve the bootloader tool and the vulnerability researcher over a persistent HTTP/WebSocket session API, as two hard-separated tracks, with no new mutation surface. | M | M | S | `src/wrapper.rs`, `vuln_res/knowledge/environments/SCHEMA.md`, `supervisor-agent` (Phase 1 implemented) |
| 5 | [Boot-Security Attestation Bundle](./products/01-attestation-bundle/PROPOSAL.md) | Product | Package the existing hash-chained evidence bundle into a signed, independently-verifiable compliance artifact for MDM-managed fleets. | S–M | M | S | `report.rs`, `evidence/vm-sec-research-25D125/` |
| 6 | [Vulnerability-Triage-as-a-Service](./products/02-triage-as-a-service/PROPOSAL.md) | Product | Offer the proven recon+triage scoring pipeline (already found and fixed a real bug in this repo) to other owners of Rust/parser-heavy codebases. | M | M | M | `vulnres-recon`, `vulnres-triage` scoring rubric |
| 7 | [Boot-Security Copilot](./products/03-boot-security-copilot/PROPOSAL.md) | Product | Package the existing CLI + the already-written hobbyist guide into a guided, plain-English onboarding product. | S | S–M | S | CLI (P0–P2), `reports/m2-bootloader-unlock-technicians-guide.md` |

Effort/Impact/Risk are S(mall)/M(edium)/L(arge), relative to each other, not absolute
estimates.

## The supervisor agent

[`supervisor-agent/PROPOSAL.md`](./supervisor-agent/PROPOSAL.md) is the orchestration
layer that ties the three projects and the existing `vuln_res/` suite together — deciding
what's stale, what's next, and enforcing the same escalation ladder (autonomous for
read-only/static work, explicit sign-off for anything that executes, touches a live
target, mutates boot state, or smells like platform-security drift) across all of it. It
explicitly reconciles with — and sits one layer above — the existing
`vulnres-orchestrator`, which coordinates one `vuln_res/` sweep; the supervisor decides
*which project* needs attention next, `vulnres-orchestrator` still runs the sweep itself.
Read it before any of the three projects above, since each project's "what runs when"
section assumes the supervisor's scheduling model.

**Known constraint that affects all of this:** this harness currently only discovers
`subagent_type` values from the global `~/.claude/agents/`, not this repo's project-scoped
`.claude/agents/` (confirmed, root-caused, with a working fallback — see
`vuln_res/plans/06-orchestration-and-scheduling.md`'s "How to actually invoke this suite
today"). The supervisor-agent proposal inherits the same fallback until that's fixed
upstream; it does not assume native `subagent_type: "vulnres-supervisor"` works today.

## How to read a proposal

Every `PROPOSAL.md` (project or product) follows the same shape: one-line pitch; the
APT-mindset framing (what an adversary would want, inverted into what this builds); what's
reused from this repo today, cited by file; a prose architecture/data-flow sketch; an
explicit guardrail mapping to the golden rules and `spec/contract-spec.md` invariants it
must respect; a phased build order; open risks and exactly what needs the user's
sign-off before any code runs; and one concrete success metric. None of these are
estimates of calendar time — they're sequencing and scope, for the user to accept, defer,
or reject per-proposal.
