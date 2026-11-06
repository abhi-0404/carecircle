"""`uv run carecircle demo`: the whole CareCircle story, offline, in 2 seconds.

No Switch server, no Discord, no API key. The real @ledger and @pillbox code
runs against an in-memory stand-in for Switch, people's taps are scripted, and
@meds' reading of the sample prescription is replayed from
demo/samples/prescription-cardiology.transcript.json. Everything printed is
what the agents actually produce.
"""

from __future__ import annotations

import asyncio
import json
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

from carecircle.circle import Circle
from carecircle.ledger_agent import LedgerAgent
from carecircle.pillbox_agent import PillboxAgent

FAMILY, MA = "sharma-circle", "sharma-ma"
PEOPLE = {
    "@switch-discord-priya:demo": "Priya",
    "@switch-discord-rahul:demo": "Rahul",
    "@switch-discord-ankit:demo": "Ankit",
    "@switch-discord-vikram:demo": "Cousin Vikram",
}
CIRCLE = Circle.from_dict(
    {
        "parent": "Ma",
        "members": {"priya": ["Priya"], "rahul": ["Rahul"], "ankit": ["Ankit"]},
        "approval": {"people_only": True, "not_own_entry": True},
        "reminders": {"timeout_minutes": 30},
    }
)
SAMPLE = Path(__file__).resolve().parents[2] / "demo" / "samples" / "prescription-cardiology.transcript.json"


class Clock:
    def __init__(self, t: datetime):
        self.t = t

    def __call__(self) -> datetime:
        return self.t


class StandIn:
    """Just enough of Switch: rooms print, cards print, taps are scripted."""

    def __init__(self, name: str, out):
        self.name, self.out = name, out
        self.cards: list[dict] = []
        self.answers: list[dict] = []

    async def op(self, name, args=None, connection_id=None):
        if name == "list_linked_rooms":
            return [{"room_id": MA, "label": "parent's room"}]
        if name == "list_participants":
            return [{"id": k, "name": v} for k, v in PEOPLE.items()]
        if name == "create_room_document":
            self.out(f"   📄 room document “{args['name']}” created by @{self.name}")
            return {"id": f"doc-{args['name']}"}
        if name == "update_room_document":
            self.out(f"   📄 room document updated by @{self.name}")
        return {}

    async def send(self, room_id, content):
        self.out(f"[#{room_id}] @{self.name}: " + content.replace("\n", "\n" + " " * 8))

    async def open_approval(self, **kw):
        self.cards.append(kw)
        buttons = "  ".join(f"[ {o['label']} ]" for o in kw["options"])
        self.out(f"[#{kw['room_id']}] 🃏 card from @{self.name}: {kw['title']}")
        for line in (kw.get("detail") or "").splitlines():
            self.out(f"        │ {line}")
        self.out(f"        {buttons}")
        return {}

    async def close_approval(self, session_id, request_id):
        self.out(f"   (card withdrawn by @{self.name}: nobody answered in time)")

    async def approval_outcomes(self):
        out, self.answers = self.answers, []
        return out

    async def mark_delivered(self, session_id, request_id):
        pass

    def tap(self, option: str, who: str, card: dict | None = None):
        card = card or self.cards[-1]
        label = next(o["label"] for o in card["options"] if o["id"] == option)
        self.out(f"   👆 {PEOPLE[who]} taps [ {label} ]")
        self.answers.append({"sessionId": card["session_id"], "requestId": card["request_id"],
                             "state": "answered", "answer": option, "answeredBy": who})


def _msg(who: str, body: str) -> dict:
    return {"addressed": True, "sender_name": PEOPLE.get(who, who), "sender": who, "body": body}


async def story(out) -> None:
    clock = Clock(datetime(2026, 11, 9, 7, 40))
    data = Path(tempfile.mkdtemp(prefix="carecircle-demo-"))
    ls, ps = StandIn("ledger", out), StandIn("pillbox", out)
    ledger, pillbox = LedgerAgent(ls, CIRCLE, data), PillboxAgent(ps, CIRCLE, data, now=clock)

    def scene(title: str) -> None:
        out("")
        out(f"── {title} " + "─" * max(0, 60 - len(title)))

    async def says(agent, room, who, body):
        out(f"[#{room}] {PEOPLE.get(who, '@' + who)}: {body.splitlines()[0]}" + (" …" if "\n" in body else ""))
        await agent.handle_message(room, _msg(who, body))

    scene("1. Ankit paid for Ma's lab tests")
    await says(ledger, FAMILY, "@switch-discord-ankit:demo", "@ledger add 2400 lab tests")
    ls.tap("approve", "@switch-discord-ankit:demo")
    await ledger.check_outcomes()
    ls.tap("approve", "@switch-discord-rahul:demo")
    await ledger.check_outcomes()

    scene("2. A new prescription: @meds reads it, @pillbox checks it")
    transcript = json.loads(SAMPLE.read_text(encoding="utf-8"))
    body = "@pillbox new prescription for Ma, transcribed by @meds:\n```json\n" + json.dumps(transcript) + "\n```"
    out("[#sharma-circle] Priya: (photo of the prescription) @meds please read this")
    out("[#sharma-circle] @meds: I've copied the prescription; @pillbox is checking it - please review its card.")
    await pillbox.handle_message(FAMILY, {"addressed": True, "sender_name": "meds", "sender": "@meds:demo", "body": body})
    ps.tap("approve", "@switch-discord-vikram:demo")
    await pillbox.check_outcomes()
    ps.tap("approve", "@switch-discord-priya:demo")
    await pillbox.check_outcomes()

    scene("3. @coordinator settles who takes Ma to the cardiologist")
    out("[#sharma-circle] 🃏 card from @coordinator: Who will take Ma to cardiology, Fri 13 Nov 10:00?")
    out("        [ Priya ]  [ Rahul ]  [ Ankit ]  [ Nobody can - need help ]")
    out("   👆 Rahul taps [ Rahul ]")
    await pillbox.handle_message(FAMILY, {"addressed": True, "sender_name": "coordinator", "sender": "@coordinator:demo",
                                          "body": "@pillbox visit 2026-11-13 10:00 | Cardiology check-up, Dr. Kapoor | Rahul"})

    scene("4. 8:05 AM: Ma's morning reminder")
    clock.t = datetime(2026, 11, 9, 8, 5)
    await pillbox.tick()
    out("   (nobody answers…)")
    clock.t += timedelta(minutes=31)
    await pillbox.tick()
    ps.tap("calling", "@switch-discord-rahul:demo")
    await pillbox.check_outcomes()

    scene("5. Ankit settles up")
    await says(ledger, FAMILY, "@switch-discord-ankit:demo", "@ledger settle")
    out("")
    out("Every card above is a native Switch approval card; on Discord they are buttons.")


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    asyncio.run(story(print))


if __name__ == "__main__":
    main()
