"""A fake ClaudeSDKClient for exercising the HTTP/WebSocket plumbing without ever
calling the real Claude API — no cost, no credentials, no real agent loop. Only the
async surface app/api/* actually calls is implemented: connect/disconnect/query/
receive_response/interrupt."""

from __future__ import annotations

from typing import Any


class FakeClaudeSDKClient:
    def __init__(self, options: Any = None):
        self.options = options
        self.connected = False
        self.queries: list[str] = []
        self.interrupt_count = 0
        self._queued_messages: list[Any] = []

    def queue_response(self, messages: list[Any]) -> None:
        """Set what the next receive_response() call yields."""
        self._queued_messages = messages

    async def connect(self, prompt: str | None = None) -> None:
        self.connected = True

    async def disconnect(self) -> None:
        self.connected = False

    async def query(self, prompt: str, session_id: str = "default") -> None:
        self.queries.append(prompt)

    async def receive_response(self):
        messages, self._queued_messages = self._queued_messages, []
        for message in messages:
            yield message

    async def interrupt(self) -> None:
        self.interrupt_count += 1
