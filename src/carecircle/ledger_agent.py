"""@ledger: the family's expense keeper, as a Switch agent with no model in it.

Siblings (or other agents) address it in a room. Every new entry becomes an
approval card in that room; only a tap on Approve records it. Balances,
splits and settle-up are plain Python over whole paise.

    uv run carecircle-ledger register   # once: registers @ledger, saves its key to .env
    uv run carecircle-ledger run        # keep it running while the family uses the room
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Protocol

from carecircle.circle import Circle, chat_name
from carecircle.commands import HELP, AddExpense, AddPayment, CommandError, Query, parse
from carecircle.env import load_env, require, set_env_values
from carecircle.ledger import Expense, Ledger, LedgerError, Payment
from carecircle.money import format_rupees

log = logging.getLogger("carecircle.ledger")

SESSION_PREFIX = "ledger-"
APPROVE, REJECT = "approve", "reject"
DOC_NAME = "expense-ledger"


class Switch(Protocol):
    """What @ledger needs from Switch (SwitchAgent in production, a fake in tests)."""

    async def op(self, name: str, args: dict | None = None, connection_id: str | None = None) -> Any: ...
    async def send(self, room_id: str, content: str) -> None: ...
    async def open_approval(self, **kw: Any) -> dict: ...
    async def approval_outcomes(self) -> list[dict]: ...
    async def mark_delivered(self, session_id: str, request_id: str) -> None: ...


@dataclass
class RoomState:
    """Everything @ledger keeps for one room, saved as one file so it changes atomically."""

    room_id: str
    path: Path
    ledger: Ledger
    pending: dict[str, dict] = field(default_factory=dict)  # request_id -> proposal
    doc_id: str | None = None
    cursor: int = 0

    @classmethod
    def load(cls, room_id: str, data_dir: Path, members: list[str]) -> "RoomState":
        path = data_dir / f"room-{_safe(room_id)}.json"
        if path.exists():
            d = json.loads(path.read_text(encoding="utf-8"))
            return cls(
                room_id=room_id,
                path=path,
                ledger=Ledger.from_json(json.dumps(d["ledger"])),
                pending=d.get("pending", {}),
                doc_id=d.get("doc_id"),
                cursor=d.get("cursor", 0),
            )
        return cls(room_id=room_id, path=path, ledger=Ledger(members))

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(
            json.dumps(
                {
                    "room_id": self.room_id,
                    "ledger": json.loads(self.ledger.to_json()),
                    "pending": self.pending,
                    "doc_id": self.doc_id,
                    "cursor": self.cursor,
                },
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        tmp.replace(self.path)


def _safe(room_id: str) -> str:
    return "".join(c if c.isalnum() or c in "-_" else "_" for c in room_id)


def _proposal_to_dict(item: Expense | Payment) -> dict:
    return {"type": "expense" if isinstance(item, Expense) else "payment", **asdict(item)}


def _proposal_from_dict(d: dict) -> Expense | Payment:
    d = dict(d)
    kind = d.pop("type")
    return Expense(**d) if kind == "expense" else Payment(**d)


class LedgerAgent:
    def __init__(self, switch: Switch, circle: Circle, data_dir: Path) -> None:
        self.switch = switch
        self.circle = circle
        self.data_dir = data_dir
        self.rooms: dict[str, RoomState] = {}
        self.connections: dict[str, str] = {}  # room_id -> connection id, for room-bound ops
        self._names: dict[str, dict[str, str]] = {}  # room_id -> participant id -> name

    def room(self, room_id: str) -> RoomState:
        if room_id not in self.rooms:
            self.rooms[room_id] = RoomState.load(room_id, self.data_dir, self.circle.names)
        return self.rooms[room_id]

    async def say(self, room_id: str, text: str) -> None:
        await self.switch.send(room_id, text)

    # -- incoming messages -------------------------------------------------
    async def handle_message(self, room_id: str, payload: dict) -> None:
        body = payload.get("body") or ""
        sender_name = payload.get("sender_name") or ""
        sender = payload.get("sender") or ""
        room = self.room(room_id)
        try:
            cmd = parse(body)
        except CommandError as exc:
            await self.say(room_id, f"🤔 {exc}")
            return
        if isinstance(cmd, Query):
            await self.say(room_id, self.answer_query(room, cmd.what))
            return
        try:
            if isinstance(cmd, AddExpense):
                payer = cmd.paid_by or self.circle.identify(sender_name, sender)
                if payer is None:
                    await self.say(
                        room_id,
                        f"🤔 I don't know which of {self._names_list()} you are, "
                        f"{sender_name or 'friend'}. Add `paid by <name>`.",
                    )
                    return
                proposal: Expense | Payment = room.ledger.propose_expense(
                    cmd.amount, cmd.description, payer, cmd.shares
                )
            else:
                assert isinstance(cmd, AddPayment)
                proposal = room.ledger.propose_payment(cmd.frm, cmd.to, cmd.amount)
        except LedgerError as exc:
            await self.say(room_id, f"🤔 {exc}")
            return
        await self.ask_approval(room, proposal, asked_by=sender_name)

    def answer_query(self, room: RoomState, what: str) -> str:
        led = room.ledger
        if what == "help":
            return HELP
        if what == "history":
            items = sorted(led.expenses + led.payments, key=lambda x: x.id)[-10:]
            if not items:
                return "📒 Nothing recorded yet."
            lines = []
            for x in items:
                if isinstance(x, Expense):
                    lines.append(f"#{x.id} {led.describe(x)}")
                else:
                    lines.append(
                        f"#{x.id} {x.frm.title()} paid {x.to.title()} {format_rupees(x.amount)}"
                    )
            return "📒 **Last entries**\n" + "\n".join(lines)
        transfers = led.settle_up()
        if what == "settle":
            if not transfers:
                return "✅ Everyone is square. Nothing to settle."
            plan = "\n".join(f"• {t}" for t in transfers)
            return (
                f"💸 **To settle up** ({len(transfers)} transfer"
                f"{'s' if len(transfers) != 1 else ''}):\n{plan}\n"
                "When money moves, tell me: `paid 800 from rahul to ankit`."
            )
        return self.balance_text(room)

    def balance_text(self, room: RoomState) -> str:
        parts = []
        for m, v in room.ledger.balances().items():
            if v > 0:
                parts.append(f"{m.title()} is owed {format_rupees(v)}")
            elif v < 0:
                parts.append(f"{m.title()} owes {format_rupees(-v)}")
            else:
                parts.append(f"{m.title()} is square")
        return "⚖️ " + " · ".join(parts)

    def _names_list(self) -> str:
        names = [n.title() for n in self.circle.names]
        return ", ".join(names[:-1]) + f" or {names[-1]}" if len(names) > 1 else names[0]

    # -- approvals -----------------------------------------------------------
    def card_text(self, room: RoomState, item: Expense | Payment) -> tuple[str, str]:
        if isinstance(item, Expense):
            split = " · ".join(f"{m.title()} {format_rupees(v)}" for m, v in item.owed().items())
            title = f"Record {format_rupees(item.amount)} for {item.description}?"
            detail = (
                f"Paid by {item.paid_by.title()}. Split: {split}.\n"
                "Nothing goes into the family ledger until a sibling approves."
            )
        else:
            title = (
                f"Record that {item.frm.title()} paid {item.to.title()} "
                f"{format_rupees(item.amount)}?"
            )
            detail = "A settle-up payment. Approve only once the money has really moved."
        return title, detail

    async def ask_approval(self, room: RoomState, item: Expense | Payment, asked_by: str) -> None:
        request_id = uuid.uuid4().hex
        title, detail = self.card_text(room, item)
        await self.switch.open_approval(
            session_id=SESSION_PREFIX + room.room_id,
            request_id=request_id,
            title=title,
            detail=detail,
            options=[
                {"id": APPROVE, "label": "Approve", "decision": "accept"},
                {"id": REJECT, "label": "Reject", "decision": "decline"},
            ],
            room_id=room.room_id,
        )
        room.pending[request_id] = {"item": _proposal_to_dict(item), "asked_by": asked_by}
        room.save()

    async def check_outcomes(self) -> int:
        """Act on every answered or expired card. Returns how many were handled."""
        handled = 0
        for o in await self.switch.approval_outcomes():
            session_id = o.get("sessionId") or o.get("session_id") or ""
            request_id = o.get("requestId") or o.get("request_id") or ""
            if session_id.startswith(SESSION_PREFIX):
                room = self.room(session_id[len(SESSION_PREFIX):])
                entry = room.pending.pop(request_id, None)
                if entry is not None:
                    await self._settle_request(room, entry, o)
                    handled += 1
            await self.switch.mark_delivered(session_id, request_id)
        return handled

    async def _settle_request(self, room: RoomState, entry: dict, outcome: dict) -> None:
        item = _proposal_from_dict(entry["item"])
        label = (
            f"{format_rupees(item.amount)} for {item.description}"
            if isinstance(item, Expense)
            else f"{item.frm.title()} → {item.to.title()} {format_rupees(item.amount)}"
        )
        state = outcome.get("state")
        answer = outcome.get("answer")
        participant = outcome.get("answeredBy") or outcome.get("answered_by")
        who = await self.name_of(room.room_id, participant)
        if state == "answered":
            member = await self.member_of(room.room_id, participant)
            problem = self.approval_problem(item, member, approving=answer == APPROVE)
            if problem:
                room.save()  # this card is spent; a fresh one replaces it
                await self.say(
                    room.room_id, f"⚠️ {who} can't decide this one: {problem} I've put up a fresh card."
                )
                await self.ask_approval(room, item, asked_by=entry.get("asked_by", ""))
                return
        if state == "answered" and answer == APPROVE:
            recorded = room.ledger.record(item, approved_by=who)
            room.save()  # the pending entry is gone and the record is in, in one write
            await self.sync_document(room)
            await self.say(
                room.room_id,
                f"✅ Recorded #{recorded.id}: {label} — approved by {who}.\n{self.balance_text(room)}",
            )
        elif state == "answered":
            room.save()
            await self.say(room.room_id, f"❌ Not recorded: {label} — declined by {who}.")
        else:
            room.save()
            await self.say(room.room_id, f"⌛ The card for {label} was {state}; nothing was recorded.")

    def approval_problem(
        self, item: Expense | Payment, member: str | None, *, approving: bool
    ) -> str | None:
        """Why this person's answer can't count, or None. Plain rules, no model."""
        if self.circle.people_only and member is None:
            return "only someone in the family circle can approve or reject entries."
        if not (approving and self.circle.not_own_entry):
            return None
        if isinstance(item, Expense) and member == item.paid_by:
            return "nobody approves their own expense — another sibling has to confirm it."
        if isinstance(item, Payment) and member != item.to:
            return f"only {item.to.title()}, who received the money, can confirm it."
        return None

    async def member_of(self, room_id: str, participant: str | None) -> str | None:
        """The circle member who answered, or None if they aren't one."""
        if not participant:
            return None
        keys = [participant, participant.removeprefix("user:")]
        names = self._names.get(room_id) or await self._load_names(room_id)
        name = next((names[k] for k in keys if k in names), None)
        return self.circle.identify(name, participant)

    async def name_of(self, room_id: str, participant: str | None) -> str:
        if not participant:
            return "someone"
        # Answers carry "user:<id>" (Switch Console) or a chat participant id
        # ("@switch-user-…:server"); list_participants keys people by plain id.
        keys = [participant, participant.removeprefix("user:")]
        names = self._names.get(room_id)
        if names is None or not any(k in names for k in keys):
            names = await self._load_names(room_id)
        name = next((names[k] for k in keys if k in names), None)
        if name is None and participant.startswith("@"):
            name = chat_name(participant)
        member = self.circle.identify(name, participant)
        if member:
            return member.title()
        if name:
            return name
        return "the owner in Switch Console" if participant.startswith("user:") else "someone"

    async def _load_names(self, room_id: str) -> dict[str, str]:
        names: dict[str, str] = {}
        try:
            result = await self.switch.op(
                "list_participants", {}, connection_id=self.connections.get(room_id)
            )
        except Exception as exc:  # noqa: BLE001 - a name is a nicety
            log.warning("could not list participants of %s: %s", room_id, exc)
            result = None
        for p in _dicts(result):
            pid = next((p[k] for k in ("id", "user_id", "participant_id", "mxid") if p.get(k)), None)
            name = next(
                (p[k] for k in ("display_name", "name", "username") if p.get(k)), None
            )
            if pid and name:
                names[str(pid)] = str(name)
        self._names[room_id] = names
        return names

    # -- the room document -------------------------------------------------
    async def sync_document(self, room: RoomState) -> None:
        """Keep the `expense-ledger` room document equal to the ledger. Only @ledger edits it."""
        content = room.ledger.render_markdown()
        conn = self.connections.get(room.room_id)
        try:
            if room.doc_id:
                await self.switch.op(
                    "update_room_document",
                    {"document_id": room.doc_id, "content": content},
                    connection_id=conn,
                )
            else:
                result = await self.switch.op(
                    "create_room_document",
                    {
                        "name": DOC_NAME,
                        "description": "The family's shared expenses: balances, settle-up and history.",
                        "instructions": (
                            "Kept by @ledger from approved entries only; every amount is "
                            "computed by code. To change anything, ask @ledger."
                        ),
                        "content": content,
                    },
                    connection_id=conn,
                )
                room.doc_id = _find_id(result)
                room.save()
        except Exception as exc:  # noqa: BLE001 - the ledger itself is already saved
            log.warning("could not update the %s document in %s: %s", DOC_NAME, room.room_id, exc)


