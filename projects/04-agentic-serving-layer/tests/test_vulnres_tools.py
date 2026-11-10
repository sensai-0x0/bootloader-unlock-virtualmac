"""Exercises the vuln-research track's tool impls directly — no Claude Agent SDK involved.

The safety-critical property under test: execute_in_environment refuses anything
without a matching, active, capability-approved profile, and even a passing check
never spawns a subprocess in this Phase 1 service.
"""

from __future__ import annotations

import pytest

from app.config import VULN_RES_ROOT
from app.tracks import vulnres
from tests.conftest import read_transcript


@pytest.mark.asyncio
async def test_static_analysis_rejects_unknown_check_without_running_anything(vulnres_session):
    result = await vulnres.run_static_analysis_impl(vulnres_session, "rm -rf /")
    assert result.get("is_error") is True
    assert read_transcript(vulnres_session) == []


@pytest.mark.asyncio
async def test_static_analysis_runs_a_known_check(vulnres_session):
    result = await vulnres.run_static_analysis_impl(vulnres_session, "fmt-check")
    assert "content" in result
    transcript = read_transcript(vulnres_session)
    assert transcript[0]["data"]["argv"] == ["cargo", "fmt", "--check"]


@pytest.mark.asyncio
async def test_read_knowledge_index_reads_a_real_file(vulnres_session):
    result = await vulnres.read_knowledge_index_impl(vulnres_session, "INDEX.md")
    assert "content" in result
    assert result["content"][0]["text"]  # non-empty


@pytest.mark.asyncio
@pytest.mark.parametrize("escape_attempt", [
    "../../CLAUDE.md",
    "../../spec/build-spec.md",
    "../../../etc/passwd",
])
async def test_read_knowledge_index_refuses_path_escape(vulnres_session, escape_attempt):
    result = await vulnres.read_knowledge_index_impl(vulnres_session, escape_attempt)
    assert result.get("is_error") is True


@pytest.mark.asyncio
async def test_execute_in_environment_refuses_unregistered_profile(vulnres_session):
    result = await vulnres.execute_in_environment_impl(
        vulnres_session, "no-such-environment", "fuzzing"
    )
    assert result.get("is_error") is True
    transcript = read_transcript(vulnres_session)
    assert transcript[0]["data"]["result"] == "no_profile"


@pytest.mark.asyncio
async def test_execute_in_environment_refuses_capability_outside_approved_for(vulnres_session):
    # Real profile in this repo today, approved only for measurement/verification work —
    # not fuzzing. Confirms approved_for is scoped, not blanket, against real repo data.
    result = await vulnres.execute_in_environment_impl(
        vulnres_session, "vm-sec-research-25d125", "fuzzing"
    )
    assert result.get("is_error") is True
    transcript = read_transcript(vulnres_session)
    assert transcript[0]["data"]["result"] == "capability_not_approved"


@pytest.mark.asyncio
async def test_execute_in_environment_passes_for_an_approved_capability_but_is_inert(vulnres_session):
    result = await vulnres.execute_in_environment_impl(
        vulnres_session, "vm-sec-research-25d125", "bputil-eval-live-tool-verification"
    )
    assert result.get("is_error") is not True
    assert "No execution backend is wired up" in result["content"][0]["text"]
    transcript = read_transcript(vulnres_session)
    assert transcript[0]["data"]["result"] == "approved_but_inert"


@pytest.mark.asyncio
async def test_execute_in_environment_with_synthetic_profile(vulnres_session, tmp_path, monkeypatch):
    envs_dir = tmp_path / "environments"
    envs_dir.mkdir()
    (envs_dir / "synthetic-env.md").write_text(
        "---\n"
        "id: synthetic-env\n"
        "provider: docker\n"
        "lifecycle: disposable\n"
        "status: active\n"
        "approved_for: [fuzzing]\n"
        "---\n\nTest fixture only.\n"
    )
    monkeypatch.setattr(vulnres, "ENVIRONMENTS_DIR", envs_dir)

    refused = await vulnres.execute_in_environment_impl(vulnres_session, "synthetic-env", "exploit-dev")
    assert refused.get("is_error") is True

    approved = await vulnres.execute_in_environment_impl(vulnres_session, "synthetic-env", "fuzzing")
    assert approved.get("is_error") is not True
    transcript = read_transcript(vulnres_session)
    assert transcript[-1]["data"]["result"] == "approved_but_inert"


def test_parse_environment_profile_handles_real_schema_file():
    fields = vulnres.parse_environment_profile(
        VULN_RES_ROOT / "knowledge" / "environments" / "vm-sec-research-25d125.md"
    )
    assert fields is not None
    assert fields["status"] == "active"
    assert "bputil-eval-live-tool-verification" in fields["approved_for"]
