"""GET /sessions/{id}/stream (WebSocket) — event frames:
assistant_delta | tool_use | tool_result | interrupt_ack | error | session_closed.

A disconnect never tears down the live ClaudeSDKClient (see sessions/registry.py's
grace-period teardown). A reconnect within the grace period replays this session's
bounded event buffer before resuming live events, so nothing silently vanishes.
"""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.auth import parse_token_table
from app.sessions.registry import UnknownSessionError, registry

router = APIRouter()


@router.websocket("/sessions/{session_id}/stream")
async def stream_session(websocket: WebSocket, session_id: str) -> None:
    token = websocket.query_params.get("token")
    auth_header = websocket.headers.get("authorization", "")
    if not token and auth_header.lower().startswith("bearer "):
        token = auth_header.split(" ", 1)[1].strip()

    table = parse_token_table()
    principal = table.get(token or "")
    if principal is None:
        await websocket.close(code=4401)
        return

    try:
        session = registry.get(session_id)
    except UnknownSessionError:
        await websocket.close(code=4404)
        return
    if session.auth_principal != principal.name:
        await websocket.close(code=4403)
        return

    await websocket.accept()

    # Replay the bounded buffer first, so a reconnect sees anything emitted while gone.
    for event in list(session.event_buffer):
        await websocket.send_json(event)

    registry.mark_reconnected(session)
    queue = registry.subscribe(session)
    try:
        while True:
            event = await queue.get()
            await websocket.send_json(event)
    except WebSocketDisconnect:
        pass
    finally:
        registry.unsubscribe(session, queue)
        registry.mark_disconnected(session, asyncio.get_running_loop())
