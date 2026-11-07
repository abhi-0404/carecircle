"""`uv run carecircle lock`: who may talk to @ledger and @pillbox, enforced by Switch.

Without a policy, anyone in a room may address an agent. These policies make
the Switch server itself refuse everyone except:

    @ledger   people, and @scribe (which hands over bills)
    @pillbox  people, and @meds (transcripts) and @coordinator (visits)

So if @meds were ever tricked into writing "@ledger add 50000 ...", Switch
drops it before @ledger sees it. Approvals stay with people either way: only a
person can tap a card.

Changing a policy is an owner/admin action, so this signs in to the server's
gateway: SWITCH_ADMIN_EMAIL / SWITCH_ADMIN_PASSWORD from .env, or, on a server
Switch Console runs on this computer, the admin login Console generated.
"""

from __future__ import annotations

import os
from pathlib import Path

import httpx

POLICIES: dict[str, list[str]] = {
    "ledger": ["scribe"],
    "pillbox": ["meds", "coordinator"],
}


def policy_for(agent_ids: list[str]) -> dict:
    """People anywhere; agents only when named. Platform senders stay denied."""
    rules = [{"users": "*", "agents": []}]
    if agent_ids:
        rules.append({"users": [], "agents": agent_ids})
    return {"rules": rules}


def _console_login() -> tuple[str, str] | None:
    env = Path(os.environ.get("APPDATA", "")) / "switchdash" / "local-switch-server" / "native" / "run" / "switch-core.env"
    if not env.exists():
        return None
    vals = dict(
        line.split("=", 1) for line in env.read_text(encoding="utf-8").splitlines() if "=" in line and not line.startswith("#")
    )
    if "GATEWAY_ADMIN_EMAIL" in vals and "GATEWAY_ADMIN_PASSWORD" in vals:
        return vals["GATEWAY_ADMIN_EMAIL"].strip(), vals["GATEWAY_ADMIN_PASSWORD"].strip()
    return None


def _login(http: httpx.Client) -> None:
    email, password = os.environ.get("SWITCH_ADMIN_EMAIL"), os.environ.get("SWITCH_ADMIN_PASSWORD")
    if not (email and password):
        found = _console_login()
        if not found:
            raise SystemExit("Set SWITCH_ADMIN_EMAIL and SWITCH_ADMIN_PASSWORD in .env (the Switch gateway admin).")
        email, password = found
    r = http.post("/gateway/auth/login", json={"email": email, "password": password})
    if r.status_code != 200:
        raise SystemExit(f"Gateway login failed ({r.status_code}).")


def _agents(http: httpx.Client) -> dict[str, str]:
    r = http.get("/gateway/agents")
    r.raise_for_status()
    data = r.json()
    rows = data if isinstance(data, list) else next((v for v in data.values() if isinstance(v, list)), [])
    return {a["name"]: a["id"] for a in rows if isinstance(a, dict) and a.get("name") and a.get("id")}


def lock(base_url: str, *, unlock: bool = False) -> None:
    with httpx.Client(base_url=base_url, timeout=30) as http:
        _login(http)
        ids = _agents(http)
        for name, allowed in POLICIES.items():
            if name not in ids:
                print(f"@{name}: not registered on this server; skipped")
                continue
            missing = [a for a in allowed if a not in ids]
            body = {"policy": None} if unlock else {"policy": policy_for([ids[a] for a in allowed if a in ids])}
            r = http.put(f"/gateway/agents/{ids[name]}/addressing-policy", json=body)
            r.raise_for_status()
            who = "anyone" if unlock else "people" + "".join(f", @{a}" for a in allowed if a in ids)
            note = f" (not found yet: {', '.join('@' + m for m in missing)})" if missing and not unlock else ""
            print(f"@{name}: only {who} may address it{note}" if not unlock else f"@{name}: open to anyone")
