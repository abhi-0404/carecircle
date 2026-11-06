"""@ledger end to end against a fake Switch: messages in, cards out, taps back."""

import asyncio

import pytest

from carecircle.circle import Circle
from carecircle.ledger_agent import APPROVE, REJECT, SESSION_PREFIX, LedgerAgent

ROOM = "room-family"
CIRCLE = Circle.from_dict(
    {"parent": "Ma", "members": {"priya": ["Priya S"], "rahul": [], "ankit": ["ankit_k"]}}
)


class FakeSwitch:
    def __init__(self):
        self.sent: list[tuple[str, str]] = []
        self.cards: list[dict] = []
        self.ops: list[tuple[str, dict]] = []
        self.outcomes: list[dict] = []
        self.delivered: list[tuple[str, str]] = []

    async def op(self, name, args=None, connection_id=None):
        self.ops.append((name, args or {}))
        if name == "create_room_document":
            return {"document": {"id": "doc-1"}}
        if name == "list_participants":
            return {
                "participants": [
                    {"id": "@switch-user-r1:local", "display_name": "Rahul"},
                    {"id": "@switch-user-a1:local", "display_name": "Ankit"},
                    {"id": "@switch-user-p1:local", "display_name": "Priya S"},
                    {"id": "@switch-user-x9:local", "display_name": "Cousin Vikram"},
                ]
            }
        return {}

    async def send(self, room_id, content):
        self.sent.append((room_id, content))

    async def open_approval(self, **kw):
        self.cards.append(kw)
        return {}

    async def approval_outcomes(self):
        out, self.outcomes = self.outcomes, []
        return out

    async def mark_delivered(self, session_id, request_id):
        self.delivered.append((session_id, request_id))

    def tap(self, card: dict, option: str, by: str = "@switch-user-r1:local", state="answered"):
        self.outcomes.append(
            {
                "sessionId": card["session_id"],
                "requestId": card["request_id"],
                "state": state,
                "answer": option if state == "answered" else None,
                "answeredBy": by if state == "answered" else None,
            }
        )


def msg(body, sender_name="Ankit", sender="@switch-user-a1:local"):
    return {"addressed": True, "body": body, "sender_name": sender_name, "sender": sender}


@pytest.fixture
def setup(tmp_path):
    fake = FakeSwitch()
    return fake, LedgerAgent(fake, CIRCLE, tmp_path)


def run(coro):
    return asyncio.run(coro)


def test_expense_waits_for_approval_then_records(setup):
    fake, agent = setup
    run(agent.handle_message(ROOM, msg("@ledger add ₹2,400 lab tests")))
    assert len(fake.cards) == 1
    card = fake.cards[0]
    assert card["title"] == "Record ₹2,400 for lab tests?"
    assert "Paid by Ankit" in card["detail"] and "Priya ₹800" in card["detail"]
    assert card["session_id"] == SESSION_PREFIX + ROOM and card["room_id"] == ROOM
    assert [o["decision"] for o in card["options"]] == ["accept", "decline"]
    # nothing recorded yet
    assert agent.room(ROOM).ledger.expenses == []

    fake.tap(card, APPROVE)
    assert run(agent.check_outcomes()) == 1
    led = agent.room(ROOM).ledger
    assert len(led.expenses) == 1 and led.expenses[0].approved_by == "Rahul"
    assert "✅ Recorded #1" in fake.sent[-1][1] and "approved by Rahul" in fake.sent[-1][1]
    assert "Ankit is owed ₹1,600" in fake.sent[-1][1]
    assert fake.delivered == [(card["session_id"], card["request_id"])]
    # the room document was created with the ledger in it
    name, args = next(o for o in fake.ops if o[0] == "create_room_document")
    assert args["name"] == "expense-ledger" and "₹2,400" in args["content"]
    assert agent.room(ROOM).doc_id == "doc-1"


def test_second_record_updates_document(setup):
    fake, agent = setup
    for body in ("add 600 medicines", "add 900 auto fare"):
        run(agent.handle_message(ROOM, msg(body)))
        fake.tap(fake.cards[-1], APPROVE)
        run(agent.check_outcomes())
    assert [o[0] for o in fake.ops if "document" in o[0]] == [
        "create_room_document",
        "update_room_document",
    ]
    assert fake.ops[-1][1]["document_id"] == "doc-1"


def test_rejected_is_not_recorded(setup):
    fake, agent = setup
    run(agent.handle_message(ROOM, msg("add 2400 lab tests paid by priya")))
    fake.tap(fake.cards[0], REJECT)
    run(agent.check_outcomes())
    assert agent.room(ROOM).ledger.expenses == []
    assert fake.sent[-1][1].startswith("❌ Not recorded")


def test_expired_is_not_recorded(setup):
    fake, agent = setup
    run(agent.handle_message(ROOM, msg("add 2400 lab tests")))
    fake.tap(fake.cards[0], APPROVE, state="expired")
    run(agent.check_outcomes())
    assert agent.room(ROOM).ledger.expenses == []
    assert "expired" in fake.sent[-1][1]


