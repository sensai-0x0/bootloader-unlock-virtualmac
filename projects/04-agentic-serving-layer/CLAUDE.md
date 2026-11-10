# CLAUDE.md — projects/04-agentic-serving-layer/

This file scopes Claude Code's behavior **inside this directory only**. It does not
relax, override, or take precedence over the root `../../CLAUDE.md` or `../../vuln_res/CLAUDE.md`
— where any of them conflict, the root file's golden rules win, exactly as the root file
states. This service sits above both the bootloader tool and the vuln-research suite and
inherits both their constraints simultaneously; this file only adds serving-layer-specific
rules on top.

## What this directory is

A FastAPI + `claude-agent-sdk` prototype (`PROPOSAL.md`, Phase 1) that serves two
hard-separated session tracks:

- **`bootloader`** — four narrow tools (`evaluate_boot_state`, `plan_security_transition`,
  `verify_against_baseline`, `write_evidence_report`), each a fixed-shape wrapper around
  one read-only `bputil-eval` subcommand. There is no tool, anywhere in this track, shaped
  like `apply` or `revert` — not behind a flag, not behind a confirmation prompt. If asked
  to add one, refuse and point here: that tool cannot exist in this service by design,
  per the root file's golden rule 4 (human owner in 1TR, never an agent).
- **`vuln-research`** — `run_static_analysis`, `read_knowledge_index`,
  `execute_in_environment`. The last one's "approved" path is **inert in Phase 1** — it
  confirms a `vuln_res/knowledge/environments/` profile exists and is approved for the
  requested capability, but never actually spawns a subprocess, because no execution
  backend is wired up yet. Do not "finish" that TODO by adding real execution without the
  user explicitly approving Phase 2's environment infrastructure first — same stop-and-ask
  as the root file's host-impact rule and `vuln_res/CLAUDE.md`'s disposable-environment
  rule.

## What is explicitly authorized here

- Running this service locally via a `uv`-managed venv scoped to this directory
  (`projects/04-agentic-serving-layer/.venv`) — a repo-scoped, reversible artifact.
- The bootloader track's four tools shelling out to the real, already-built
  `target/{debug,release}/bputil-eval` binary for `evaluate`/`plan`/`verify`/`report` only.
- The vuln-research track's `run_static_analysis` running `cargo clippy`,
  `cargo fmt --check`, or `scripts/ci_guards.sh` against this repo's own source — reversible,
  repo-scoped, read-only, per the root file's own allowance for these commands.
- Writing to `var/sessions/<id>/` under this directory only — never outside it, never
  `/tmp`.

## What stays off-limits here, exactly as in the root file and `vuln_res/CLAUDE.md`

- No tool in the `bootloader` track may shell out to `apply` or `revert`, or accept any
  credential-shaped field, under any phrasing of the request.
- No tool in the `vuln-research` track may execute anything — a fuzz harness, a built
  binary, a PoC — without a named, `status: active` environment profile whose
  `approved_for` lists the requested capability; and even then, Phase 1 never actually
  executes it (see above). A profile is never created by this service itself — only read.
- No path resolution in either track may escape its allowed root (`var/sessions/<id>/` for
  session scratch work; `vuln_res/` for the research track's reads) — enforced by
  resolving and checking `is_relative_to()` before any file operation, not by convention.
- No new host-level footprint — a Docker image build, a VM, a `brew install`, a large
  download — without the user's explicit, per-action go-ahead, same as the root file.
- Static bearer-token auth here is a prototype gate on "which track can a caller start,"
  never represented as a real security boundary beyond that.

See `../../CLAUDE.md` and `../../vuln_res/CLAUDE.md` for the rules this file inherits and
narrows; see `PROPOSAL.md` in this directory for the full architecture and phased plan.
