import pytest

from carecircle.commands import AddExpense, AddPayment, CommandError, Query, parse


def test_add_simple():
    assert parse("@ledger add 2400 lab tests") == AddExpense(240000, "lab tests", None, None)


def test_add_discord_mention_and_rupee_sign():
    assert parse("<@123456> add ₹2,400 for lab tests") == AddExpense(
        240000, "lab tests", None, None
    )


def test_add_discord_role_mention():
    assert parse("<@&1568210191730610288> add 2400 lab tests") == AddExpense(
        240000, "lab tests", None, None
    )


def test_add_paid_by():
    assert parse("@ledger add 2400 lab tests paid by Ankit") == AddExpense(
        240000, "lab tests", "ankit", None
    )


def test_add_paid_by_inline_mention():
    assert parse("@ledger add 2400 lab tests paid by @ankit") == AddExpense(
        240000, "lab tests", "ankit", None
    )


def test_add_weighted_split():
    assert parse("add 3000 nurse visit paid by priya split priya:2 rahul:1, ankit") == (
        AddExpense(300000, "nurse visit", "priya", {"priya": 2, "rahul": 1, "ankit": 1})
    )


def test_add_split_equally_means_everyone():
    assert parse("add 900 auto fare split equally").shares is None


def test_payment():
    assert parse("@ledger paid 800 from Priya to Ankit") == AddPayment(80000, "priya", "ankit")


@pytest.mark.parametrize("word, what", [("balance", "balance"), ("balances", "balance"),
                                        ("settle", "settle"), ("history", "history"),
                                        ("help", "help"), ("", "help")])
def test_queries(word, what):
    assert parse(f"@ledger {word}") == Query(what)


@pytest.mark.parametrize("text", ["@ledger hello - show the family how to record an expense.",
                                  "@ledger hi!", "<@&123> namaste"])
def test_greeting_gets_help(text):
    assert parse(text) == Query("help")


@pytest.mark.parametrize("text", ["@ledger buy milk", "add lots lab", "add 0 nothing",
                                  "add 100 x split priya:two"])
def test_rejects(text):
    with pytest.raises(CommandError):
        parse(text)
