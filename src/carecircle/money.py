"""Rupee amounts as whole paise, so no money maths ever touches a float."""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation

_AMOUNT = re.compile(
    r"^(?:₹|rs\.?|inr)?\s*(\d{1,3}(?:,\d{2,3})*|\d+)(?:\.(\d{1,2}))?$",
    re.IGNORECASE,
)


class MoneyError(ValueError):
    pass


def parse_rupees(text: str) -> int:
    """'₹2,400', 'Rs 2400', '2400.5' -> paise. Rejects zero, negatives and junk."""
    m = _AMOUNT.match(text.strip())
    if not m:
        raise MoneyError(f"Not an amount: {text!r}")
    whole = m.group(1).replace(",", "")
    frac = (m.group(2) or "").ljust(2, "0")
    try:
        paise = int(Decimal(whole) * 100) + int(frac or 0)
    except InvalidOperation as exc:  # pragma: no cover - the regex already guards
        raise MoneyError(f"Not an amount: {text!r}") from exc
    if paise <= 0:
        raise MoneyError("An amount must be more than zero.")
    return paise


def format_rupees(paise: int) -> str:
    """Paise -> '₹2,400' or '₹1,20,000.50', with Indian digit grouping."""
    sign = "-" if paise < 0 else ""
    rupees, rest = divmod(abs(paise), 100)
    digits = str(rupees)
    if len(digits) > 3:
        head, tail = digits[:-3], digits[-3:]
        groups = []
        while len(head) > 2:
            groups.insert(0, head[-2:])
            head = head[:-2]
        if head:
            groups.insert(0, head)
        digits = ",".join(groups + [tail])
    return f"{sign}₹{digits}" + (f".{rest:02d}" if rest else "")
