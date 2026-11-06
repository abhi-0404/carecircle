"""Turn a transcribed prescription into a parent's daily schedule, and refuse
anything the prescription doesn't actually say.

The split of work is deliberate:

* a model (the @meds agent) only *transcribes* the photo: for every line it
  copies the text verbatim and fills in fields (name, strength, dose, ...);
* this module, plain code, decides what is accepted. A field that cannot be
  found in its own verbatim line is treated as a model mistake and the line is
  not added. Dose codes (1-0-1, BD, TDS, HS, SOS...) become clock times from a
  fixed table, never from a model;
* a person approves the result on a card before anything reaches the schedule.

Nothing here gives medical advice or changes a dose. Unclear lines are flagged
with "ask the doctor or pharmacist", and left out.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from difflib import SequenceMatcher

SLOTS = ("morning", "afternoon", "evening", "night")
SLOT_TIME = {"morning": "8:00 AM", "afternoon": "2:00 PM", "evening": "6:00 PM", "night": "9:00 PM"}
SLOT_ICON = {"morning": "🌅", "afternoon": "☀️", "evening": "🌇", "night": "🌙"}

# Prescription shorthand -> doses per slot (quantity 1 unless the line says otherwise).
_CODES: dict[str, dict[str, float]] = {}
for _words, _slots in [
    (("od", "qd", "once daily", "once a day", "daily"), {"morning": 1}),
    (("bd", "bid", "twice daily", "twice a day"), {"morning": 1, "night": 1}),
    (("tds", "tid", "thrice daily", "three times a day"), {"morning": 1, "afternoon": 1, "night": 1}),
    (("qid", "qds", "four times a day"), {"morning": 1, "afternoon": 1, "evening": 1, "night": 1}),
    (("hs", "at bedtime", "at night", "bedtime"), {"night": 1}),
]:
    for _w in _words:
        _CODES[_w] = _slots
_AS_NEEDED = ("sos", "prn", "as needed", "when needed", "when required", "if needed")

_QTY = r"(\d+(?:\.\d+)?|\d+/\d+|½)"
_PATTERN = re.compile(rf"^\s*{_QTY}\s*-\s*{_QTY}\s*-\s*{_QTY}(?:\s*-\s*{_QTY})?\s*$")
_LEADING_QTY = re.compile(
    r"^\s*(\d+(?:\.\d+)?|\d+/\d+|½)\s*(ml|drops?|puffs?|tabs?|tablets?|caps?|capsules?)?\s+(.+)$",
    re.IGNORECASE,
)
_STRENGTH = re.compile(r"(\d+(?:\.\d+)?)\s*(mcg|µg|mg|g|ml|iu|%)", re.IGNORECASE)
_DURATION = re.compile(r"(\d+)\s*(days?|d\b|weeks?|wks?|months?|mo\b)", re.IGNORECASE)
_ONGOING = ("continue", "cont.", "long term", "lifelong", "till next visit")

_UNIT_FOR_FORM = {
    "tablet": ("tablet", "tablets"),
    "capsule": ("capsule", "capsules"),
    "syrup": ("ml", "ml"),
    "drops": ("drop", "drops"),
    "inhaler": ("puff", "puffs"),
}

_FORM_WORDS = {
    "tablet": ("tab", "tabs", "tablet", "tablets"),
    "capsule": ("cap", "caps", "capsule", "capsules"),
    "syrup": ("syp", "syr", "syrup", "suspension", "susp"),
    "drops": ("drop", "drops", "gtt"),
    "inhaler": ("inhaler", "puff", "puffs", "inh"),
}


def normalize_form(form: str | None, verbatim: str = "") -> str:
    """'Tab.' / 'tabs' -> 'tablet'; unknown -> read the line's first word; else 'tablet'."""
    for text in (form or "", verbatim.split(" ", 1)[0] if verbatim else ""):
        word = re.sub(r"[^a-z]", "", text.lower())
        for canon, words in _FORM_WORDS.items():
            if word in words:
                return canon
    return (form or "tablet").strip().lower() or "tablet"


MAX_DOSES_PER_DAY = 4
NOT_ADVICE = (
    "CareCircle copies what the prescription says; it is not medical advice. "
    "If anything looks wrong, ask the doctor or pharmacist."
)


def _qty(text: str) -> float:
    text = text.strip()
    if text == "½":
        return 0.5
    if "/" in text:
        a, b = text.split("/", 1)
        return int(a) / int(b)
    return float(text)


