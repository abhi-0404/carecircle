"""@pillbox: keeps the parent's medicine list and reminds them. No model in it.

How a prescription reaches the list:

1. A sibling posts a photo and asks @meds (a Claude Code agent) to read it.
2. @meds copies every line verbatim and hands @pillbox a transcript: a
   ```json block with {"lines": [{verbatim, name, strength, dose, ...}]}.
3. @pillbox checks every line in code (carecircle.meds): anything that can't be
   traced to its own line is kept out. The result goes on an approval card.
4. Only when a sibling taps Approve does it update the `medicine-list`
   document and post the new plan in the parent's room.

Every day, at each dose time, it asks in the parent's room "Taken?" on a card.
If nobody answers in time, it tells the family room and asks who will call.
Switch has no scheduler, so this clock lives here.
"""

from __future__ import annotations

import json
import logging
import re
import uuid
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from carecircle.circle import Circle, chat_name
from carecircle.commands import strip_mentions
from carecircle.meds import (
    SLOT_ICON,
    SLOT_TIME,
    SLOTS,
    Med,
    card_text,
    check_prescription,
    schedule_markdown,
)

log = logging.getLogger("carecircle.pillbox")

SESSION_PREFIX = "pillbox-"
APPROVE, REJECT = "approve", "reject"
TAKEN, LATER = "taken", "later"
CALLING = "calling"
DOC_NAME = "medicine-list"
SLOT_HOUR = {"morning": (8, 0), "afternoon": (14, 0), "evening": (18, 0), "night": (21, 0)}
WINDOW = timedelta(minutes=30)  # a reminder is sent only within 30 min after its time
MAX_DETAIL = 3900

_JSON_BLOCK = re.compile(r"```(?:json)?\s*(\{.*\})\s*```", re.S)
_VISIT = re.compile(
    r"^visit\s+(\d{4}-\d{2}-\d{2})\s+(\d{1,2}:\d{2})\s*\|\s*([^|]+?)\s*(?:\|\s*([^|]+?)\s*)?$",
    re.IGNORECASE,
)
VISIT_EVE_HOUR = 19  # remind the evening before, at 7 PM
VISIT_LEAD = timedelta(hours=2)  # and two hours before


def parse_visit(text: str) -> tuple[datetime, str, str | None]:
    """'visit 2026-11-13 10:00 | Cardiology, Dr. Kapoor | Rahul' -> (when, what, who)."""
    m = _VISIT.match(text.strip())
    if not m:
        raise ValueError("Say it like: visit 2026-11-13 10:00 | what and where | who is going")
    when = datetime.fromisoformat(f"{m.group(1)} {int(m.group(2).split(':')[0]):02d}:{m.group(2).split(':')[1]}")
    return when, m.group(3).strip(), (m.group(4) or "").strip() or None


def _when(dt: datetime) -> str:
    return dt.strftime("%A %d %b, %I:%M %p").replace(" 0", " ")

HELP = """**@pillbox** — I keep {parent}'s medicine list and remind {parent} at dose times. No AI in me.
• Send a prescription photo to **@meds**; it reads it and hands it to me. I check every line, and a sibling approves before anything changes.
• `today` — today's doses · `list` — the current list
• `stop Amlodipine` — take a medicine off the list (a sibling approves)
• `visit 2026-11-13 10:00 | Cardiology, Dr. Kapoor | Rahul` — I tell {parent} and remind them (or ask @coordinator)
• `visits` — upcoming visits · `remind now` — send the next reminder right away"""


def _med_from(d: dict) -> Med:
    from carecircle.meds import normalize_form

    d = {k: v for k, v in d.items() if k in Med.__dataclass_fields__}
    d["form"] = normalize_form(d.get("form"), d.get("verbatim", ""))
    return Med(**d)


