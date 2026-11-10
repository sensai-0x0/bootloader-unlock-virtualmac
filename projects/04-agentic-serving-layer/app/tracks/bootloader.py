"""Bootloader track: evaluate_boot_state, plan_security_transition,
verify_against_baseline, write_evidence_report.

No tool, anywhere in this module, is shaped like `apply` or `revert` — the exclusion is
structural (there is no such schema, no such code path), not a runtime check on a
free-form argument. See ../../PROPOSAL.md and ../../CLAUDE.md.

Tool logic lives in plain `_impl` async functions, each testable directly without the
Claude Agent SDK in the loop; `build_options` wraps them with `@tool` for real sessions.
"""

from __future__ import annotations

import json
import subprocess
from typing import Any

from claude_agent_sdk import ClaudeAgentOptions, create_sdk_mcp_server, tool

from app.config import REPO_ROOT, bputil_eval_binary
from app.sessions.models import Session, utcnow_iso

ALLOWED_TARGETS = {"full", "reduced-kexts", "permissive-custom-kernel"}

# Every built-in Claude Code tool, removed from this track's context entirely —
# `disallowed_tools` (not `allowed_tools`, which only auto-approves, per the SDK docs)
# is what actually keeps the model from seeing a generic shell.
BUILTIN_TOOLS_TO_REMOVE = [
    "Bash", "Read", "Write", "Edit", "Glob", "Grep", "WebFetch", "WebSearch",
    "Agent", "NotebookEdit", "TodoWrite", "TaskCreate", "TaskGet", "TaskUpdate",
    "TaskList", "AskUserQuestion", "ExitPlanMode", "ListMcpResourcesTool",
    "ReadMcpResourceTool", "Monitor", "TaskStop",
]

SYSTEM_PROMPT = """You are the bootloader-posture agent for bputil-eval, a read-only \
boot-chain trust evaluator for Apple Silicon Macs.

You have exactly four tools, each a fixed wrapper around one real CLI subcommand:
- evaluate_boot_state: measure the current boot-chain trust state (fresh, every time)
- plan_security_transition: diff current state against a target profile (full, \
reduced-kexts, permissive-custom-kernel); never executes anything
- verify_against_baseline: diff a prior BootState JSON against a fresh measurement
- write_evidence_report: write the hash-chained evidence bundle for this session

There is no tool to apply or revert a security-policy change anywhere in this service. \
That requires a human physically present in One True Recovery (1TR) typing Apple's own \
credentials. This is a hard boundary, not a preference. If asked to unlock, lower \
security, "apply the plan," or anything that would mutate the device, explain this \
plainly: describe what plan_security_transition already showed, and that the actual \
change must be carried out by the device owner themselves through Apple's own \
bputil/kmutil/csrutil, in 1TR. Never claim a state change happened without a fresh \
evaluate_boot_state call proving it — honesty of state is non-negotiable here.
"""


def run_bputil_eval(argv: list[str]) -> dict[str, Any]:
    """The single call site for this track's subprocess invocations — mirrors
    src/wrapper.rs's "one audited call site" discipline in Python. `argv`'s first
    element is always one of evaluate/plan/verify/report; there is no caller in this
    module that can pass apply/revert, since no impl function below ever constructs one."""
    binary = bputil_eval_binary()
    full_argv = [str(binary), *argv]
    proc = subprocess.run(
        full_argv, cwd=REPO_ROOT, capture_output=True, text=True, timeout=60
    )
    return {
        "argv": full_argv,
        "exit_code": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
    }


def _text_result(text: str, is_error: bool = False) -> dict[str, Any]:
    result: dict[str, Any] = {"content": [{"type": "text", "text": text}]}
    if is_error:
        result["is_error"] = True
    return result


async def evaluate_boot_state_impl(session: Session) -> dict[str, Any]:
    record = run_bputil_eval(["evaluate", "--json"])
    session.append_transcript(
        {"type": "wrapper_call", "tool": "evaluate_boot_state", "ts": utcnow_iso(), "data": record}
    )
    return _text_result(record["stdout"] or record["stderr"])


