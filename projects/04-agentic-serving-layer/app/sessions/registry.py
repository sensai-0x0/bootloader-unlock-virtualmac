"""In-memory session registry — Phase 1 only (see PROPOSAL.md's Phase 2 note on Redis).

A process restart loses every session. That's a stated Phase 1 limitation, not a bug.
"""

from __future__ import annotations

import asyncio
import uuid
from collections import deque
from pathlib import Path

from app.config import DISCONNECT_GRACE_SECONDS, EVENT_BUFFER_MAXLEN, SESSIONS_ROOT
from app.sessions.models import Session, SessionStatus, Track, utcnow_iso


class UnknownSessionError(KeyError):
    pass


class SessionRegistry:
    """Owns every live Session. One asyncio.Lock per session (held during a turn),
    never a single global lock — a turn on session A must never block session B."""

    def __init__(self) -> None:
        self._sessions: dict[str, Session] = {}

    def create(self, track: Track, auth_principal: str) -> Session:
        session_id = str(uuid.uuid4())
        workspace = (SESSIONS_ROOT / session_id).resolve()
        # Defense-in-depth: session_id is server-generated (uuid4), never client-supplied,
        # so this can't actually escape SESSIONS_ROOT — assert it anyway, cheaply.
        assert workspace.is_relative_to(SESSIONS_ROOT.resolve())
        workspace.mkdir(parents=True, exist_ok=False)
        (workspace / "work").mkdir()

        session = Session(
            id=session_id,
            track=track,
            workspace_path=workspace,
            auth_principal=auth_principal,
        )
        session.event_buffer = deque(maxlen=EVENT_BUFFER_MAXLEN)
        self._sessions[session_id] = session
        return session

    def get(self, session_id: str) -> Session:
        session = self._sessions.get(session_id)
        if session is None:
            raise UnknownSessionError(session_id)
        return session

    def all_ids(self) -> list[str]:
        return list(self._sessions.keys())

    async def emit(self, session: Session, event: dict) -> None:
        """Record an event: transcript (always), replay buffer (always), live
        subscribers (best-effort — a slow/gone subscriber never blocks the turn)."""
        session.append_transcript(event)
        session.event_buffer.append(event)
        for queue in list(session.subscribers):
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                pass  # best-effort fan-out; the replay buffer is the durable copy

    def subscribe(self, session: Session) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue(maxsize=1000)
        session.subscribers.add(queue)
        return queue

    def unsubscribe(self, session: Session, queue: asyncio.Queue) -> None:
        session.subscribers.discard(queue)

    def mark_disconnected(self, session: Session, loop: asyncio.AbstractEventLoop) -> None:
        """A WS drop never tears down the live ClaudeSDKClient — only a grace-period
        timer that, if it elapses with no reconnect, calls close()."""
        if session.status == SessionStatus.CLOSED:
            return
        session.status = SessionStatus.DISCONNECTED
        if session.disconnect_timer is not None:
            session.disconnect_timer.cancel()

        async def _teardown_after_grace() -> None:
            try:
                await asyncio.sleep(DISCONNECT_GRACE_SECONDS)
            except asyncio.CancelledError:
                return
            if session.status == SessionStatus.DISCONNECTED:
                await self.close(session)

        session.disconnect_timer = loop.create_task(_teardown_after_grace())

    def mark_reconnected(self, session: Session) -> None:
        if session.disconnect_timer is not None:
            session.disconnect_timer.cancel()
            session.disconnect_timer = None
        if session.status == SessionStatus.DISCONNECTED:
            session.status = SessionStatus.IDLE

    async def close(self, session: Session) -> None:
        """Tear down the SDK client; retain the workspace directory and transcript —
        never deleted automatically (see PROPOSAL.md open risk on retention)."""
        if session.client is not None:
            try:
                await session.client.disconnect()
            except Exception:
                pass
            session.client = None
        session.status = SessionStatus.CLOSED
        await self.emit(session, {"type": "session_closed", "session_id": session.id, "ts": utcnow_iso(), "data": {}})


registry = SessionRegistry()