@dataclass
class PillboxState:
    """One family's medicine list and open cards, saved as one file."""

    room_id: str
    path: Path
    meds: list[dict] = field(default_factory=list)  # Med fields + "added_on", "approved_by"
    pending: dict[str, dict] = field(default_factory=dict)  # request_id -> what it decides
    doc_id: str | None = None
    parent_room: str | None = None
    reminded: dict[str, str] = field(default_factory=dict)  # "2026-11-06/morning" -> state
    visits: list[dict] = field(default_factory=list)  # {"at", "what", "who", "told": [...]}
    cursor: int = 0

    @classmethod
    def load(cls, room_id: str, data_dir: Path) -> "PillboxState":
        safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in room_id)
        path = data_dir / f"pillbox-{safe}.json"
        if path.exists():
            d = json.loads(path.read_text(encoding="utf-8"))
            d.pop("room_id", None)
            return cls(room_id=room_id, path=path, **d)
        return cls(room_id=room_id, path=path)

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        d = asdict(self)
        d.pop("path")
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(d, indent=2, ensure_ascii=False), encoding="utf-8")
        tmp.replace(self.path)

    def active_meds(self, today: date) -> list[Med]:
        out = []
        for d in self.meds:
            m = _med_from(d)
            start = date.fromisoformat(d.get("added_on", today.isoformat()))
            if m.duration_days and today > start + timedelta(days=m.duration_days):
                continue  # course finished
            out.append(m)
        return out


