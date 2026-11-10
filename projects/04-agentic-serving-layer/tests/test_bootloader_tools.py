"""Exercises the bootloader track's tool impls directly — no Claude Agent SDK involved.

The safety-critical property under test: there is no code path in this module that can
ever shell out to `apply` or `revert`, independent of what a caller asks for.
"""

from __future__ import annotations

import pytest

from app.tracks import bootloader
from tests.conftest import read_transcript


def test_module_never_constructs_apply_or_revert_argv():
    """Static sanity check: these subcommand strings must not appear anywhere in the
    module except inside the system prompt's prose explaining *why* they don't exist."""
    import inspect

    source = inspect.getsource(bootloader)
    prompt_start = source.index('SYSTEM_PROMPT = """')
    prompt_end = source.index('"""', prompt_start + len('SYSTEM_PROMPT = """')) + 3
    code_without_prompt = source[:prompt_start] + source[prompt_end:]
    assert '"apply"' not in code_without_prompt
    assert '"revert"' not in code_without_prompt
    assert "ALLOWED_TARGETS" in source  # the allowlist that makes plan's target safe


@pytest.mark.asyncio
async def test_evaluate_boot_state_runs_real_binary_and_records_transcript(bootloader_session):
    result = await bootloader.evaluate_boot_state_impl(bootloader_session)
    assert "content" in result
    transcript = read_transcript(bootloader_session)
    assert len(transcript) == 1
    record = transcript[0]["data"]
    assert record["argv"][-2:] == ["evaluate", "--json"]
    assert "bputil-eval" in record["argv"][0]


@pytest.mark.asyncio
async def test_plan_with_valid_target_runs_and_records(bootloader_session):
    result = await bootloader.plan_security_transition_impl(bootloader_session, "full")
    assert "content" in result
    transcript = read_transcript(bootloader_session)
    assert len(transcript) == 1
    assert transcript[0]["data"]["argv"][-3:-1] == ["plan", "full"]


@pytest.mark.asyncio
@pytest.mark.parametrize("smuggled_target", ["apply", "revert", "Apply", "full; apply", ""])
async def test_plan_refuses_anything_outside_the_allowlist_without_running_anything(
    bootloader_session, smuggled_target
):
    result = await bootloader.plan_security_transition_impl(bootloader_session, smuggled_target)
    assert result.get("is_error") is True
    # The structural guarantee: no subprocess call was ever recorded for a refused target.
    assert read_transcript(bootloader_session) == []


@pytest.mark.asyncio
async def test_verify_refuses_invalid_json_without_running_anything(bootloader_session):
    result = await bootloader.verify_against_baseline_impl(bootloader_session, "{not valid json")
    assert result.get("is_error") is True
    assert read_transcript(bootloader_session) == []


@pytest.mark.asyncio
async def test_verify_with_valid_baseline_writes_file_and_runs(bootloader_session):
    fresh = await bootloader.evaluate_boot_state_impl(bootloader_session)
    baseline_json = fresh["content"][0]["text"]
    result = await bootloader.verify_against_baseline_impl(bootloader_session, baseline_json)
    assert "content" in result
    baseline_file = bootloader_session.workspace_path / "work" / "baseline.json"
    assert baseline_file.exists()
    transcript = read_transcript(bootloader_session)
    assert transcript[-1]["data"]["argv"][-1] == "--json"
    assert "verify" in transcript[-1]["data"]["argv"]
    assert str(baseline_file) in transcript[-1]["data"]["argv"]


@pytest.mark.asyncio
async def test_write_evidence_report_runs_and_records(bootloader_session):
    result = await bootloader.write_evidence_report_impl(bootloader_session, "test-label")
    assert "content" in result
    transcript = read_transcript(bootloader_session)
    assert transcript[-1]["data"]["argv"][1] == "report"
    assert "test-label" in transcript[-1]["data"]["argv"]
