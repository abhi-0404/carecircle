"""The family's shared expense book. Plain code: no model ever does the maths.

An expense is split by agreed shares (equal by default, or e.g. 2:1:1 when one
sibling has agreed to carry more). Balances are positive for whoever is owed.
Settle-up produces the fewest transfers that clear every balance.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from carecircle.money import format_rupees


class LedgerError(ValueError):
    pass


@dataclass(frozen=True)
class Expense:
    id: int
    description: str
    amount: int  # paise
    paid_by: str
    shares: dict[str, int]  # member -> weight
    approved_by: str | None = None
    created_at: str = ""

    def owed(self) -> dict[str, int]:
        return split(self.amount, self.shares)


@dataclass(frozen=True)
class Payment:
    """Money one member handed another to settle up."""

    id: int
    frm: str
    to: str
    amount: int
    approved_by: str | None = None
    created_at: str = ""


@dataclass(frozen=True)
class Transfer:
    frm: str
    to: str
    amount: int

    def __str__(self) -> str:
        return f"{self.frm.title()} → {self.to.title()}: {format_rupees(self.amount)}"


def split(amount: int, shares: dict[str, int]) -> dict[str, int]:
    """Divide `amount` paise by weight. Parts always add up to `amount` exactly.

    Leftover paise go one each to the largest fractional remainders, ties broken
    by the order the members were listed, so the result never depends on luck.
    """
    if not shares:
        raise LedgerError("Nobody to split between.")
    if any(w <= 0 for w in shares.values()):
        raise LedgerError("Every share must be a positive whole number.")
    total = sum(shares.values())
    base = {m: amount * w // total for m, w in shares.items()}
    left = amount - sum(base.values())
    order = sorted(
        shares, key=lambda m: (-(amount * shares[m] % total), list(shares).index(m))
    )
    for m in order[:left]:
        base[m] += 1
    return base


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass
class Ledger:
    members: list[str]
    expenses: list[Expense] = field(default_factory=list)
    payments: list[Payment] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.members = [m.lower() for m in self.members]
        if len(set(self.members)) != len(self.members) or not self.members:
            raise LedgerError("Members must be a non-empty list of unique names.")

    # -- changes ---------------------------------------------------------
    def _next_id(self) -> int:
        ids = [e.id for e in self.expenses] + [p.id for p in self.payments]
        return max(ids, default=0) + 1

    def _member(self, name: str) -> str:
        n = name.lower()
        if n not in self.members:
            raise LedgerError(
                f"{name!r} is not in the circle ({', '.join(self.members)})."
            )
        return n

    def propose_expense(
        self,
        amount: int,
        description: str,
        paid_by: str,
        shares: dict[str, int] | None = None,
    ) -> Expense:
        """Build (but do not record) an expense, validating every name."""
        if amount <= 0:
            raise LedgerError("An amount must be more than zero.")
        payer = self._member(paid_by)
        weights = shares or {m: 1 for m in self.members}
        weights = {self._member(m): w for m, w in weights.items()}
        split(amount, weights)  # validates the weights
        return Expense(
            id=self._next_id(),
            description=description.strip() or "Expense",
            amount=amount,
            paid_by=payer,
            shares=weights,
        )

    def propose_payment(self, frm: str, to: str, amount: int) -> Payment:
        a, b = self._member(frm), self._member(to)
        if a == b:
            raise LedgerError("Someone can't pay themselves.")
        if amount <= 0:
            raise LedgerError("An amount must be more than zero.")
        return Payment(id=self._next_id(), frm=a, to=b, amount=amount)

    def record(self, item: Expense | Payment, approved_by: str) -> Expense | Payment:
        """Commit a proposal once a person has approved it."""
        stamped = type(item)(
            **{**asdict(item), "approved_by": approved_by, "created_at": _now(), "id": self._next_id()}
        )
        (self.expenses if isinstance(stamped, Expense) else self.payments).append(stamped)
        return stamped

    # -- reading ---------------------------------------------------------
    def balances(self) -> dict[str, int]:
        """Positive: the circle owes this member. Negative: they owe the circle."""
        bal = {m: 0 for m in self.members}
        for e in self.expenses:
            bal[e.paid_by] += e.amount
            for m, part in e.owed().items():
                bal[m] -= part
        for p in self.payments:
            bal[p.frm] += p.amount
            bal[p.to] -= p.amount
        return bal

    def settle_up(self) -> list[Transfer]:
        """The fewest transfers (greedy, largest first) that zero every balance."""
        bal = self.balances()
        debtors = sorted(((-v, m) for m, v in bal.items() if v < 0), reverse=True)
        creditors = sorted(((v, m) for m, v in bal.items() if v > 0), reverse=True)
        debtors = [[v, m] for v, m in debtors]
        creditors = [[v, m] for v, m in creditors]
        out: list[Transfer] = []
        i = j = 0
        while i < len(debtors) and j < len(creditors):
            pay = min(debtors[i][0], creditors[j][0])
            out.append(Transfer(debtors[i][1], creditors[j][1], pay))
            debtors[i][0] -= pay
            creditors[j][0] -= pay
            if debtors[i][0] == 0:
                i += 1
            if creditors[j][0] == 0:
                j += 1
        return out

    def describe(self, e: Expense) -> str:
        parts = ", ".join(f"{m.title()} {format_rupees(v)}" for m, v in e.owed().items())
        return (
            f"{e.description}: {format_rupees(e.amount)} paid by {e.paid_by.title()}"
            f" — split {parts}"
        )

    def render_markdown(self) -> str:
        """The `expense-ledger` room document."""
        lines = ["# Expense ledger", "", "## Balances", ""]
        for m, v in self.balances().items():
            state = "is owed" if v > 0 else "owes" if v < 0 else "is square"
            amount = f" {format_rupees(abs(v))}" if v else ""
            lines.append(f"- **{m.title()}** {state}{amount}")
        transfers = self.settle_up()
        lines += ["", "## To settle up", ""]
        lines += [f"- {t}" for t in transfers] or ["- Everyone is square."]
        lines += ["", "## History", ""]
        items = sorted(self.expenses + self.payments, key=lambda x: x.id)
        if not items:
            lines.append("- Nothing recorded yet.")
        for x in items:
            who = f" (approved by {x.approved_by})" if x.approved_by else ""
            if isinstance(x, Expense):
                lines.append(f"- #{x.id} {self.describe(x)}{who}")
            else:
                lines.append(
                    f"- #{x.id} {x.frm.title()} paid {x.to.title()} "
                    f"{format_rupees(x.amount)}{who}"
                )
        return "\n".join(lines) + "\n"

    # -- storage ---------------------------------------------------------
    def to_json(self) -> str:
        return json.dumps(
            {
                "members": self.members,
                "expenses": [asdict(e) for e in self.expenses],
                "payments": [asdict(p) for p in self.payments],
            },
            indent=2,
            ensure_ascii=False,
        )

    @classmethod
    def from_json(cls, text: str) -> "Ledger":
        d = json.loads(text)
        return cls(
            members=d["members"],
            expenses=[Expense(**e) for e in d.get("expenses", [])],
            payments=[Payment(**p) for p in d.get("payments", [])],
        )

    def save(self, path: Path) -> None:
        tmp = path.with_suffix(".tmp")
        tmp.write_text(self.to_json(), encoding="utf-8")
        tmp.replace(path)

    @classmethod
    def load(cls, path: Path, members: list[str]) -> "Ledger":
        if path.exists():
            return cls.from_json(path.read_text(encoding="utf-8"))
        return cls(members=members)
