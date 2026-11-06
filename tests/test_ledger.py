import random

import pytest

from carecircle.ledger import Ledger, LedgerError, split

SIBS = ["priya", "rahul", "ankit"]


def test_split_equal_exact():
    assert split(240000, {"priya": 1, "rahul": 1, "ankit": 1}) == {
        "priya": 80000,
        "rahul": 80000,
        "ankit": 80000,
    }


def test_split_remainder_is_deterministic():
    # ₹100 three ways: one paisa left over, it goes to the first listed
    assert split(10000, {"priya": 1, "rahul": 1, "ankit": 1}) == {
        "priya": 3334,
        "rahul": 3333,
        "ankit": 3333,
    }


def test_split_weighted():
    assert split(300000, {"priya": 2, "rahul": 1, "ankit": 1}) == {
        "priya": 150000,
        "rahul": 75000,
        "ankit": 75000,
    }


def test_split_always_sums_to_amount():
    rng = random.Random(7)
    for _ in range(2000):
        n = rng.randint(1, 6)
        shares = {f"m{i}": rng.randint(1, 5) for i in range(n)}
        amount = rng.randint(1, 10_000_000)
        parts = split(amount, shares)
        assert sum(parts.values()) == amount
        assert all(v >= 0 for v in parts.values())


@pytest.mark.parametrize("shares", [{}, {"priya": 0}, {"priya": -1}])
def test_split_rejects_bad_shares(shares):
    with pytest.raises(LedgerError):
        split(100, shares)


def test_balances_and_settle_up():
    led = Ledger(SIBS)
    led.record(led.propose_expense(240000, "Lab tests", "ankit"), "rahul")
    led.record(led.propose_expense(60000, "Medicines", "priya"), "ankit")
    bal = led.balances()
    assert sum(bal.values()) == 0
    # ankit paid 2400, owes 1000 -> +1400; priya paid 600, owes 1000 -> -400
    assert bal == {"priya": -40000, "rahul": -100000, "ankit": 140000}
    transfers = led.settle_up()
    assert [(t.frm, t.to, t.amount) for t in transfers] == [
        ("rahul", "ankit", 100000),
        ("priya", "ankit", 40000),
    ]


def test_payment_clears_balance():
    led = Ledger(SIBS)
    led.record(led.propose_expense(300000, "Nurse", "priya"), "rahul")
    for t in led.settle_up():
        led.record(led.propose_payment(t.frm, t.to, t.amount), t.to)
    assert set(led.balances().values()) == {0}
    assert led.settle_up() == []


def test_settle_up_zeroes_random_ledgers():
    rng = random.Random(11)
    for _ in range(300):
        led = Ledger(SIBS + ["meera"])
        for _ in range(rng.randint(1, 12)):
            payer = rng.choice(led.members)
            who = rng.sample(led.members, rng.randint(1, 4))
            shares = {m: rng.randint(1, 3) for m in who}
            led.record(led.propose_expense(rng.randint(1, 500000), "x", payer, shares), "t")
        for t in led.settle_up():
            led.record(led.propose_payment(t.frm, t.to, t.amount), "t")
        assert set(led.balances().values()) == {0}


def test_unknown_member_rejected():
    led = Ledger(SIBS)
    with pytest.raises(LedgerError, match="not in the circle"):
        led.propose_expense(100, "x", "stranger")
    with pytest.raises(LedgerError):
        led.propose_payment("priya", "priya", 100)


def test_proposal_is_not_recorded_until_approved():
    led = Ledger(SIBS)
    led.propose_expense(240000, "Lab tests", "ankit")
    assert led.expenses == []
    assert set(led.balances().values()) == {0}


def test_round_trip_json(tmp_path):
    led = Ledger(SIBS)
    led.record(led.propose_expense(240000, "Lab tests", "ankit"), "rahul")
    led.record(led.propose_payment("priya", "ankit", 80000), "ankit")
    path = tmp_path / "ledger.json"
    led.save(path)
    again = Ledger.load(path, SIBS)
    assert again == led
    assert "₹2,400" in again.render_markdown()
    assert "approved by rahul" in again.render_markdown()
