# Project 4 — Agentic Serving Layer

**One-line pitch:** serve this repo's two already-built, read-only-by-construction agent
capabilities — boot-posture evaluation (`bputil-eval`) and owned-code vulnerability
research (`vuln_res/`) — over a persistent HTTP/WebSocket session API, as two
hard-separated tracks, so a human can drive a multi-turn Claude Agent SDK conversation
against either without a terminal, with no new mutation surface and no new host footprint.

## APT-mindset framing

An APT benefits from a serving layer that blurs trust boundaries — one session type that
can both measure boot posture *and* execute fuzzed code, or one over-broad credential that
reaches everything. The defensive inversion: two hard-separated session tracks, each with
its own system prompt, its own tool set, and its own workspace root, so a compromised or
confused session in one track structurally cannot reach the other's capabilities. This is
the direct code expression of the project owner's own requirement: *the vulnerability
researcher stays separate from the bootloader tool.*

## What's reused from this repo today

- `target/{debug,release}/bputil-eval` — the compiled CLI, invoked as an audited
  subprocess; never reimplemented in Python. `evaluate`/`plan`/`verify`/`report` are
  read-only per `spec/build-spec.md`'s golden rules; `apply`/`revert` are P3 stubs that
  this layer never exposes as a tool at all (see Architecture).
- `src/wrapper.rs` — "the only place `std::process::Command` is called," recording
  argv/exit-code/output-hash for every invocation. The Python service's
  `run_bputil_eval()` / static-analysis helpers mirror that single-call-site discipline.
- `vuln_res/CLAUDE.md`, `vuln_res/knowledge/environments/SCHEMA.md` — the
  disposable-environment rules (`approved_for` scoping, "no profile means no approved
  environment") this layer ports into code for the vuln-research track's execution gate.
- `projects/supervisor-agent/tools/supervisor.py` — `score`/`render` subcommands back
  the optional `GET /portfolio/brief` read.
- `reports/evaluator/evaluator-decisions-2026-11-11.md` — the actual build-next/interop
  roadmap (posture-confidence, baseline/drift-watch, downgrade/rollback observables;
  internal-format-first CTI emission) this layer exists to make conversational, not a new
  feature set invented for this proposal.

## Architecture (prose)

A FastAPI service exposes `POST /sessions` (track: `bootloader` | `vuln-research`), a
WebSocket event stream, `POST /sessions/{id}/messages`, `POST /sessions/{id}/interrupt`,
and a read-only `GET /portfolio/brief`. Each session gets its own `ClaudeSDKClient`
instance with **only** that track's custom MCP tool(s) registered — every built-in tool
(`Bash`, `Read`, `Write`, `Agent`, …) is removed from the model's context via
`disallowed_tools`, so the model literally cannot see a generic shell.

The bootloader track exposes four narrow, separately-schema'd tools —
`evaluate_boot_state`, `plan_security_transition`, `verify_against_baseline`,
`write_evidence_report` — each a thin, fixed-shape wrapper around one `bputil-eval`
subcommand. There is no tool, schema field, or code path shaped like `apply` or `revert`
anywhere in this track; the exclusion is structural, not a runtime check on a free-form
argument.

The vuln-research track exposes `run_static_analysis` (clippy/fmt-check/the
`security-relevant-contains()` lint — always allowed, read-only, never touches untrusted
input), `read_knowledge_index` (read-only, path-contained to `vuln_res/`), and
`execute_in_environment`, which checks a named profile against
`vuln_res/knowledge/environments/<id>.md` (`status: active`, requested capability present
in `approved_for`) before proceeding. In Phase 1 this check is real but its "pass" branch
is inert — no execution backend is wired up yet (the registry is empty today), so a
passing check never actually spawns a subprocess; it only confirms the gate works. Real
execution against a real disposable environment is Phase 2 work, once there's
infrastructure to execute against.

## Guardrail mapping

| Guardrail | How this project respects it |
|---|---|
| Read-only by default / golden rule 3 | Bootloader track's four tools map 1:1 to `evaluate/plan/verify/report`; no tool exists for `apply`/`revert`. |
| Human owner in 1TR for any mutation / golden rule 4 | Unreachable by construction — there is no mutating tool in this service at all. |
| `NoCredentialHandling` | No tool schema anywhere accepts a credential-shaped field. |
| Never impact the host machine (root `CLAUDE.md`) | Service environment is a `uv`-managed venv scoped to this directory; `var/sessions/` stays under the repo; no Docker/VM creation happens under this proposal — that's Phase 2, gated on a fresh go-ahead. |
| vuln_res disposable-environment rule | `execute_in_environment`'s profile check is a direct code port of `SCHEMA.md` rules 1–2; its "pass" path is inert in Phase 1 since no provider is wired up, so no execution ever reaches the host under this proposal. |
| vuln_res scope boundary (never Apple's platform) | `read_knowledge_index` and `execute_in_environment` both path-contain to `vuln_res/`; neither can resolve a path outside it. |
| Honesty of state / golden rule 8 | `evaluate_boot_state` always calls the real binary fresh; no tool caches or fabricates a `BootState`. |

## Phased build order

1. **Phase 1 (this proposal, in depth):** local FastAPI + `ClaudeSDKClient` prototype —
   sessions, WebSocket stream, messages/interrupt, in-memory registry, repo-scoped
   workspace, static bearer-token auth, the two tracks' tool wrappers, `/portfolio/brief`.
2. **Phase 2 (needs a fresh, explicit go-ahead before any Docker/VM work):** containerize
   the service; Redis-backed session registry; the vuln-research track's first real
   registered environment profiles (this is where `execute_in_environment`'s "pass" path
   stops being inert).
3. **Phase 3:** multi-tenant isolation, durable storage, queues, real secrets management,
   audit logging — several pieces already have a running start: `report.rs`'s
   hash-chained evidence bundle for session-transcript auditability; the 1TR gate as the
   permission-workflow pattern for any future mutation path; `SCHEMA.md`'s `approved_for`
   model as the scoped-permission sketch.

## Open risks / what needs sign-off before any code runs

- This directory's own `.venv` and `var/sessions/` are new, repo-scoped artifacts —
  reversible and gitignored, but still new disk usage the user should know is accumulating
  (no retention policy in Phase 1; see `CLAUDE.md` in this directory).
- `claude-agent-sdk` wraps the Claude Code CLI itself as a subprocess — the service's
  runtime dependency is on that CLI being installed and reachable, not just a Python
  package.
- The vuln-research track's narrower tool set (static analysis + profile-gated execution)
  is deliberately less capable than the full `.claude/agents/vulnres-*` suite — that's a
  considered Phase 1 choice (no per-call human approval gate exists yet for an API
  session), not a gap to silently backfill without a decision point.
- Static bearer-token auth is explicitly a prototype, not a security boundary beyond
  "which track can this caller start" — do not expose this service beyond localhost as-is.

## Success metric

A human opens a bootloader-track session, asks it to evaluate current posture, watches
`tool_use`/`tool_result` events stream over the WebSocket, asks it to "apply the plan now,"
and watches it refuse — with the test asserting no `apply`-shaped tool call was ever
possible, not just that the model declined in prose. Separately, a vuln-research-track
session runs `cargo clippy` successfully, then refuses to start a fuzz campaign because no
environment profile is registered — all against a repo-scoped `uv` venv, with zero new
host footprint beyond this directory.