def _dicts(result: Any) -> list[dict]:
    """The list of dicts inside an op result, whatever key it sits under."""
    if isinstance(result, list):
        return [x for x in result if isinstance(x, dict)]
    if isinstance(result, dict):
        for v in result.values():
            if isinstance(v, list) and all(isinstance(x, dict) for x in v):
                return v
    return []


def _find_id(result: Any) -> str | None:
    if isinstance(result, dict):
        for k in ("document_id", "id"):
            if isinstance(result.get(k), str):
                return result[k]
        for v in result.values():
            found = _find_id(v)
            if found:
                return found
    return None


def _room_ids(result: Any) -> list[str]:
    ids = []
    for r in _dicts(result):
        rid = r.get("room_id") or r.get("id")
        if isinstance(rid, str) and not r.get("archived"):
            ids.append(rid)
    return ids


# -- running it ---------------------------------------------------------------

async def _serve(agent: LedgerAgent, switch) -> None:
    from carecircle.switch_client import RoomStream

    streams: dict[str, asyncio.Task] = {}

    async def discover() -> None:
        while True:
            try:
                for rid in _room_ids(await switch.op("list_rooms")):
                    if rid in streams:
                        continue
                    state = agent.room(rid)

                    def remember(cursor: int, state: RoomState = state) -> None:
                        if cursor > state.cursor:
                            state.cursor = cursor
                            state.save()

                    stream = RoomStream(
                        switch, rid, agent.handle_message, start_from=state.cursor, on_cursor=remember
                    )
                    agent.connections[rid] = stream.connection_id
                    streams[rid] = asyncio.create_task(stream.run())
                    log.info("listening in room %s", rid)
            except Exception as exc:  # noqa: BLE001
                log.warning("could not list rooms: %s", exc)
            await asyncio.sleep(15)

    async def outcomes() -> None:
        while True:
            try:
                await agent.check_outcomes()
            except Exception as exc:  # noqa: BLE001
                log.warning("could not read card outcomes: %s", exc)
            await asyncio.sleep(2)

    await asyncio.gather(discover(), outcomes())


