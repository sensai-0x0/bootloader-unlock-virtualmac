"""Vuln-research track: run_static_analysis, read_knowledge_index, execute_in_environment.

Scoped strictly to this repo's own code (never Apple's platform), per
../../vuln_res/CLAUDE.md. `execute_in_environment`'s "approved" path is deliberately
inert in Phase 1 — see ../../PROPOSAL.md and ../../CLAUDE.md: no execution backend is
wired up yet, so a passing profile check never actually spawns a subprocess.

Tool logic lives in plain `_impl` async functions, each testable directly without the
Claude Agent SDK in the loop; `build_options` wraps them with `@tool` for real sessions.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Any

from claude_agent_sdk import ClaudeAgentOptions, create_sdk_mcp_server, tool

from app.config import ENVIRONMENTS_DIR, REPO_ROOT, VULN_RES_ROOT
from app.sessions.models import Session, utcnow_iso

BUILTIN_TOOLS_TO_REMOVE = [
    "Bash", "Read", "Write", "Edit", "Glob", "Grep", "WebFetch", "WebSearch",
    "Agent", "NotebookEdit", "TodoWrite", "TaskCreate", "TaskGet", "TaskUpdate",
    "TaskList", "AskUserQuestion", "ExitPlanMode", "ListMcpResourcesTool",
    "ReadMcpResourceTool", "Monitor", "TaskStop",
]

STATIC_ANALYSIS_CHECKS: dict[str, list[str]] = {
    "clippy": ["cargo", "clippy", "--all-targets", "--", "-D", "warnings"],
    "fmt-check": ["cargo", "fmt", "--check"],
    "security-lint": ["./scripts/ci_guards.sh"],
}

SYSTEM_PROMPT = """You are the vulnerability-research agent for this repo's own Rust \
code and dependency graph (bputil-eval) — never Apple's platform (Boot ROM, SEP, iBoot, \
or any signature-verification path), not on real hardware, not in a VM, not on extracted \
firmware. You have exactly three tools:

- run_static_analysis: cargo clippy, cargo fmt --check, or this repo's CI security-lint \
guard. Always allowed — read-only, never touches untrusted/fuzzed input.
- read_knowledge_index: read a file under vuln_res/knowledge/ or vuln_res/sweep-reports/. \
Always allowed, read-only, and cannot resolve a path outside those two trees.
- execute_in_environment: requires a named, already-registered environment profile \
under vuln_res/knowledge/environments/ whose status is "active" and whose approved_for \
list includes the capability you're requesting. If no matching profile exists, refuse \
and say so — never improvise with this host. Note: in this Phase 1 service, even a \
passing check never actually executes anything yet (no execution backend is wired up); \
say so plainly if a check passes.

