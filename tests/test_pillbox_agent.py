"""@pillbox end to end against a fake Switch and a clock we control."""

import asyncio
import json
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from carecircle.circle import Circle
from carecircle.pillbox_agent import APPROVE, CALLING, REJECT, SESSION_PREFIX, TAKEN, PillboxAgent

FAMILY, MA_ROOM = "room-family", "room-ma"
SAMPLE = json.loads(
    (Path(__file__).parents[1] / "demo" / "samples" / "prescription-cardiology.transcript.json").read_text(
        encoding="utf-8"
    )
)
CIRCLE = Circle.from_dict(
    {
        "parent": "Ma",
        "members": {"priya": [], "rahul": [], "ankit": []},
        "parent_handles": ["ma_sharma"],
        "reminders": {"timeout_minutes": 30},
    }
)
PEOPLE = {
    "@switch-user-r1:local": "Rahul",
    "@switch-user-a1:local": "Ankit",
    "@switch-user-x9:local": "Cousin Vikram",
    "@switch-discord-d9947352-c5c4-411c-82c7-3738fdc6977b-ma_sharma:local": "ma_sharma",
}


class Clock:
    def __init__(self, t: datetime):
        self.t = t

    def __call__(self) -> datetime:
        return self.t


class FakeSwitch:
    def __init__(self):
        self.sent, self.cards, self.ops, self.closed, self.delivered = [], [], [], [], []
        self.outcomes = []

    async def op(self, name, args=None, connection_id=None):
        self.ops.append((name, args or {}))
        if name == "create_room_document":
            return {"id": "doc-meds"}
        if name == "list_linked_rooms":
            return {"links": [{"room_id": MA_ROOM, "name": "sharma-ma", "label": "parent's room"}]}
        if name == "list_participants":
            return [{"id": k, "name": v} for k, v in PEOPLE.items()]
        return {}

    async def send(self, room_id, content):
        self.sent.append((room_id, content))

    async def open_approval(self, **kw):
        self.cards.append(kw)
        return {}

    async def close_approval(self, session_id, request_id):
        self.closed.append(request_id)

    async def approval_outcomes(self):
        out, self.outcomes = self.outcomes, []
        return out

    async def mark_delivered(self, session_id, request_id):
        self.delivered.append(request_id)

    def tap(self, card, option, by="@switch-user-r1:local", state="answered"):
        self.outcomes.append({"sessionId": card["session_id"], "requestId": card["request_id"],
                              "state": state, "answer": option, "answeredBy": by})


def run(c):
    return asyncio.run(c)


def from_meds(transcript=SAMPLE):
    return {"addressed": True, "sender_name": "meds", "sender": "@switch-agent-meds:local",
            "body": "@pillbox new prescription for Ma, transcribed:\n```json\n"
                    + json.dumps(transcript) + "\n```"}


def say(text, who="Ankit", pid="@switch-user-a1:local"):
    return {"addressed": True, "sender_name": who, "sender": pid, "body": f"@pillbox {text}"}


@pytest.fixture
def env(tmp_path):
    fake, clock = FakeSwitch(), Clock(datetime(2026, 11, 7, 7, 30))
    agent = PillboxAgent(fake, CIRCLE, tmp_path, now=clock)
    return fake, clock, agent


def approve_prescription(fake, agent):
    run(agent.handle_message(FAMILY, from_meds()))
    fake.tap(fake.cards[-1], APPROVE)
    run(agent.check_outcomes())


def test_transcript_becomes_a_card_not_a_change(env):
    fake, _, agent = env
    run(agent.handle_message(FAMILY, from_meds()))
    card = fake.cards[0]
    assert card["title"] == "Add 4 medicines to Ma's schedule?"
    assert card["room_id"] == FAMILY and card["session_id"] == SESSION_PREFIX + FAMILY
    assert "Amlodipine 5 mg — 1 tablet morning, 1 tablet night" in card["detail"]
    assert "not medical advice" in card["detail"]
    assert agent.room(FAMILY).meds == []


