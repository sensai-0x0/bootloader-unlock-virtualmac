"""Static bearer-token auth — a prototype gate on *which track* a caller may start.

Explicitly not a real security boundary: no expiry, no rotation, no rate limiting.
See PROPOSAL.md's "Open risks" section. Do not expose this service beyond localhost
as-is.
"""

from __future__ import annotations

from fastapi import Header, HTTPException

from app.config import load_token_table
from app.sessions.models import Track


class Principal:
    def __init__(self, token: str, name: str, allowed_tracks: set[Track]):
        self.token = token
        self.name = name
        self.allowed_tracks = allowed_tracks

    def can_use(self, track: Track) -> bool:
        return track in self.allowed_tracks


def parse_token_table() -> dict[str, Principal]:
    table = load_token_table()
    parsed: dict[str, Principal] = {}
    for token, entry in table.items():
        parsed[token] = Principal(
            token=token,
            name=entry.get("principal", "unknown"),
            allowed_tracks={Track(t) for t in entry.get("allowed_tracks", [])},
        )
    return parsed


async def require_principal(authorization: str | None = Header(default=None)) -> Principal:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="missing or malformed bearer token")
    token = authorization.split(" ", 1)[1].strip()
    table = parse_token_table()
    principal = table.get(token)
    if principal is None:
        raise HTTPException(status_code=401, detail="unrecognized token")
    return principal


def require_track_access(principal: Principal, track: Track) -> None:
    if not principal.can_use(track):
        raise HTTPException(
            status_code=403,
            detail=f"token '{principal.name}' is not scoped to track '{track.value}'",
        )