If a request drifts from "does our own code handle malformed input safely" toward \
"find and weaponize a bug in Apple's iBoot/SEP," or toward targeting a real device, stop \
and explain the boundary rather than partially complying.
"""


def _text_result(text: str, is_error: bool = False) -> dict[str, Any]:
    result: dict[str, Any] = {"content": [{"type": "text", "text": text}]}
    if is_error:
        result["is_error"] = True
    return result


def _resolve_within(root: Path, relative: str) -> Path | None:
    try:
        candidate = (root / relative).resolve()
    except (OSError, ValueError):
        return None
    if not candidate.is_relative_to(root.resolve()):
        return None
    return candidate


def parse_environment_profile(path: Path) -> dict[str, Any] | None:
    """Minimal frontmatter parser for knowledge/environments/SCHEMA.md's shape — only
    top-level (non-indented) `key: value` lines; a wrapped continuation line (indented)
    is ignored, which is fine since the fields this track checks (status, approved_for)
    are always single-line in the schema."""
    text = path.read_text()
    parts = text.split("---")
    if len(parts) < 3:
        return None
    frontmatter = parts[1]
    fields: dict[str, Any] = {}
    for line in frontmatter.splitlines():
        if not line or line[0].isspace():
            continue
        m = re.match(r"^(\w+):\s*(.*)$", line)
        if not m:
            continue
        key, value = m.group(1), m.group(2).strip()
        if value.startswith("[") and value.endswith("]"):
            items = [v.strip() for v in value[1:-1].split(",") if v.strip()]
            fields[key] = items
        else:
            fields[key] = value
    return fields


async def run_static_analysis_impl(session: Session, check: str) -> dict[str, Any]:
    argv = STATIC_ANALYSIS_CHECKS.get(check)
    if argv is None:
        return _text_result(
            f"Refused: '{check}' is not a known check. Must be one of {sorted(STATIC_ANALYSIS_CHECKS)}.",
            is_error=True,
        )
    proc = subprocess.run(argv, cwd=REPO_ROOT, capture_output=True, text=True, timeout=300)
    record = {"argv": argv, "exit_code": proc.returncode, "stdout": proc.stdout, "stderr": proc.stderr}
    session.append_transcript(
        {"type": "wrapper_call", "tool": "run_static_analysis", "ts": utcnow_iso(), "data": record}
    )
    return _text_result((proc.stdout + "\n" + proc.stderr).strip())


async def read_knowledge_index_impl(session: Session, relative_path: str) -> dict[str, Any]:
    resolved = None
    for allowed_root in (VULN_RES_ROOT / "knowledge", VULN_RES_ROOT / "sweep-reports"):
        candidate = _resolve_within(allowed_root, relative_path)
        if candidate is not None and candidate.exists():
            resolved = candidate
            break
    if resolved is None:
        return _text_result(
            f"Refused: '{relative_path}' does not resolve inside vuln_res/knowledge/ "
            "or vuln_res/sweep-reports/, or does not exist.",
            is_error=True,
        )
    session.append_transcript(
        {"type": "read_call", "tool": "read_knowledge_index", "ts": utcnow_iso(), "data": {"path": str(resolved)}}
    )
    return _text_result(resolved.read_text()[:20000])


async def execute_in_environment_impl(session: Session, environment_id: str, capability: str) -> dict[str, Any]:
    profile_path = ENVIRONMENTS_DIR / f"{environment_id}.md"
    if not profile_path.exists():
        text = (
            f"Refused: no environment profile '{environment_id}' found under "
            "vuln_res/knowledge/environments/. No profile means no approved "
            "environment — ask the user to register one, don't improvise with the host."
        )
        session.append_transcript({
            "type": "environment_check", "tool": "execute_in_environment", "ts": utcnow_iso(),
            "data": {"environment_id": environment_id, "capability": capability, "result": "no_profile"},
        })
        return _text_result(text, is_error=True)

    fields = parse_environment_profile(profile_path) or {}
    status = fields.get("status")
    approved_for = fields.get("approved_for", [])

    if status != "active":
        text = f"Refused: environment '{environment_id}' has status '{status}', not 'active'."
        session.append_transcript({
            "type": "environment_check", "tool": "execute_in_environment", "ts": utcnow_iso(),
            "data": {"environment_id": environment_id, "capability": capability, "result": "not_active"},
        })
        return _text_result(text, is_error=True)

    if capability not in approved_for:
        text = (
            f"Refused: environment '{environment_id}' is approved for {approved_for}, "
            f"not '{capability}'. approved_for is scoped, not blanket — ask the user "
            "before proceeding, and update the profile once they say yes."
        )
        session.append_transcript({
            "type": "environment_check", "tool": "execute_in_environment", "ts": utcnow_iso(),
            "data": {"environment_id": environment_id, "capability": capability, "result": "capability_not_approved"},
        })
        return _text_result(text, is_error=True)

    text = (
        f"Environment '{environment_id}' is active and approved for '{capability}'. "
        "No execution backend is wired up in this Phase 1 service, so nothing was "
        "actually run — this check only confirms the gate itself works. Real "
        "execution against a real disposable environment is Phase 2 work."
    )
    session.append_transcript({
        "type": "environment_check", "tool": "execute_in_environment", "ts": utcnow_iso(),
        "data": {"environment_id": environment_id, "capability": capability, "result": "approved_but_inert"},
    })
    return _text_result(text)


def build_options(session: Session) -> ClaudeAgentOptions:
    @tool(
        "run_static_analysis",
        "Run a read-only static-analysis check against this repo's own code: "
        "clippy, fmt-check, or security-lint.",
        {"check": str},
    )
    async def run_static_analysis(args: dict[str, Any]) -> dict[str, Any]:
        return await run_static_analysis_impl(session, args.get("check", ""))

    @tool(
        "read_knowledge_index",
        "Read a file under vuln_res/knowledge/ or vuln_res/sweep-reports/ (read-only, "
        "path-contained to those trees).",
        {"relative_path": str},
    )
    async def read_knowledge_index(args: dict[str, Any]) -> dict[str, Any]:
        return await read_knowledge_index_impl(session, args.get("relative_path", ""))

    @tool(
        "execute_in_environment",
        "Check a registered vuln_res environment profile before any execution. "
        "In this Phase 1 service, a passing check is inert — nothing is actually run yet.",
        {"environment_id": str, "capability": str},
    )
    async def execute_in_environment(args: dict[str, Any]) -> dict[str, Any]:
        return await execute_in_environment_impl(
            session, args.get("environment_id", ""), args.get("capability", "")
        )

    server = create_sdk_mcp_server(
        name="vulnres",
        tools=[run_static_analysis, read_knowledge_index, execute_in_environment],
    )

    return ClaudeAgentOptions(
        system_prompt=SYSTEM_PROMPT,
        mcp_servers={"vulnres": server},
        allowed_tools=[
            "mcp__vulnres__run_static_analysis",
            "mcp__vulnres__read_knowledge_index",
            "mcp__vulnres__execute_in_environment",
        ],
        disallowed_tools=BUILTIN_TOOLS_TO_REMOVE,
        cwd=str(session.workspace_path),
    )