def test_approved_prescription_updates_list_doc_and_parent_room(env):
    fake, _, agent = env
    approve_prescription(fake, agent)
    st = agent.room(FAMILY)
    assert [m["name"] for m in st.meds] == ["Amlodipine", "Metformin", "Atorvastatin", "Paracetamol"]
    assert all(m["approved_by"] == "Rahul" for m in st.meds)
    name, args = next(o for o in fake.ops if o[0] == "create_room_document")
    assert args["name"] == "medicine-list" and "Amlodipine" in args["content"]
    to_ma = [t for r, t in fake.sent if r == MA_ROOM]
    assert to_ma and "here is your updated medicine plan" in to_ma[0]
    assert fake.sent[-1] == (FAMILY, "✅ Added 4 medicine(s) to Ma's list — approved by Rahul. Ma's room has the new plan.")


def test_rejected_prescription_changes_nothing(env):
    fake, _, agent = env
    run(agent.handle_message(FAMILY, from_meds()))
    fake.tap(fake.cards[0], REJECT)
    run(agent.check_outcomes())
    assert agent.room(FAMILY).meds == []
    assert fake.sent[-1][1].startswith("❌ Nothing changed")


def test_stranger_cannot_approve(env):
    fake, _, agent = env
    run(agent.handle_message(FAMILY, from_meds()))
    fake.tap(fake.cards[0], APPROVE, by="@switch-user-x9:local")
    run(agent.check_outcomes())
    assert agent.room(FAMILY).meds == []
    assert len(fake.cards) == 2 and "isn't in the family circle" in fake.sent[-1][1]


def test_unknown_agent_cannot_submit(env):
    fake, _, agent = env
    msg = from_meds()
    msg["sender_name"] = "some-bot"
    run(agent.handle_message(FAMILY, msg))
    assert fake.cards == [] and "only take prescriptions" in fake.sent[-1][1]


def test_hallucinated_transcript_gets_no_card(env):
    fake, _, agent = env
    bad = {"lines": [{"verbatim": "Tab. Amlodipine 5mg 1-0-1", "name": "Atenolol", "strength": "5mg", "dose": "1-0-1"}]}
    run(agent.handle_message(FAMILY, from_meds(bad)))
    assert fake.cards == []
    assert "couldn't add anything" in fake.sent[-1][1] and "Atenolol" in fake.sent[-1][1]


def test_morning_reminder_and_taken(env):
    fake, clock, agent = env
    approve_prescription(fake, agent)
    clock.t = datetime(2026, 11, 7, 8, 5)
    run(agent.tick())
    run(agent.tick())  # a second tick in the window sends nothing new
    reminders = [c for c in fake.cards if c["room_id"] == MA_ROOM]
    assert len(reminders) == 1
    r = reminders[0]
    assert r["title"] == "🌅 Ma, time for your morning medicines"
    assert "Amlodipine 5 mg — 1 tablet (after food)" in r["detail"] and "Atorvastatin" not in r["detail"]
    assert [o["id"] for o in r["options"]] == ["taken", "later"]
    fake.tap(r, TAKEN, by="@switch-discord-d9947352-c5c4-411c-82c7-3738fdc6977b-ma_sharma:local")
    run(agent.check_outcomes())
    assert fake.sent[-1] == (FAMILY, "✅ Ma took the morning medicines (8:05 AM, confirmed by Ma).")
    run(agent.handle_message(FAMILY, say("today")))
    assert "8:00 AM ✅" in fake.sent[-1][1]


def test_unanswered_reminder_escalates_to_family(env):
    fake, clock, agent = env
    approve_prescription(fake, agent)
    clock.t = datetime(2026, 11, 7, 8, 5)
    run(agent.tick())
    reminder = fake.cards[-1]
    clock.t += timedelta(minutes=31)
    run(agent.tick())
    assert reminder["request_id"] in fake.closed
    assert any("Nobody confirmed Ma's morning medicines" in t for r, t in fake.sent if r == FAMILY)
    call = fake.cards[-1]
    assert call["room_id"] == FAMILY and call["title"] == "Can someone call Ma?"
    fake.tap(call, CALLING)
    run(agent.check_outcomes())
    assert fake.sent[-1] == (FAMILY, "📞 Rahul is calling Ma. Thank you!")
    # Switch's own expiry arriving later changes nothing
    fake.tap(reminder, None, state="expired")
    run(agent.check_outcomes())
    assert sum("Nobody confirmed" in t for _, t in fake.sent) == 1


def test_no_reminder_outside_the_window(env):
    fake, clock, agent = env
    approve_prescription(fake, agent)
    clock.t = datetime(2026, 11, 7, 9, 0)  # 8:00 + 30 min window has passed
    run(agent.tick())
    assert [c for c in fake.cards if c["room_id"] == MA_ROOM] == []


