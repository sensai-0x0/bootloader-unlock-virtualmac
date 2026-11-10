"""GET /portfolio/brief — thin, session-less read of projects/supervisor-agent's own
deterministic score/render output. No LLM loop, no new execution surface: purely
additive. See PROPOSAL.md on why this is included in Phase 1."""

from __future__ import annotations

import json
import subprocess
import sys

from fastapi import APIRouter, Depends, HTTPException

from app.auth import Principal, require_principal
from app.config import REPO_ROOT, SUPERVISOR_SCRIPT

router = APIRouter()


@router.get("/portfolio/brief")
async def portfolio_brief(_: Principal = Depends(require_principal)) -> dict:
    if not SUPERVISOR_SCRIPT.exists():
        raise HTTPException(status_code=503, detail="supervisor-agent tooling not found")

    render = subprocess.run(
        [sys.executable, str(SUPERVISOR_SCRIPT), "render"],
        cwd=REPO_ROOT, capture_output=True, text=True, timeout=60,
    )
    score = subprocess.run(
        [sys.executable, str(SUPERVISOR_SCRIPT), "score"],
        cwd=REPO_ROOT, capture_output=True, text=True, timeout=60,
    )
    if score.returncode != 0:
        raise HTTPException(status_code=502, detail=f"supervisor score failed: {score.stderr.strip()}")

    try:
        ranking = json.loads(score.stdout)
    except json.JSONDecodeError:
        ranking = {"raw_stdout": score.stdout}

    fused_portfolio_path = SUPERVISOR_SCRIPT.parent.parent / "state" / "fused-portfolio.md"
    fused_markdown = fused_portfolio_path.read_text() if fused_portfolio_path.exists() else None

    return {
        "render_ok": render.returncode == 0,
        "ranking": ranking,
        "fused_portfolio_markdown": fused_markdown,
    }
