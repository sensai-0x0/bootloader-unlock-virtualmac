"""POST /sessions/{id}/messages — sends a turn into the live SDK client and returns
immediately; every resulting event streams over that session's WebSocket. Decoupling
message-send from the stream means a WS disconnect never aborts an in-flight turn."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.auth import Principal, require_principal
from app.sessions.models import Session, SessionStatus, utcnow_iso
from app.sessions.registry import UnknownSessionError, registry

router = APIRouter()


class SendMessageRequest(BaseModel):
    content: str


def _get_owned_session(session_id: str, principal: Principal) -> Session:
    try:
        session = registry.get(session_id)
    except UnknownSessionError:
        raise HTTPException(status_code=404, detail="unknown session")
    if session.auth_principal != principal.name:
        raise HTTPException(status_code=403, detail="session belongs to a different principal")
    if session.client is None or session.status == SessionStatus.CLOSED:
        raise HTTPException(status_code=409, detail="session is closed")
    return session


async def _run_turn(session: Session, content: str) -> None:
    from claude_agent_sdk import AssistantMessage, ResultMessage, TextBlock, ToolResultBlock, ToolUseBlock

    async with session.lock:
        session.status = SessionStatus.ACTIVE
        session.touch()
        try:
            await session.client.query(content)
            async for message in session.client.receive_response():
                if isinstance(message, AssistantMessage):
                    for block in message.content:
                        if isinstance(block, TextBlock):
                            await registry.emit(session, {
                                "type": "assistant_delta", "session_id": session.id,
                                "ts": utcnow_iso(), "data": {"text": block.text},
                            })
                        elif isinstance(block, ToolUseBlock):
                            await registry.emit(session, {
                                "type": "tool_use", "session_id": session.id, "ts": utcnow_iso(),
                                "data": {"id": block.id, "name": block.name, "input": block.input},
                            })
                        elif isinstance(block, ToolResultBlock):
                            await registry.emit(session, {
                                "type": "tool_result", "session_id": session.id, "ts": utcnow_iso(),
                                "data": {
                                    "tool_use_id": block.tool_use_id,
                                    "content": block.content,
                                    "is_error": bool(block.is_error),
                                },
                            })
                elif isinstance(message, ResultMessage):
                    if message.is_error:
                        await registry.emit(session, {
                            "type": "error", "session_id": session.id, "ts": utcnow_iso(),
                            "data": {"subtype": message.subtype, "result": message.result},
                        })
        except Exception as exc:
            await registry.emit(session, {
                "type": "error", "session_id": session.id, "ts": utcnow_iso(),
                "data": {"message": str(exc)},
            })
        finally:
            session.touch()
            if session.status == SessionStatus.ACTIVE:
                session.status = SessionStatus.IDLE


@router.post("/sessions/{session_id}/messages", status_code=202)
async def send_message(
    session_id: str, body: SendMessageRequest, principal: Principal = Depends(require_principal)
) -> dict:
    session = _get_owned_session(session_id, principal)
    asyncio.create_task(_run_turn(session, body.content))
    return {"accepted": True, "session_id": session.id}