def test_remind_now_picks_the_next_slot(env):
    fake, clock, agent = env
    approve_prescription(fake, agent)
    clock.t = datetime(2026, 11, 7, 15, 0)
    run(agent.handle_message(FAMILY, say("remind now")))
    r = fake.cards[-1]
    assert r["room_id"] == MA_ROOM and "night" in r["title"]
    assert "Atorvastatin 10 mg" in r["detail"]


def test_stop_needs_approval(env):
    fake, _, agent = env
    approve_prescription(fake, agent)
    run(agent.handle_message(FAMILY, say("stop amlodipine")))
    assert fake.cards[-1]["title"] == "Take Amlodipine 5 mg off Ma's list?"
    fake.tap(fake.cards[-1], APPROVE)
    run(agent.check_outcomes())
    assert "Amlodipine" not in [m["name"] for m in agent.room(FAMILY).meds]


def test_finished_course_drops_off(env):
    fake, clock, agent = env
    approve_prescription(fake, agent)
    clock.t = datetime(2026, 12, 8, 8, 5)  # 31 days after 7 Nov: the 30-day courses are done
    names = [m.name for m in agent.room(FAMILY).active_meds(clock.t.date())]
    assert "Amlodipine" not in names and "Metformin" in names  # Metformin has no end date


def coordinator(text):
    return {"addressed": True, "sender_name": "coordinator", "sender": "@switch-agent-c:local",
            "body": f"@pillbox {text}"}


def test_visit_from_coordinator_tells_ma_and_reminds(env):
    fake, clock, agent = env
    approve_prescription(fake, agent)  # also finds Ma's room
    run(agent.handle_message(FAMILY, coordinator("visit 2026-11-13 10:00 | Cardiology check-up, Dr. Kapoor | Rahul")))
    to_ma = [t for r, t in fake.sent if r == MA_ROOM]
    assert to_ma[-1] == "📅 Ma, your next visit: **Friday 13 Nov, 10:00 AM** — Cardiology check-up, Dr. Kapoor. Rahul will take you."
    assert fake.sent[-1][0] == FAMILY and "will remind them the evening before" in fake.sent[-1][1]
    clock.t = datetime(2026, 11, 12, 19, 1)
    run(agent.tick())
    run(agent.tick())
    eve = [t for r, t in fake.sent if r == MA_ROOM and t.startswith("🌙")]
    assert eve == ["🌙 Ma, tomorrow: Cardiology check-up, Dr. Kapoor at 10:00 AM. Rahul will take you."]
    clock.t = datetime(2026, 11, 13, 8, 10)
    run(agent.tick())
    assert any(t.startswith("⏰ Ma, in about 2 hours") for r, t in fake.sent if r == MA_ROOM)
    assert any("visit is in 2 hours" in t for r, t in fake.sent if r == FAMILY)
    run(agent.handle_message(FAMILY, say("today")))
    assert "Next visit: Friday 13 Nov, 10:00 AM" in fake.sent[-1][1]


@pytest.mark.parametrize("text", ["visit tomorrow morning", "visit 2026-11-13 | no time", "visit 13/11/2026 10:00 | x"])
def test_visit_needs_the_exact_form(env, text):
    fake, _, agent = env
    run(agent.handle_message(FAMILY, coordinator(text)))
    assert "Say it like: visit" in fake.sent[-1][1]


def test_past_visit_is_refused(env):
    fake, _, agent = env
    run(agent.handle_message(FAMILY, coordinator("visit 2026-11-01 10:00 | old | Rahul")))
    assert "has already passed" in fake.sent[-1][1]


def test_unknown_agent_cannot_add_visit(env):
    fake, _, agent = env
    msg = coordinator("visit 2026-11-13 10:00 | x | y")
    msg["sender_name"] = "some-bot"
    run(agent.handle_message(FAMILY, msg))
    assert "only take visits" in fake.sent[-1][1]


def test_messages_in_parent_room_act_on_family(env):
    fake, _, agent = env
    approve_prescription(fake, agent)
    run(agent.handle_message(MA_ROOM, say("today", who="ma_sharma", pid="@x:y")))
    assert fake.sent[-1][0] == MA_ROOM and "Ma's doses today" in fake.sent[-1][1]
