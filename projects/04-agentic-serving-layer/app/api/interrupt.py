from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.auth import Principal, require_principal
from app.sessions.models import utcnow_iso
from app.sessions.registry import UnknownSessionError, registry

router = APIRouter()


@router.post("/sessions/{session_id}/interrupt")
async def interrupt_session(session_id: str, principal: Principal = Depends(require_principal)) -> dict:
    try:
        session = registry.get(session_id)
    except UnknownSessionError:
        raise HTTPException(status_code=404, detail="unknown session")
    if session.auth_principal != principal.name:
        raise HTTPException(status_code=403, detail="session belongs to a different principal")
    if session.client is None:
        raise HTTPException(status_code=409, detail="session is closed")

    await session.client.interrupt()
    await registry.emit(session, {
        "type": "interrupt_ack", "session_id": session.id, "ts": utcnow_iso(), "data": {},
    })
    return {"interrupted": True}
