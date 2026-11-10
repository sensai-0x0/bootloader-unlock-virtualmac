from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.auth import Principal, require_principal, require_track_access
from app.sessions.models import Session, SessionStatus, Track
from app.sessions.registry import UnknownSessionError, registry
from app.tracks import build_options

router = APIRouter()


class CreateSessionRequest(BaseModel):
    track: Track


async def _connect_client(session: Session) -> None:
    from claude_agent_sdk import ClaudeSDKClient

    options = build_options(session)
    client = ClaudeSDKClient(options=options)
    await client.connect()
    session.client = client


@router.post("/sessions")
async def create_session(
    body: CreateSessionRequest, principal: Principal = Depends(require_principal)
) -> dict:
    require_track_access(principal, body.track)
    session = registry.create(track=body.track, auth_principal=principal.name)
    try:
        await _connect_client(session)
    except Exception as exc:  # connecting failed — don't leave a half-open session around
        session.status = SessionStatus.CLOSED
        raise HTTPException(status_code=502, detail=f"failed to start agent session: {exc}") from exc
    return session.to_public_dict()


@router.get("/sessions/{session_id}")
async def get_session(session_id: str, principal: Principal = Depends(require_principal)) -> dict:
    try:
        session = registry.get(session_id)
    except UnknownSessionError:
        raise HTTPException(status_code=404, detail="unknown session")
    if session.auth_principal != principal.name:
        raise HTTPException(status_code=403, detail="session belongs to a different principal")
    return session.to_public_dict()