def test_duplicate_outcome_records_once(setup):
    fake, agent = setup
    run(agent.handle_message(ROOM, msg("add 300 fruit")))
    fake.tap(fake.cards[0], APPROVE)
    fake.tap(fake.cards[0], APPROVE)
    run(agent.check_outcomes())
    assert len(agent.room(ROOM).ledger.expenses) == 1


def test_state_survives_restart(setup, tmp_path):
    fake, agent = setup
    run(agent.handle_message(ROOM, msg("add 2400 lab tests")))
    # @ledger restarts before anyone taps
    again = LedgerAgent(fake, CIRCLE, tmp_path)
    fake.tap(fake.cards[0], APPROVE)
    run(again.check_outcomes())
    assert len(again.room(ROOM).ledger.expenses) == 1


def test_unknown_sender_must_name_payer(setup):
    fake, agent = setup
    run(agent.handle_message(ROOM, msg("add 500 taxi", sender_name="Cousin Vikram", sender="@x:y")))
    assert fake.cards == []
    assert "paid by <name>" in fake.sent[-1][1]


def test_alias_identifies_sender(setup):
    fake, agent = setup
    run(agent.handle_message(ROOM, msg("add 500 taxi", sender_name="Priya S")))
    assert "Paid by Priya" in fake.cards[0]["detail"]


def test_payment_and_settle(setup):
    fake, agent = setup
    run(agent.handle_message(ROOM, msg("add 3000 nurse visit")))
    fake.tap(fake.cards[-1], APPROVE)
    run(agent.check_outcomes())
    run(agent.handle_message(ROOM, msg("settle")))
    assert "Priya → Ankit: ₹1,000" in fake.sent[-1][1]
    run(agent.handle_message(ROOM, msg("paid 1000 from priya to ankit")))
    assert "Priya paid Ankit ₹1,000" in fake.cards[-1]["title"]
    fake.tap(fake.cards[-1], APPROVE)
    run(agent.check_outcomes())
    run(agent.handle_message(ROOM, msg("balance")))
    assert "Priya is square" in fake.sent[-1][1]


STRICT = Circle.from_dict(
    {
        "parent": "Ma",
        "members": {"priya": ["Priya S"], "rahul": [], "ankit": []},
        "approval": {"people_only": True, "not_own_entry": True},
    }
)


def test_stranger_tap_does_not_count(setup):
    fake, agent = setup
    run(agent.handle_message(ROOM, msg("add 2400 lab tests")))
    fake.tap(fake.cards[0], APPROVE, by="@switch-user-x9:local")
    run(agent.check_outcomes())
    assert agent.room(ROOM).ledger.expenses == []
    assert fake.sent[-1][1].startswith("⚠️ Cousin Vikram can't decide this one")
    assert len(fake.cards) == 2  # a fresh card replaced the spent one
    fake.tap(fake.cards[1], APPROVE)  # Rahul
    run(agent.check_outcomes())
    assert len(agent.room(ROOM).ledger.expenses) == 1


def test_nobody_approves_their_own_expense(tmp_path):
    fake = FakeSwitch()
    agent = LedgerAgent(fake, STRICT, tmp_path)
    run(agent.handle_message(ROOM, msg("add 2400 lab tests")))  # Ankit paid
    fake.tap(fake.cards[0], APPROVE, by="@switch-user-a1:local")  # Ankit approves himself
    run(agent.check_outcomes())
    assert agent.room(ROOM).ledger.expenses == []
    assert "another sibling has to confirm" in fake.sent[-1][1]
    fake.tap(fake.cards[1], APPROVE, by="@switch-user-r1:local")  # Rahul confirms
    run(agent.check_outcomes())
    assert agent.room(ROOM).ledger.expenses[0].approved_by == "Rahul"


def test_payer_may_still_withdraw_own_entry(tmp_path):
    fake = FakeSwitch()
    agent = LedgerAgent(fake, STRICT, tmp_path)
    run(agent.handle_message(ROOM, msg("add 2400 lab tests")))
    fake.tap(fake.cards[0], REJECT, by="@switch-user-a1:local")
    run(agent.check_outcomes())
    assert fake.sent[-1][1].startswith("❌ Not recorded")
    assert len(fake.cards) == 1


def test_payment_is_confirmed_by_receiver(tmp_path):
    fake = FakeSwitch()
    agent = LedgerAgent(fake, STRICT, tmp_path)
    run(agent.handle_message(ROOM, msg("paid 800 from priya to ankit")))
    fake.tap(fake.cards[0], APPROVE, by="@switch-user-r1:local")  # Rahul can't confirm
    run(agent.check_outcomes())
    assert "only Ankit, who received the money" in fake.sent[-1][1]
    fake.tap(fake.cards[1], APPROVE, by="@switch-user-a1:local")  # Ankit confirms
    run(agent.check_outcomes())
    assert len(agent.room(ROOM).ledger.payments) == 1


def test_bad_input_gets_help_not_a_card(setup):
    fake, agent = setup
    run(agent.handle_message(ROOM, msg("@ledger buy milk")))
    run(agent.handle_message(ROOM, msg("add 100 x paid by stranger")))
    assert fake.cards == []
    assert "help" in fake.sent[0][1] and "not in the circle" in fake.sent[1][1]
