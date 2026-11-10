"""HTTP/WebSocket-level tests against the real FastAPI app, with a fake
ClaudeSDKClient standing in for the real one — no real Claude API calls, no cost,
no credentials needed. Verifies the session lifecycle, the SDK-message-to-wire-event
mapping, interrupt, and the disconnect/reconnect replay contract from PROPOSAL.md.
"""

from __future__ import annotations

import asyncio
import json
import time

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.sessions.registry import registry
from tests.fake_sdk_client import FakeClaudeSDKClient

TOKEN_BOOTLOADER = "sk-test-bootloader"
TOKEN_VULNRES = "sk-test-vulnres"


@pytest.fixture(autouse=True)
def fake_tokens(tmp_path, monkeypatch):
    tokens_path = tmp_path / "tokens.json"
    tokens_path.write_text(json.dumps({
        TOKEN_BOOTLOADER: {"principal": "p1", "allowed_tracks": ["bootloader"]},
        TOKEN_VULNRES: {"principal": "p2", "allowed_tracks": ["vuln-research"]},
    }))
    monkeypatch.setattr("app.config._TOKENS_PATH", tokens_path)


@pytest.fixture(autouse=True)
def fake_sdk(monkeypatch):
    monkeypatch.setattr("claude_agent_sdk.ClaudeSDKClient", FakeClaudeSDKClient)


@pytest.fixture
def client():
    # Entered as a context manager so the app's portal/event loop stays alive across
    # calls — without this, a background asyncio.create_task scheduled during one
    # call (e.g. the disconnect-grace teardown timer) gets orphaned the moment that
    # call's own portal closes, instead of running to completion.
    with TestClient(app) as c:
        yield c


def auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_create_session_requires_auth(client):
    r = client.post("/sessions", json={"track": "bootloader"})
    assert r.status_code == 401


def test_create_session_requires_track_scope(client):
    r = client.post("/sessions", json={"track": "vuln-research"}, headers=auth(TOKEN_BOOTLOADER))
    assert r.status_code == 403


def test_create_session_connects_fake_client(client):
    r = client.post("/sessions", json={"track": "bootloader"}, headers=auth(TOKEN_BOOTLOADER))
    assert r.status_code == 200
    body = r.json()
    assert body["track"] == "bootloader"
    assert body["status"] == "active"
    session = registry.get(body["session_id"])
    assert isinstance(session.client, FakeClaudeSDKClient)
    assert session.client.connected is True
    # Track selects a distinct tool server — the one structural guarantee that
    # the two tracks can never share a capability surface.
    assert "bootloader" in session.client.options.mcp_servers
    assert "vulnres" not in session.client.options.mcp_servers


def test_create_vuln_research_session_gets_the_other_tool_server(client):
    # The symmetric check: a vuln-research-track session gets exactly the opposite
    # tool server, never the bootloader one — the separation holds in both directions.
    r = client.post("/sessions", json={"track": "vuln-research"}, headers=auth(TOKEN_VULNRES))
    assert r.status_code == 200
    body = r.json()
    assert body["track"] == "vuln-research"
    session = registry.get(body["session_id"])
    assert "vulnres" in session.client.options.mcp_servers
    assert "bootloader" not in session.client.options.mcp_servers
    # No raw Bash/Read/Write tool is left reachable in either track's context.
    for builtin in ("Bash", "Read", "Write"):
        assert builtin in session.client.options.disallowed_tools


def test_send_message_maps_sdk_events_onto_the_wire_contract(client):
    from claude_agent_sdk import (
        AssistantMessage,
        ResultMessage,
        TextBlock,
        ToolResultBlock,
        ToolUseBlock,
    )

    r = client.post("/sessions", json={"track": "bootloader"}, headers=auth(TOKEN_BOOTLOADER))
    session_id = r.json()["session_id"]
    session = registry.get(session_id)

    session.client.queue_response([
        AssistantMessage(
            content=[
                TextBlock(text="hello"),
                ToolUseBlock(id="t1", name="evaluate_boot_state", input={}),
            ],
            model="claude-x",
        ),
        AssistantMessage(
            content=[ToolResultBlock(tool_use_id="t1", content="ok", is_error=False)],
            model="claude-x",
        ),
        ResultMessage(
            subtype="success", duration_ms=1, duration_api_ms=1, is_error=False,
            num_turns=1, session_id=session_id, total_cost_usd=0.0, usage={},
        ),
    ])

    resp = client.post(
        f"/sessions/{session_id}/messages", json={"content": "evaluate"}, headers=auth(TOKEN_BOOTLOADER)
    )
    assert resp.status_code == 202

    for _ in range(100):
        if list(session.event_buffer):
            break
        time.sleep(0.02)

    types = [e["type"] for e in session.event_buffer]
    assert "assistant_delta" in types
    assert "tool_use" in types
    assert "tool_result" in types
    assert "error" not in types
    assert session.client.queries == ["evaluate"]


