from __future__ import annotations

from claude_agent_sdk import ClaudeAgentOptions

from app.sessions.models import Session, Track
from app.tracks import bootloader, vulnres


def build_options(session: Session) -> ClaudeAgentOptions:
    if session.track == Track.BOOTLOADER:
        return bootloader.build_options(session)
    if session.track == Track.VULN_RESEARCH:
        return vulnres.build_options(session)
    raise ValueError(f"unknown track: {session.track}")
