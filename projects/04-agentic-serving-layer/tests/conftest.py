from __future__ import annotations

import json
import uuid
from pathlib import Path

import pytest

from app.sessions.models import Session, Track


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    ws = tmp_path / "session-workspace"
    (ws / "work").mkdir(parents=True)
    return ws


@pytest.fixture
def bootloader_session(workspace: Path) -> Session:
    return Session(
        id=str(uuid.uuid4()),
        track=Track.BOOTLOADER,
        workspace_path=workspace,
        auth_principal="test-principal",
    )


@pytest.fixture
def vulnres_session(workspace: Path) -> Session:
    return Session(
        id=str(uuid.uuid4()),
        track=Track.VULN_RESEARCH,
        workspace_path=workspace,
        auth_principal="test-principal",
    )


def read_transcript(session: Session) -> list[dict]:
    path = session.transcript_path()
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line]