def test_interrupt_calls_sdk_and_emits_ack(client):
    r = client.post("/sessions", json={"track": "bootloader"}, headers=auth(TOKEN_BOOTLOADER))
    session_id = r.json()["session_id"]
    session = registry.get(session_id)

    resp = client.post(f"/sessions/{session_id}/interrupt", headers=auth(TOKEN_BOOTLOADER))
    assert resp.status_code == 200
    assert session.client.interrupt_count == 1
    assert session.event_buffer[-1]["type"] == "interrupt_ack"


def test_websocket_rejects_bad_token(client):
    r = client.post("/sessions", json={"track": "bootloader"}, headers=auth(TOKEN_BOOTLOADER))
    session_id = r.json()["session_id"]
    with pytest.raises(Exception):
        with client.websocket_connect(f"/sessions/{session_id}/stream?token=not-a-real-token"):
            pass


def test_websocket_stream_replays_buffer_then_delivers_live_events(client):
    r = client.post("/sessions", json={"track": "bootloader"}, headers=auth(TOKEN_BOOTLOADER))
    session_id = r.json()["session_id"]
    session = registry.get(session_id)

    asyncio.run(registry.emit(session, {
        "type": "assistant_delta", "session_id": session_id, "ts": "t0", "data": {"text": "buffered"},
    }))

    with client.websocket_connect(f"/sessions/{session_id}/stream?token={TOKEN_BOOTLOADER}") as ws:
        replayed = ws.receive_json()
        assert replayed["data"]["text"] == "buffered"

        asyncio.run(registry.emit(session, {
            "type": "assistant_delta", "session_id": session_id, "ts": "t1", "data": {"text": "live"},
        }))
        live = ws.receive_json()
        assert live["data"]["text"] == "live"


def test_disconnect_does_not_tear_down_the_sdk_client_within_grace_period(client, monkeypatch):
    import app.sessions.registry as registry_module
    monkeypatch.setattr(registry_module, "DISCONNECT_GRACE_SECONDS", 60)

    r = client.post("/sessions", json={"track": "bootloader"}, headers=auth(TOKEN_BOOTLOADER))
    session_id = r.json()["session_id"]
    session = registry.get(session_id)

    with client.websocket_connect(f"/sessions/{session_id}/stream?token={TOKEN_BOOTLOADER}"):
        pass  # connect then immediately drop

    for _ in range(50):
        if session.status.value == "disconnected":
            break
        time.sleep(0.02)

    assert session.status.value == "disconnected"
    assert session.client is not None
    assert session.client.connected is True  # never torn down — grace period hasn't elapsed


def test_disconnect_tears_down_after_grace_period_elapses(client, monkeypatch):
    import app.sessions.registry as registry_module
    monkeypatch.setattr(registry_module, "DISCONNECT_GRACE_SECONDS", 0.05)

    r = client.post("/sessions", json={"track": "bootloader"}, headers=auth(TOKEN_BOOTLOADER))
    session_id = r.json()["session_id"]
    session = registry.get(session_id)
    fake_client = session.client

    with client.websocket_connect(f"/sessions/{session_id}/stream?token={TOKEN_BOOTLOADER}"):
        pass

    for _ in range(100):
        if session.status.value == "closed":
            break
        time.sleep(0.02)

    assert session.status.value == "closed"
    assert session.client is None
    assert fake_client.connected is False


def test_reconnect_within_grace_cancels_teardown(client, monkeypatch):
    import app.sessions.registry as registry_module
    monkeypatch.setattr(registry_module, "DISCONNECT_GRACE_SECONDS", 60)

    r = client.post("/sessions", json={"track": "bootloader"}, headers=auth(TOKEN_BOOTLOADER))
    session_id = r.json()["session_id"]
    session = registry.get(session_id)

    with client.websocket_connect(f"/sessions/{session_id}/stream?token={TOKEN_BOOTLOADER}"):
        pass

    for _ in range(50):
        if session.status.value == "disconnected":
            break
        time.sleep(0.02)
    assert session.status.value == "disconnected"

    with client.websocket_connect(f"/sessions/{session_id}/stream?token={TOKEN_BOOTLOADER}"):
        for _ in range(50):
            if session.status.value != "disconnected":
                break
            time.sleep(0.02)
        assert session.status.value in ("idle", "active")

    assert session.client is not None
    assert session.client.connected is True