class PillboxAgent:
    def __init__(self, switch, circle: Circle, data_dir: Path, *, now=datetime.now) -> None:
        self.switch = switch
        self.circle = circle
        self.data_dir = data_dir
        self.now = now
        self.rooms: dict[str, PillboxState] = {}
        self.connections: dict[str, str] = {}
        self._names: dict[str, dict[str, str]] = {}
        self._parent_of: dict[str, str] = {}  # parent room -> family room

    # -- state -------------------------------------------------------------
    def room(self, room_id: str) -> PillboxState:
        if room_id not in self.rooms:
            self.rooms[room_id] = PillboxState.load(room_id, self.data_dir)
            pr = self.rooms[room_id].parent_room
            if pr:
                self._parent_of[pr] = room_id
        return self.rooms[room_id]

    def family_of(self, room_id: str) -> PillboxState:
        """Messages in the parent's room act on the family that owns it."""
        return self.room(self._parent_of.get(room_id, room_id))

    def cursor_of(self, room_id: str) -> int:
        return self.room(room_id).cursor

    def remember_cursor(self, room_id: str, cursor: int) -> None:
        st = self.room(room_id)
        if cursor > st.cursor:
            st.cursor = cursor
            st.save()

    async def say(self, room_id: str, text: str) -> None:
        await self.switch.send(room_id, text)

    # -- incoming ------------------------------------------------------------
    async def handle_message(self, room_id: str, payload: dict) -> None:
        body = payload.get("body") or ""
        sender_name = (payload.get("sender_name") or "").strip()
        sender = payload.get("sender") or ""
        st = self.family_of(room_id)
        block = _JSON_BLOCK.search(body)
        if block:
            await self._intake(room_id, st, block.group(1), sender_name, sender)
            return
        text = strip_mentions(body).lower()
        word = text.split(maxsplit=1)[0].strip(",.!") if text else "help"
        if word in {"today", "schedule"}:
            await self.say(room_id, self.today_text(st))
        elif word in {"list", "medicines", "meds"}:
            await self.say(room_id, self.list_text(st))
        elif word == "stop":
            await self._ask_stop(room_id, st, text.split(maxsplit=1)[1] if " " in text else "")
        elif word == "remind":
            slot = next((s for s in SLOTS if s in text), None)
            await self.send_reminder(st, slot, forced=True)
        elif word == "visit":
            await self._add_visit(room_id, st, strip_mentions(body), sender_name, sender)
        elif word == "visits":
            await self.say(room_id, self.visits_text(st))
        elif sender.startswith("@switch-agent-"):
            return  # another agent mentioned us in passing; answering would start agent chatter
        else:
            await self.say(room_id, HELP.format(parent=self.circle.parent))

    async def _intake(self, room_id: str, st: PillboxState, raw: str, sender_name: str, sender: str) -> None:
        from_reader = sender_name.lower() in self.circle.reader_agents
        from_member = self.circle.identify(sender_name, sender) is not None
        if not (from_reader or from_member):
            await self.say(room_id, "🤔 I only take prescriptions from @meds or from the family.")
            return
        try:
            transcript = json.loads(raw)
        except json.JSONDecodeError:
            await self.say(room_id, "🤔 That transcript isn't valid JSON, so I can't check it.")
            return
        result = check_prescription(transcript, ocr_text=transcript.get("ocr_text"))
        if not result.accepted:
            reasons = "\n".join(f"✗ {v} — {why}" for v, why in result.rejected) or "(no lines)"
            await self.say(
                st.room_id,
                f"⚠️ I couldn't add anything from this prescription:\n{reasons}\n"
                "Please check with the doctor or pharmacist, or send a clearer photo.",
            )
            return
        title, detail = card_text(result, self.circle.parent)
        await self._open(
            st,
            {
                "kind": "rx",
                "meds": [asdict(m) for m in result.accepted],
                "left_out": len(result.rejected),
            },
            title=title,
            detail=detail,
            options=[("Approve", APPROVE, "accept"), ("Reject", REJECT, "decline")],
            room_id=st.room_id,
        )

    async def _add_visit(self, room_id: str, st: PillboxState, text: str, sender_name: str, sender: str) -> None:
        trusted = sender_name.lower() in self.circle.planner_agents
        if not (trusted or self.circle.identify(sender_name, sender)):
            await self.say(room_id, "🤔 I only take visits from @coordinator or from the family.")
            return
        try:
            when, what, who = parse_visit(text)
        except ValueError as exc:
            await self.say(room_id, f"🤔 {exc}")
            return
        if when <= self.now():
            await self.say(room_id, f"🤔 {_when(when)} has already passed.")
            return
        st.visits = [v for v in st.visits if v["at"] != when.isoformat()] + [
            {"at": when.isoformat(), "what": what, "who": who, "told": []}
        ]
        st.visits.sort(key=lambda v: v["at"])
        st.save()
        going = f" {who} will take you." if who else ""
        parent_room = await self.parent_room_of(st)
        if parent_room:
            await self.say(parent_room, f"📅 {self.circle.parent}, your next visit: **{_when(when)}** — {what}.{going}")
        await self.say(
            st.room_id,
            f"📅 Noted: {_when(when)} — {what}" + (f" ({who} going)" if who else "")
            + f". I've told {self.circle.parent} and will remind them the evening before and 2 hours before.",
        )

    async def _ask_stop(self, room_id: str, st: PillboxState, name: str) -> None:
        name = name.strip()
        match = next((d for d in st.meds if name and d["name"].lower().startswith(name.lower())), None)
        if not match:
            await self.say(room_id, f"🤔 {name or 'That'} isn't on {self.circle.parent}'s list. Say `list` to see it.")
            return
        m = _med_from(match)
        await self._open(
            st,
            {"kind": "stop", "name": m.name},
            title=f"Take {m.label()} off {self.circle.parent}'s list?",
            detail="Only do this if the doctor said so. Reminders for it stop right away.",
            options=[("Take it off", APPROVE, "accept"), ("Keep it", REJECT, "decline")],
            room_id=st.room_id,
        )

    async def _open(self, st, entry, *, title, detail, options, room_id, expires_in=None) -> str:
        request_id = uuid.uuid4().hex
        kw = {}
        if expires_in is not None:
            kw["expires_in"] = expires_in
        await self.switch.open_approval(
            session_id=SESSION_PREFIX + st.room_id,
            request_id=request_id,
            title=title,
            detail=detail[:MAX_DETAIL],
            options=[{"id": i, "label": label, "decision": dec} for label, i, dec in options],
            room_id=room_id,
            **kw,
        )
        st.pending[request_id] = entry
        st.save()
        return request_id

    # -- answers -------------------------------------------------------------
    async def check_outcomes(self) -> int:
        handled = 0
        for o in await self.switch.approval_outcomes():
            session_id = o.get("sessionId") or o.get("session_id") or ""
            request_id = o.get("requestId") or o.get("request_id") or ""
            if session_id.startswith(SESSION_PREFIX):
                st = self.room(session_id[len(SESSION_PREFIX):])
                entry = st.pending.pop(request_id, None)
                if entry is not None:
                    await self._settle(st, entry, o)
                    handled += 1
            await self.switch.mark_delivered(session_id, request_id)
        return handled

    async def _settle(self, st: PillboxState, entry: dict, o: dict) -> None:
        state, answer = o.get("state"), o.get("answer")
        participant = o.get("answeredBy") or o.get("answered_by")
        who = await self.name_of(st.room_id, participant)
        kind = entry["kind"]
        if kind == "reminder":
            await self._settle_reminder(st, entry, state, answer, who)
            return
        if kind == "call":
            st.save()
            if state == "answered":
                await self.say(st.room_id, f"📞 {who} is calling {self.circle.parent}. Thank you!")
            return
        member = await self.member_of(st.room_id, participant)
        if state == "answered" and self.circle.people_only and member is None:
            st.save()
            await self.say(st.room_id, f"⚠️ {who} isn't in the family circle, so that answer doesn't count. Here's a fresh card.")
            await self._reopen(st, entry)
            return
        if state != "answered" or answer != APPROVE:
            st.save()
            verdict = f"declined by {who}" if state == "answered" else f"the card {state}"
            await self.say(st.room_id, f"❌ Nothing changed on {self.circle.parent}'s list ({verdict}).")
            return
        if kind == "rx":
            today = self.now().date().isoformat()
            new = [dict(m, added_on=today, approved_by=who) for m in entry["meds"]]
            names = {m["name"].lower() for m in new}
            st.meds = [m for m in st.meds if m["name"].lower() not in names] + new
            st.save()
            await self.sync_document(st)
            plan = schedule_markdown(st.active_meds(self.now().date()), self.circle.parent)
            parent_room = await self.parent_room_of(st)
            if parent_room:
                await self.say(parent_room, f"📋 {self.circle.parent}, here is your updated medicine plan:\n\n{plan}")
            left = entry.get("left_out", 0)
            note = f" {left} line(s) were left out — please check them with the doctor." if left else ""
            where = f" {self.circle.parent}'s room has the new plan." if parent_room else ""
            await self.say(
                st.room_id,
                f"✅ Added {len(new)} medicine(s) to {self.circle.parent}'s list — approved by {who}.{where}{note}",
            )
        elif kind == "stop":
            st.meds = [m for m in st.meds if m["name"] != entry["name"]]
            st.save()
            await self.sync_document(st)
            await self.say(st.room_id, f"✅ {entry['name']} is off {self.circle.parent}'s list — approved by {who}.")

    async def _reopen(self, st: PillboxState, entry: dict) -> None:
        if entry["kind"] == "rx":
            meds = [_med_from(m) for m in entry["meds"]]
            from carecircle.meds import CheckResult

            title, detail = card_text(CheckResult(accepted=meds, photo_checked=True), self.circle.parent)
            await self._open(st, entry, title=title, detail=detail,
                             options=[("Approve", APPROVE, "accept"), ("Reject", REJECT, "decline")],
                             room_id=st.room_id)
        elif entry["kind"] == "stop":
            await self._open(st, entry, title=f"Take {entry['name']} off {self.circle.parent}'s list?",
                             detail="Only do this if the doctor said so.",
                             options=[("Take it off", APPROVE, "accept"), ("Keep it", REJECT, "decline")],
                             room_id=st.room_id)

    # -- reminders -----------------------------------------------------------
    def due(self, st: PillboxState, slot: str) -> list[Med]:
        return [m for m in st.active_meds(self.now().date()) if slot in m.slots and not m.as_needed]

    async def send_reminder(self, st: PillboxState, slot: str | None, *, forced: bool = False) -> bool:
        if slot is None:  # the next slot that has medicines, from now on (wrapping to tomorrow)
            hour = self.now().hour
            order = sorted(SLOTS, key=lambda s: (SLOT_HOUR[s][0] < hour, SLOT_HOUR[s][0]))
            slot = next((s for s in order if self.due(st, s)), None)
        meds = self.due(st, slot) if slot else []
        if not meds:
            await self.say(st.room_id, f"🤔 There's nothing on {self.circle.parent}'s list to remind about yet.")
            return False
        parent_room = await self.parent_room_of(st)
        if not parent_room:
            await self.say(st.room_id, f"🤔 I can't find {self.circle.parent}'s room. Link it from this room as \"parent's room\".")
            return False
        lines = [f"• {m.label()} — {m._amount(m.slots[slot])}" + (f" ({m.timing})" if m.timing else "") for m in meds]
        today = self.now().date().isoformat()
        key = f"{today}/{slot}" + ("/now" if forced else "")
        deadline = self.now() + timedelta(minutes=self.circle.reminder_timeout_minutes)
        await self._open(
            st,
            {"kind": "reminder", "slot": slot, "key": key, "names": [m.label() for m in meds],
             "deadline": deadline.isoformat(timespec="seconds")},
            title=f"{SLOT_ICON[slot]} {self.circle.parent}, time for your {slot} medicines",
            detail="\n".join(lines) + "\n\nTap Taken once they're done.",
            options=[("✅ Taken", TAKEN, "accept"), ("⏰ Not yet", LATER, "decline")],
            room_id=parent_room,
            expires_in=timedelta(minutes=self.circle.reminder_timeout_minutes + 5),
        )
        st.reminded[key] = "sent"
        st.save()
        return True

    async def _settle_reminder(self, st, entry, state, answer, who) -> None:
        key, slot = entry["key"], entry["slot"]
        if st.reminded.get(key) == "escalated":
            st.save()
            return
        if state == "answered" and answer == TAKEN:
            st.reminded[key] = "taken"
            st.save()
            at = self.now().strftime("%I:%M %p").lstrip("0")
            await self.say(st.room_id, f"✅ {self.circle.parent} took the {slot} medicines ({at}, confirmed by {who}).")
        elif state == "answered":
            st.reminded[key] = "later"
            st.save()
            await self.say(st.room_id, f"⏰ {self.circle.parent} will take the {slot} medicines a little later ({who} answered).")
        else:
            st.save()
            await self._escalate(st, entry)

    async def tick(self) -> None:
        """Called every ~30 s: send due reminders, escalate unanswered ones."""
        now = self.now()
        for st in list(self.rooms.values()):
            for request_id, entry in list(st.pending.items()):
                if entry.get("kind") == "reminder" and now >= datetime.fromisoformat(entry["deadline"]):
                    st.pending.pop(request_id)
                    st.save()
                    try:
                        await self.switch.close_approval(SESSION_PREFIX + st.room_id, request_id)
                    except Exception as exc:  # noqa: BLE001 - the card may already be closed
                        log.info("closing reminder %s: %s", request_id, exc)
                    await self._escalate(st, entry)
            if self.circle.reminders and st.parent_room:
                await self._visit_reminders(st, now)
            if not (self.circle.reminders and st.meds and st.parent_room):
                continue
            for slot in SLOTS:
                h, m = SLOT_HOUR[slot]
                at = now.replace(hour=h, minute=m, second=0, microsecond=0)
                key = f"{now.date().isoformat()}/{slot}"
                if at <= now < at + WINDOW and key not in st.reminded and self.due(st, slot):
                    await self.send_reminder(st, slot)

    async def _visit_reminders(self, st: PillboxState, now: datetime) -> None:
        changed = False
        for v in st.visits:
            at = datetime.fromisoformat(v["at"])
            eve = (at - timedelta(days=1)).replace(hour=VISIT_EVE_HOUR, minute=0)
            going = f" {v['who']} will take you." if v.get("who") else ""
            if "eve" not in v["told"] and eve <= now < at - VISIT_LEAD:
                v["told"].append("eve")
                changed = True
                await self.say(st.parent_room, f"🌙 {self.circle.parent}, tomorrow: {v['what']} at {at.strftime('%I:%M %p').lstrip('0')}.{going}")
            if "soon" not in v["told"] and at - VISIT_LEAD <= now < at:
                v["told"].append("soon")
                changed = True
                await self.say(st.parent_room, f"⏰ {self.circle.parent}, in about 2 hours: {v['what']}.{going}")
                await self.say(st.room_id, f"⏰ {self.circle.parent}'s visit is in 2 hours: {v['what']}" + (f" ({v['who']} going)." if v.get("who") else "."))
        past = [v for v in st.visits if datetime.fromisoformat(v["at"]) < now - timedelta(hours=6)]
        if past or changed:
            st.visits = [v for v in st.visits if v not in past]
            st.save()

    def visits_text(self, st: PillboxState) -> str:
        if not st.visits:
            return f"📅 No visits planned for {self.circle.parent}."
        return f"📅 **{self.circle.parent}'s visits**\n" + "\n".join(
            f"• {_when(datetime.fromisoformat(v['at']))} — {v['what']}" + (f" ({v['who']} going)" if v.get("who") else "")
            for v in st.visits
        )

    async def _escalate(self, st: PillboxState, entry: dict) -> None:
        if st.reminded.get(entry["key"]) in ("taken", "later", "escalated"):
            return
        st.reminded[entry["key"]] = "escalated"
        st.save()
        names = ", ".join(entry["names"])
        await self.say(
            st.room_id,
            f"⚠️ Nobody confirmed {self.circle.parent}'s {entry['slot']} medicines ({names}) "
            f"within {self.circle.reminder_timeout_minutes} minutes.",
        )
        await self._open(
            st,
            {"kind": "call"},
            title=f"Can someone call {self.circle.parent}?",
            detail=f"The {entry['slot']} reminder ({SLOT_TIME[entry['slot']]}) wasn't confirmed.",
            options=[("📞 I'll call", CALLING, "accept")],
            room_id=st.room_id,
            expires_in=timedelta(hours=3),
        )

    # -- the parent's room, names, the document ----------------------------
    async def parent_room_of(self, st: PillboxState) -> str | None:
        if st.parent_room:
            return st.parent_room
        found = None
        try:
            links = await self.switch.op("list_linked_rooms", {}, connection_id=self.connections.get(st.room_id))
            for link in _dicts(links):
                if "parent" in str(link.get("label", "")).lower():
                    found = link.get("room_id") or link.get("to_room_id") or link.get("target_room_id") or link.get("id")
                    break
        except Exception as exc:  # noqa: BLE001
            log.warning("list_linked_rooms failed: %s", exc)
        if not found and self.circle.parent_room:
            try:
                for r in _dicts(await self.switch.op("list_rooms")):
                    if r.get("name") == self.circle.parent_room:
                        found = r.get("room_id") or r.get("id")
            except Exception as exc:  # noqa: BLE001
                log.warning("list_rooms failed: %s", exc)
        if found:
            st.parent_room = str(found)
            self._parent_of[st.parent_room] = st.room_id
            st.save()
        return st.parent_room

    async def _load_names(self, room_id: str) -> dict[str, str]:
        names: dict[str, str] = {}
        try:
            result = await self.switch.op("list_participants", {}, connection_id=self.connections.get(room_id))
        except Exception as exc:  # noqa: BLE001
            log.warning("could not list participants of %s: %s", room_id, exc)
            result = None
        for p in _dicts(result):
            pid = next((p[k] for k in ("id", "user_id", "participant_id", "mxid") if p.get(k)), None)
            name = next((p[k] for k in ("display_name", "name", "username") if p.get(k)), None)
            if pid and name:
                names[str(pid)] = str(name)
        self._names[room_id] = names
        return names

    async def member_of(self, room_id: str, participant: str | None) -> str | None:
        if not participant:
            return None
        names = self._names.get(room_id) or await self._load_names(room_id)
        keys = [participant, participant.removeprefix("user:")]
        name = next((names[k] for k in keys if k in names), None)
        return self.circle.identify(name, participant)

    async def name_of(self, room_id: str, participant: str | None) -> str:
        if not participant:
            return "someone"
        member = await self.member_of(room_id, participant)
        if member:
            return member.title()
        if self.circle.is_parent(participant):
            return self.circle.parent
        names = self._names.get(room_id, {})
        return names.get(participant) or (chat_name(participant) if participant.startswith("@") else "someone")

    async def sync_document(self, st: PillboxState) -> None:
        meds = st.active_meds(self.now().date())
        content = schedule_markdown(meds, self.circle.parent)
        content += "\n## Where this came from\n"
        content += "\n".join(
            f"- {m['name']}: added {m.get('added_on', '?')}, approved by {m.get('approved_by', '?')}"
            for m in st.meds
        ) or "- Nothing yet."
        conn = self.connections.get(st.room_id)
        try:
            if st.doc_id:
                await self.switch.op("update_room_document", {"document_id": st.doc_id, "content": content}, connection_id=conn)
            else:
                res = await self.switch.op(
                    "create_room_document",
                    {
                        "name": DOC_NAME,
                        "description": f"{self.circle.parent}'s current medicines and dose times.",
                        "instructions": "Kept by @pillbox from approved prescriptions only. Not medical advice; "
                        "to change it, send a new prescription to @meds or ask @pillbox to stop a medicine.",
                        "content": content,
                    },
                    connection_id=conn,
                )
                st.doc_id = _find_id(res)
                st.save()
        except Exception as exc:  # noqa: BLE001 - the list itself is saved
            log.warning("could not update %s in %s: %s", DOC_NAME, st.room_id, exc)

    # -- text ------------------------------------------------------------------
    def today_text(self, st: PillboxState) -> str:
        meds = st.active_meds(self.now().date())
        if not meds:
            return f"📋 {self.circle.parent}'s list is empty. Send a prescription photo to @meds."
        out = [f"📋 **{self.circle.parent}'s doses today**"]
        for slot in SLOTS:
            due = [m for m in meds if slot in m.slots and not m.as_needed]
            if due:
                status = st.reminded.get(f"{self.now().date().isoformat()}/{slot}", "")
                mark = {"taken": " ✅", "later": " ⏰", "escalated": " ⚠️"}.get(status, "")
                out.append(f"{SLOT_ICON[slot]} {SLOT_TIME[slot]}{mark}: " + ", ".join(m.label() for m in due))
        prn = [m.label() for m in meds if m.as_needed]
        if prn:
            out.append("🩹 Only when needed: " + ", ".join(prn))
        if st.visits:
            v = st.visits[0]
            out.append(f"📅 Next visit: {_when(datetime.fromisoformat(v['at']))} — {v['what']}")
        return "\n".join(out)

    def list_text(self, st: PillboxState) -> str:
        meds = st.active_meds(self.now().date())
        if not meds:
            return f"📋 {self.circle.parent}'s list is empty."
        return f"📋 **{self.circle.parent}'s medicines**\n" + "\n".join(f"• {m.describe()}" for m in meds)


def _dicts(result: Any) -> list[dict]:
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
