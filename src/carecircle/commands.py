"""What people (and other agents) can say to @ledger. A small fixed grammar,
parsed by code, so the ledger never guesses what a message meant.

    add 2400 lab tests                       payer = whoever sent it, split equally
    add ₹2,400 lab tests paid by ankit
    add 3000 nurse visit split priya:2 rahul:1 ankit:1
    paid 800 from priya to ankit             a settle-up payment
    balance | settle | history | help
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from carecircle.money import MoneyError, parse_rupees

HELP = """**@ledger** — I keep the family's shared expenses. I never guess; say it like this:
• `add 2400 lab tests` — you paid, split equally
• `add 2400 lab tests paid by ankit` — someone else paid
• `add 3000 nurse visit split priya:2 rahul:1 ankit:1` — agreed shares
• `paid 800 from priya to ankit` — record a settle-up payment
• `balance` · `settle` · `history`
Every entry waits for a sibling to approve it before it's recorded."""


class CommandError(ValueError):
    pass


@dataclass(frozen=True)
class AddExpense:
    amount: int
    description: str
    paid_by: str | None  # None: the sender
    shares: dict[str, int] | None  # None: everyone equally


@dataclass(frozen=True)
class AddPayment:
    amount: int
    frm: str
    to: str


@dataclass(frozen=True)
class Query:
    what: str  # balance | settle | history | help


Command = AddExpense | AddPayment | Query

# Discord sends a user mention as <@id> / <@!id> and a role mention as <@&id>;
# Switch gives each agent a mentionable role, so "@ledger" may arrive as either.
_LEADING_MENTIONS = re.compile(r"^(?:\s*(?:<@[!&]?\d+>|@[\w.\-]+)[\s,:]*)+")
_INLINE_AT = re.compile(r"@([\w.\-]+)")
_AMOUNT = r"((?:₹|rs\.?|inr)?\s*[\d,]+(?:\.\d{1,2})?)"
_ADD = re.compile(rf"^add\s+{_AMOUNT}\s*(.*)$", re.IGNORECASE)
_PAID = re.compile(
    rf"^paid\s+{_AMOUNT}\s+from\s+([a-z][\w-]*)\s+to\s+([a-z][\w-]*)\s*$",
    re.IGNORECASE,
)
_PAID_BY = re.compile(r"\bpaid\s+by\s+([a-z][\w-]*)", re.IGNORECASE)
_SPLIT = re.compile(r"\bsplit\s+(.+)$", re.IGNORECASE)
_SHARE = re.compile(r"^([a-z][\w-]*)(?::(\d+))?$", re.IGNORECASE)


def strip_mentions(text: str) -> str:
    """Drop the leading '@ledger', keep '@ankit' later on as plain 'ankit'."""
    text = _LEADING_MENTIONS.sub("", text)
    return _INLINE_AT.sub(r"\1", text).strip(" ,:\n\t")


_strip_mentions = strip_mentions


def _parse_shares(text: str) -> dict[str, int] | None:
    text = text.strip()
    if text.lower() in {"equally", "evenly", "equal"}:
        return None
    shares: dict[str, int] = {}
    for token in re.split(r"[\s,]+", text):
        if not token or token.lower() == "and":
            continue
        m = _SHARE.match(token)
        if not m:
            raise CommandError(f"I can't read the share {token!r}. Try `priya:2 rahul:1`.")
        shares[m.group(1).lower()] = int(m.group(2) or 1)
    if not shares:
        raise CommandError("Say who to split between, e.g. `split priya rahul`.")
    return shares


def parse(text: str) -> Command:
    body = _strip_mentions(text)
    word = body.split(maxsplit=1)[0].lower().strip(",.!-") if body else "help"
    if word in {"balance", "balances", "settle", "history", "help"}:
        return Query("balance" if word == "balances" else word)
    if word in {"hello", "hi", "hey", "namaste", "introduce", "intro"}:
        return Query("help")  # a greeting (e.g. a template's kickoff) gets the how-to

    if m := _PAID.match(body):
        try:
            amount = parse_rupees(m.group(1))
        except MoneyError as exc:
            raise CommandError(str(exc)) from exc
        return AddPayment(amount, m.group(2).lower(), m.group(3).lower())

    if m := _ADD.match(body):
        try:
            amount = parse_rupees(m.group(1))
        except MoneyError as exc:
            raise CommandError(str(exc)) from exc
        rest = m.group(2)
        shares = None
        if s := _SPLIT.search(rest):
            shares = _parse_shares(s.group(1))
            rest = rest[: s.start()]
        paid_by = None
        if p := _PAID_BY.search(rest):
            paid_by = p.group(1).lower()
            rest = rest[: p.start()] + rest[p.end():]
        description = re.sub(r"^(for|on)\s+", "", rest.strip(), flags=re.IGNORECASE)
        return AddExpense(amount, description.strip(" ,.") or "Expense", paid_by, shares)

    raise CommandError("I didn't understand that. Say `help` to see what I can do.")