async def plan_security_transition_impl(session: Session, target: str) -> dict[str, Any]:
    if target not in ALLOWED_TARGETS:
        return _text_result(
            f"Refused: '{target}' is not a valid target. Must be one of {sorted(ALLOWED_TARGETS)}.",
            is_error=True,
        )
    record = run_bputil_eval(["plan", target, "--json"])
    session.append_transcript(
        {"type": "wrapper_call", "tool": "plan_security_transition", "ts": utcnow_iso(), "data": record}
    )
    return _text_result(record["stdout"] or record["stderr"])


async def verify_against_baseline_impl(session: Session, baseline_json: str) -> dict[str, Any]:
    try:
        json.loads(baseline_json)
    except json.JSONDecodeError as exc:
        return _text_result(f"Refused: baseline_json is not valid JSON ({exc}).", is_error=True)
    baseline_path = session.workspace_path / "work" / "baseline.json"
    baseline_path.write_text(baseline_json)
    record = run_bputil_eval(["verify", "--baseline", str(baseline_path), "--json"])
    session.append_transcript(
        {"type": "wrapper_call", "tool": "verify_against_baseline", "ts": utcnow_iso(), "data": record}
    )
    return _text_result(record["stdout"] or record["stderr"])


async def write_evidence_report_impl(session: Session, session_label: str = "") -> dict[str, Any]:
    out_dir = session.workspace_path / "work" / "evidence"
    argv = ["report", "--out-dir", str(out_dir)]
    if session_label:
        argv += ["--session-id", session_label]
    record = run_bputil_eval(argv)
    session.append_transcript(
        {"type": "wrapper_call", "tool": "write_evidence_report", "ts": utcnow_iso(), "data": record}
    )
    return _text_result(record["stdout"] or record["stderr"])


def build_options(session: Session) -> ClaudeAgentOptions:
    @tool(
        "evaluate_boot_state",
        "Measure the current boot-chain trust state (read-only, always fresh).",
        {},
    )
    async def evaluate_boot_state(args: dict[str, Any]) -> dict[str, Any]:
        return await evaluate_boot_state_impl(session)

    @tool(
        "plan_security_transition",
        "Diff current boot state against a target profile and print the resulting "
        "plan as data. Never executes anything.",
        {"target": str},
    )
    async def plan_security_transition(args: dict[str, Any]) -> dict[str, Any]:
        return await plan_security_transition_impl(session, args.get("target", ""))

    @tool(
        "verify_against_baseline",
        "Diff a prior BootState JSON (from an earlier evaluate_boot_state call) "
        "against a fresh measurement. Read-only.",
        {"baseline_json": str},
    )
    async def verify_against_baseline(args: dict[str, Any]) -> dict[str, Any]:
        return await verify_against_baseline_impl(session, args.get("baseline_json", ""))

    @tool(
        "write_evidence_report",
        "Write the hash-chained evidence bundle for this session.",
        {"session_label": str},
    )
    async def write_evidence_report(args: dict[str, Any]) -> dict[str, Any]:
        return await write_evidence_report_impl(session, args.get("session_label", ""))

    server = create_sdk_mcp_server(
        name="bootloader",
        tools=[
            evaluate_boot_state,
            plan_security_transition,
            verify_against_baseline,
            write_evidence_report,
        ],
    )

    return ClaudeAgentOptions(
        system_prompt=SYSTEM_PROMPT,
        mcp_servers={"bootloader": server},
        allowed_tools=[
            "mcp__bootloader__evaluate_boot_state",
            "mcp__bootloader__plan_security_transition",
            "mcp__bootloader__verify_against_baseline",
            "mcp__bootloader__write_evidence_report",
        ],
        disallowed_tools=BUILTIN_TOOLS_TO_REMOVE,
        cwd=str(session.workspace_path),
    )
