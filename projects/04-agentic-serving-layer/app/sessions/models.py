from __future__ import annotations

import asyncio
import json
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any


class Track(str, Enum):
    BOOTLOADER = "bootloader"
    VULN_RESEARCH = "vuln-research"


class SessionStatus(str, Enum):
    ACTIVE = "active"
    IDLE = "idle"
    DISCONNECTED = "disconnected"
    CLOSED = "closed"


def utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class Session:
    id: str
    track: Track
    workspace_path: Path
    auth_principal: str
    created_at: str = field(default_factory=utcnow_iso)
    last_activity_at: str = field(default_factory=utcnow_iso)
    status: SessionStatus = SessionStatus.ACTIVE

    # The live SDK handle. None once CLOSED. Not serialized in API responses.
    client: Any = field(default=None, repr=False)

    # One lock per session so concurrent turns on *different* sessions never block
    # each other; a turn on *this* session is still serialized against itself.
    lock: asyncio.Lock = field(default_factory=asyncio.Lock, repr=False)

    # Bounded replay buffer for WebSocket reconnects — see registry.py.
    event_buffer: deque = field(default_factory=lambda: deque(maxlen=500), repr=False)

    # Live WebSocket subscribers (usually 0 or 1 in Phase 1; not fanned out further).
    subscribers: set = field(default_factory=set, repr=False)

    # Handle for the pending disconnect-grace teardown, if any.
    disconnect_timer: Any = field(default=None, repr=False)

    def touch(self) -> None:
        self.last_activity_at = utcnow_iso()

    def transcript_path(self) -> Path:
        return self.workspace_path / "transcript.jsonl"

    def append_transcript(self, event: dict) -> None:
        with self.transcript_path().open("a") as f:
            f.write(json.dumps(event, sort_keys=True) + "\n")

    def to_public_dict(self) -> dict:
        return {
            "session_id": self.id,
            "track": self.track.value,
            "status": self.status.value,
            "created_at": self.created_at,
        }
