"""Who is in the family circle, and how to recognise them from a chat name."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

# A chat person's Switch participant id looks like
#   @switch-discord-<bridge uuid>-<platform username>:<server>
# Switch says to treat ids as opaque, so this is only a best-effort way to show
# a friendly name; anything that doesn't fit falls back to the raw localpart.
_PLATFORM_USER = re.compile(
    r"^switch-[a-z]+-[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}-(.+)$"
)


def chat_name(participant: str) -> str:
    """'@switch-discord-<uuid>-abhishekkumar2672:localhost' -> 'abhishekkumar2672'."""
    local = participant[1:].split(":", 1)[0] if participant.startswith("@") else participant
    m = _PLATFORM_USER.match(local)
    return m.group(1) if m else local


@dataclass(frozen=True)
class Circle:
    parent: str
    members: dict[str, tuple[str, ...]]  # canonical name -> chat names / aliases
    # Approval rules, enforced in code (never left to a model):
    people_only: bool = True  # only a recognised family member's tap counts
    not_own_entry: bool = False  # nobody approves their own expense; payments are
    #                              confirmed by the person who received the money

    @classmethod
    def from_dict(cls, d: dict) -> "Circle":
        members = {
            name.lower(): tuple(a.casefold() for a in aliases)
            for name, aliases in d["members"].items()
        }
        rules = d.get("approval", {})
        return cls(
            parent=d.get("parent", "Ma"),
            members=members,
            people_only=bool(rules.get("people_only", True)),
            not_own_entry=bool(rules.get("not_own_entry", False)),
        )

    @classmethod
    def load(cls, path: Path) -> "Circle":
        return cls.from_dict(json.loads(path.read_text(encoding="utf-8")))

    @property
    def names(self) -> list[str]:
        return list(self.members)

    def identify(self, *candidates: str | None) -> str | None:
        """Map a chat display name or participant id to a member, or None."""
        keys: list[str] = []
        for c in candidates:
            if not c:
                continue
            c = c.casefold().strip()
            keys.append(c)
            if c.startswith("@") and ":" in c:  # a Switch participant id
                keys.append(c[1:].split(":", 1)[0])
                keys.append(chat_name(c))
            keys.append(c.split()[0] if c.split() else c)
        for name, aliases in self.members.items():
            if any(k == name or k in aliases for k in keys):
                return name
        return None