def _norm(text: str) -> str:
    """Lowercase, letters and digits only: '1 - 0 - 1' and '1-0-1' compare equal."""
    return re.sub(r"[^a-z0-9½]", "", text.lower())


class DoseError(ValueError):
    pass


def parse_dose(dose: str) -> tuple[dict[str, float], bool]:
    """'1-0-1' / '1-0-0-1' / 'BD' / '5 ml TDS' / 'SOS' -> ({slot: qty}, as_needed)."""
    d = dose.strip().lower().rstrip(".")
    if not d:
        raise DoseError("no dose given")
    if any(d == w or d.endswith(" " + w) for w in _AS_NEEDED):
        return {}, True
    m = _PATTERN.match(d)
    if m:
        parts = [p for p in m.groups() if p is not None]
        names = ("morning", "afternoon", "night") if len(parts) == 3 else SLOTS
        slots = {n: _qty(p) for n, p in zip(names, parts) if _qty(p) > 0}
        if not slots:
            raise DoseError("every dose in the pattern is zero")
        return slots, False
    qty = 1.0
    lm = _LEADING_QTY.match(d)
    if lm and lm.group(3) in _CODES:
        qty, d = _qty(lm.group(1)), lm.group(3)
    if d in _CODES:
        return {slot: qty for slot in _CODES[d]}, False
    raise DoseError(f"can't read the dose {dose!r}")


def parse_duration(text: str | None) -> int | None:
    """'x 30 days' -> 30, '2 weeks' -> 14, '1 month' -> 30; ongoing/unknown -> None."""
    if not text:
        return None
    t = text.lower()
    if any(w in t for w in _ONGOING):
        return None
    m = _DURATION.search(t)
    if not m:
        return None
    n, unit = int(m.group(1)), m.group(2).lower()
    if unit.startswith("w"):
        return n * 7
    if unit.startswith("mo"):
        return n * 30
    return n


@dataclass(frozen=True)
class Med:
    name: str
    strength: str | None
    form: str
    slots: dict[str, float]
    as_needed: bool
    duration_days: int | None
    timing: str | None
    verbatim: str

    def per_day(self) -> float:
        return sum(self.slots.values())

    def _amount(self, qty: float) -> str:
        one, many = _UNIT_FOR_FORM.get(self.form, ("dose", "doses"))
        q = "½" if qty == 0.5 else (f"{qty:g}")
        return f"{q} {one if qty <= 1 else many}"

    def label(self) -> str:
        return f"{self.name} {self.strength}" if self.strength else self.name

    def describe(self) -> str:
        if self.as_needed:
            when = "only when needed"
        else:
            when = ", ".join(f"{self._amount(q)} {s}" for s, q in self.slots.items())
        extra = []
        if self.duration_days:
            extra.append(f"{self.duration_days} days")
        if self.timing:
            extra.append(self.timing)
        return f"{self.label()} — {when}" + (f" · {' · '.join(extra)}" if extra else "")


@dataclass
class CheckResult:
    accepted: list[Med] = field(default_factory=list)
    rejected: list[tuple[str, str]] = field(default_factory=list)  # (verbatim, why)
    flags: list[str] = field(default_factory=list)
    photo_checked: bool = False


_TOKEN = re.compile(r"\d+/\d+|\d+(?:\.\d+)?|½|[a-zµ%]+")


def _tokens(text: str) -> list[str]:
    """'Tab. Amlodipine 5mg 1-0-1' -> ['tab', 'amlodipine', '5', 'mg', '1', '0', '1']."""
    return _TOKEN.findall(text.lower())


def _traceable(value: str, verbatim: str) -> bool:
    """A field counts only if its words and numbers appear, in order and side by
    side, in the line it was read from. So '10 mg' is not found in '5mg 1-0-1'
    even though the characters '1', '0', 'm', 'g' all occur there."""
    needle, hay = _tokens(value), _tokens(verbatim)
    if not needle:
        return False
    return any(hay[i : i + len(needle)] == needle for i in range(len(hay) - len(needle) + 1))


def _seen_in_photo(verbatim: str, ocr_lines: list[str]) -> bool:
    target = _norm(verbatim)
    best = max((SequenceMatcher(None, target, _norm(o)).ratio() for o in ocr_lines), default=0)
    return best >= 0.6