async def _register(args) -> None:
    from carecircle.switch_client import SwitchAgent

    base = os.environ.get("SWITCH_URL", "http://127.0.0.1:55618")
    resp = await SwitchAgent.register(
        base,
        require("SWITCH_REGISTRATION_KEY"),
        name=args.name,
        display_name="Ledger",
        description="Keeps the family's shared expenses. No AI: every amount is computed by code, "
        "and nothing is recorded until a sibling approves the card.",
        overwrite=args.overwrite,
    )
    set_env_values(Path(".env"), {"LEDGER_AGENT_ID": resp["id"], "LEDGER_API_KEY": resp["api_key"]})
    # An agent may not change its own permissions (Switch answers 403), so who
    # may address @ledger is set by its owner in Switch Console.
    print(f"Registered @{args.name} (id {resp['id']}). Its key is saved in .env.")
    print("Next, in Switch Console: Your Agents > ledger > let your family address it,")
    print("invite it into the family room, then run:  uv run carecircle-ledger run")


async def _run() -> None:
    from carecircle.switch_client import SwitchAgent

    base = os.environ.get("SWITCH_URL", "http://127.0.0.1:55618")
    switch = SwitchAgent(base, require("LEDGER_AGENT_ID"), require("LEDGER_API_KEY"))
    circle = Circle.load(Path(os.environ.get("CARECIRCLE_CONFIG", "circle.json")))
    agent = LedgerAgent(switch, circle, Path(os.environ.get("CARECIRCLE_DATA", "data")))
    log.info("@ledger is running against %s for %s", base, ", ".join(circle.names))
    try:
        await _serve(agent, switch)
    finally:
        await switch.aclose()


def main(argv: list[str] | None = None) -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    load_env()
    p = argparse.ArgumentParser(prog="carecircle-ledger")
    sub = p.add_subparsers(dest="cmd", required=True)
    reg = sub.add_parser("register", help="register @ledger with the Switch server (once)")
    reg.add_argument("--name", default="ledger")
    reg.add_argument("--overwrite", action="store_true", help="re-issue the key if it exists")
    sub.add_parser("run", help="run @ledger")
    args = p.parse_args(argv)
    try:
        asyncio.run(_register(args) if args.cmd == "register" else _run())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
