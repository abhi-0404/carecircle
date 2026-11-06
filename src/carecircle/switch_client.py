"""A small client for the Switch agent protocol.

Switch publishes the protocol but no client library, so this is ours:
registration, operations, approval cards, and one WebSocket per room.
Reference: https://docs.switchagents.ai/switch-rooms/internals/agent-protocol
"""

from __future__ import annotations

import asyncio
import json
import logging
import random
import uuid
from collections.abc import Awaitable, Callable
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import urlencode

import httpx
import websockets

log = logging.getLogger("carecircle.switch")

_CONNECTION_NS = uuid.UUID("5c1e2a90-6d1f-4c1e-9a52-0c1ac1e00000")


class SwitchError(RuntimeError):
    def __init__(self, what: str, status: int, text: str) -> None:
        super().__init__(f"{what} failed with {status}: {text[:400]}")
        self.status = status
        self.text = text


def _check(r: httpx.Response, what: str) -> Any:
    if r.status_code >= 400:
        raise SwitchError(what, r.status_code, r.text)
    return r.json() if r.content else None


class SwitchAgent:
    """Everything an agent does over HTTP, authenticated with its own API key."""

    def __init__(self, base_url: str, agent_id: str, api_key: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.agent_id = agent_id
        self.api_key = api_key
        self.http = httpx.AsyncClient(
            base_url=self.base_url,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=30,
        )

    async def aclose(self) -> None:
        await self.http.aclose()

    # -- registration ----------------------------------------------------
    @staticmethod
    async def register(
        base_url: str,
        registration_key: str,
        *,
        name: str,
        display_name: str,
        description: str,
        overwrite: bool = False,
    ) -> dict:
        """POST /agents with a registration key. Returns {id, api_key}; the key is shown once."""
        body = {
            "name": name,
            "display_name": display_name,
            "description": description,
            "connector_type": "carecircle",
            "integration_profile": {
                "connection_model": "always_on",
                "message_exchange": True,
                "pre_invocation_mediation": [],
                "post_invocation_mediation": [],
                "event_reporting": [],
            },
            "overwrite": overwrite,
        }
        async with httpx.AsyncClient(base_url=base_url.rstrip("/"), timeout=30) as http:
            r = await http.post(
                "/agents", json=body, headers={"Authorization": f"Bearer {registration_key}"}
            )
            return _check(r, "register")

    # -- operations ------------------------------------------------------
    async def op(self, name: str, args: dict | None = None, connection_id: str | None = None) -> Any:
        headers = {"X-Switch-Connection-Id": connection_id} if connection_id else {}
        r = await self.http.post(
            f"/agents/{self.agent_id}/ops/{name}", json=args or {}, headers=headers
        )
        data = _check(r, name)
        return data.get("result") if isinstance(data, dict) else data

    async def send(self, room_id: str, content: str) -> None:
        """Post into a room. Needs no connection."""
        r = await self.http.post(
            f"/agents/{self.agent_id}/message", json={"room_id": room_id, "content": content}
        )
        _check(r, "message")

    # -- approval cards ----------------------------------------------------
    async def open_approval(
        self,
        *,
        session_id: str,
        request_id: str,
        title: str,
        detail: str | None,
        options: list[dict],
        room_id: str,
        thread_id: str | None = None,
        expires_in: timedelta = timedelta(hours=23),
    ) -> dict:
        """Ask the room a yes/no question. Switch draws it as a card with buttons."""
        expires_at = datetime.now(timezone.utc) + expires_in
        body = {
            "request_id": request_id,
            "turn_id": request_id,
            "kind": "approval",
            "title": title,
            "detail": detail,
            "options": options,
            "questions": [],
            "room_id": room_id,
            "thread_id": thread_id,
            "expires_at": expires_at.isoformat(),
        }
        r = await self.http.post(f"/agent-sessions/{session_id}/approvals", json=body)
        return _check(r, "open approval")

    async def close_approval(self, session_id: str, request_id: str) -> None:
        """Withdraw a card nobody needs to answer any more."""
        r = await self.http.post(f"/agent-sessions/{session_id}/approvals/{request_id}/close")
        _check(r, "close approval")

    async def approval_outcomes(self) -> list[dict]:
        """Answers and expiries not yet acknowledged, oldest first."""
        r = await self.http.get("/agent-sessions/approvals/outcomes")
        return _check(r, "approval outcomes") or []

    async def mark_delivered(self, session_id: str, request_id: str) -> None:
        r = await self.http.post(
            f"/agent-sessions/{session_id}/approvals/{request_id}/delivered"
        )
        _check(r, "mark delivered")


MessageHandler = Callable[[str, dict], Awaitable[None]]


class RoomStream:
    """One WebSocket that claims one room and hands over messages that address us.

    Pings are answered on the read loop itself; handling runs on a separate
    worker so a slow reply can never make the connection lapse (6 s).
    """

    def __init__(
        self,
        agent: SwitchAgent,
        room_id: str,
        on_message: MessageHandler,
        *,
        start_from: int | None = None,
        on_cursor: Callable[[int], None] | None = None,
    ) -> None:
        self.agent = agent
        self.room_id = room_id
        self.on_message = on_message
        self.on_cursor = on_cursor
        self.cursor = start_from or 0
        self.generation: int | None = None
        # Stable per agent and room, so a restart takes back our own connection.
        self.connection_id = str(uuid.uuid5(_CONNECTION_NS, f"{agent.agent_id}:{room_id}"))
        self.connected = asyncio.Event()
        self._queue: asyncio.Queue[dict] = asyncio.Queue()
        self._stopped = False

    def _url(self) -> str:
        ws_base = self.agent.base_url.replace("https://", "wss://", 1).replace(
            "http://", "ws://", 1
        )
        params = {
            "connection_id": self.connection_id,
            "scope": "single",
            "filter": "addressed",
            # Resume after our cursor; 0 on a first connect replays what was
            # buffered for us before we connected, so nothing addressed is lost.
            "start_from": str(self.cursor),
            "rooms": self.room_id,
            "client": "carecircle",
            "client_version": "0.1.0",
        }
        if self.generation is not None:
            params["expected_generation"] = str(self.generation)
        return f"{ws_base}/agents/{self.agent.agent_id}/connection/ws?{urlencode(params)}"

    async def run(self) -> None:
        worker = asyncio.create_task(self._work())
        backoff = 1.0
        try:
            while not self._stopped:
                try:
                    async with websockets.connect(
                        self._url(),
                        additional_headers={"Authorization": f"Bearer {self.agent.api_key}"},
                        open_timeout=30,
                        max_size=None,
                        ping_interval=None,  # Switch's own ping frames are the heartbeat
                    ) as ws:
                        backoff = 1.0
                        await self._read(ws)
                except asyncio.CancelledError:
                    raise
                except Exception as exc:  # noqa: BLE001 - every ending is logged and retried
                    log.warning("room %s: connection ended (%s)", self.room_id, exc)
                self.connected.clear()
                if self._stopped:
                    break
                await asyncio.sleep(backoff * (0.5 + random.random()))
                backoff = min(backoff * 2, 30)
        finally:
            worker.cancel()

    async def _read(self, ws) -> None:
        async for raw in ws:
            frame = json.loads(raw)
            event = frame.get("event")
            data = frame.get("data") or {}
            if event == "ping":
                await ws.send(json.dumps({"type": "pong", "cursor": self.cursor}))
                continue
            if event == "connection_state":
                self.generation = data.get("generation", self.generation)
                self.connected.set()
                log.info("room %s: connected", self.room_id)
                continue
            if event in ("refused", "evicted"):
                detail = data.get("detail") if isinstance(data.get("detail"), dict) else data
                code = (detail or {}).get("code")
                log.warning("room %s: %s %s", self.room_id, event, data)
                if code == "taken_over":
                    self._stopped = True  # another copy of us owns the room now
                return
            if event == "gap":
                log.warning("room %s: gap in the event stream %s", self.room_id, data)
                continue
            seq = frame.get("id", data.get("sequence"))
            if isinstance(seq, int) and seq > self.cursor:
                self.cursor = seq
            if event == "message":
                payload = data.get("payload") or {}
                if payload.get("addressed"):
                    await self._queue.put(payload)
                elif self.on_cursor:
                    self.on_cursor(self.cursor)

    async def _work(self) -> None:
        while True:
            payload = await self._queue.get()
            try:
                await self.on_message(self.room_id, payload)
            except Exception:  # noqa: BLE001 - one bad message must not stop the room
                log.exception("room %s: handling a message failed", self.room_id)
            if self.on_cursor:
                self.on_cursor(self.cursor)

    def stop(self) -> None:
        self._stopped = True