def check_prescription(transcript: dict, ocr_text: str | None = None) -> CheckResult:
    """Accept only lines whose fields can be traced to their own verbatim text.

    `transcript` is what the @meds agent produced:
        {"lines": [{"verbatim", "name", "strength", "form", "dose", "duration", "timing"}]}
    `ocr_text`, when given, is an independent read of the photo; a line it
    doesn't contain is held back too.
    """
    result = CheckResult(photo_checked=ocr_text is not None)
    ocr_lines = [ln for ln in (ocr_text or "").splitlines() if ln.strip()]
    seen: dict[str, str] = {}
    for line in transcript.get("lines", []):
        verbatim = str(line.get("verbatim", "")).strip()
        name = str(line.get("name", "")).strip()
        strength = (str(line.get("strength") or "").strip()) or None
        dose = str(line.get("dose", "")).strip()
        if not verbatim or not name:
            result.rejected.append((verbatim or "(empty line)", "the line or the medicine name is missing"))
            continue
        if not _traceable(name, verbatim):
            result.rejected.append((verbatim, f"the name {name!r} isn't in this line of the prescription"))
            continue
        if strength and not _traceable(strength, verbatim):
            result.rejected.append((verbatim, f"the strength {strength!r} isn't in this line"))
            continue
        if not dose or not _traceable(dose, verbatim):
            result.rejected.append((verbatim, "the dose isn't written in this line — ask the doctor or pharmacist"))
            continue
        if ocr_lines and not _seen_in_photo(verbatim, ocr_lines):
            result.rejected.append((verbatim, "couldn't confirm this line against the photo itself"))
            continue
        try:
            slots, as_needed = parse_dose(dose)
        except DoseError as exc:
            result.rejected.append((verbatim, f"{exc} — ask the doctor or pharmacist"))
            continue
        if strength:
            sm = _STRENGTH.search(strength)
            strength = f"{sm.group(1)} {sm.group(2).lower()}" if sm else strength
        med = Med(
            name=name.title() if name.islower() else name,
            strength=strength,
            form=normalize_form(line.get("form"), verbatim),
            slots=slots,
            as_needed=as_needed,
            duration_days=parse_duration(line.get("duration") or verbatim),
            timing=(str(line.get("timing") or "").strip() or None),
            verbatim=verbatim,
        )
        key = med.name.lower()
        if key in seen:
            result.flags.append(
                f"{med.name} is written twice ({seen[key]} and {verbatim}) — check with the doctor."
            )
        seen[key] = verbatim
        if med.per_day() > MAX_DOSES_PER_DAY:
            result.flags.append(f"{med.label()} is {med.per_day():g} doses a day — please double-check.")
        if not med.strength:
            result.flags.append(f"No strength is written for {med.name}.")
        result.accepted.append(med)
    if not result.photo_checked:
        result.flags.append("The photo wasn't read a second time, so please compare the list with it.")
    return result


def card_text(result: CheckResult, parent: str) -> tuple[str, str]:
    n = len(result.accepted)
    title = f"Add {n} medicine{'s' if n != 1 else ''} to {parent}'s schedule?"
    lines = [f"• {m.describe()}" for m in result.accepted]
    if result.rejected:
        lines.append("")
        lines.append("Not added (kept out on purpose):")
        lines += [f"✗ {v} — {why}" for v, why in result.rejected]
    if result.flags:
        lines.append("")
        lines += [f"⚠️ {f}" for f in result.flags]
    lines += ["", NOT_ADVICE]
    return title, "\n".join(lines)


def schedule_markdown(meds: list[Med], parent: str) -> str:
    """Big, plain text for the parent's room: what to take, when."""
    out = [f"# {parent}'s medicines", ""]
    for slot in SLOTS:
        due = [m for m in meds if slot in m.slots]
        if not due:
            continue
        out.append(f"## {SLOT_ICON[slot]} {slot.title()} — {SLOT_TIME[slot]}")
        for m in due:
            how = f" ({m.timing})" if m.timing else ""
            out.append(f"- **{m.label()}** — {m._amount(m.slots[slot])}{how}")
        out.append("")
    as_needed = [m for m in meds if m.as_needed]
    if as_needed:
        out.append("## 🩹 Only when needed")
        out += [f"- **{m.label()}** — {m.timing or 'as the doctor said'}" for m in as_needed]
        out.append("")
    out.append(f"_{NOT_ADVICE}_")
    return "\n".join(out) + "\n"
