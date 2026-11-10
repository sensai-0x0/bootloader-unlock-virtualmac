from __future__ import annotations

from fastapi import FastAPI

from app.api import interrupt, messages, portfolio, sessions, ws
from app.config import SESSIONS_ROOT

SESSIONS_ROOT.mkdir(parents=True, exist_ok=True)

app = FastAPI(
    title="Agentic Serving Layer (Phase 1)",
    description="Bootloader track + vuln-research track, hard-separated. See PROPOSAL.md.",
)

app.include_router(sessions.router)
app.include_router(messages.router)
app.include_router(interrupt.router)
app.include_router(ws.router)
app.include_router(portfolio.router)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
