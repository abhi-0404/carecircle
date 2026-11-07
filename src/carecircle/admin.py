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


def who(base_url: str, circle, agent_id: str, api_key: str) -> None:
    """Show the people who have posted in the family room, as Switch sees them.

    A tap or message only counts if the chat name below is in circle.json, so
    this is how to find the exact name to add for a friend.
    """
    import asyncio

    from carecircle.switch_client import SwitchAgent

    with httpx.Client(base_url=base_url, timeout=30) as http:
        _login(http)
        data = http.get("/gateway/rooms").json()
        rows = data if isinstance(data, list) else next((v for v in data.values() if isinstance(v, list)), [])
        family = [r for r in rows if str(r.get("name", "")).endswith("-circle") and not r.get("archived")]
    if not family:
        raise SystemExit("No family room (*-circle) found on this server.")

    async def read(room_id: str) -> dict:
        s = SwitchAgent(base_url, agent_id, api_key)
        try:
            return await s.op("read_context", {"room_id": room_id, "limit": 200})
        finally:
            await s.aclose()

    people: dict[str, str] = {}
    for room in family:
        ctx = asyncio.run(read(room["id"]))
        for thread in ctx.get("threads", []):
            for m in [thread["root"], *thread.get("replies", [])]:
                sender = m.get("sender", "")
                if sender.startswith(("@switch-agent-", "@switch-admin", "@switch-bridge-")) or not sender:
                    continue
                people[m.get("sender_name") or sender] = sender
    if not people:
        print("Nobody has posted in the family room yet. Ask each person to say hi there, then run this again.")
        return
    for name, pid in sorted(people.items()):
        member = circle.identify(name, pid)
        if member:
            print(f"OK   {name:<28} counts as {member.title()}")
        else:
            print(f"NEW  {name:<28} is not in circle.json. Add it:  uv run carecircle member <priya|rahul|...> {name}")


def _rows(data) -> list[dict]:
    if isinstance(data, list):
        return data
    return next((v for v in data.values() if isinstance(v, list)), []) if isinstance(data, dict) else []


def machine_online(http: httpx.Client) -> bool:
    """Is the computer that runs the Claude Code helpers (Switch Console) connected?"""
    r = http.get("/gateway/management/controllers")
    return r.status_code == 200 and any(c.get("state") == "online" for c in _rows(r.json()))


def reset(
    base_url: str,
    *,
    family: str,
    parent: str,
    parent_slug: str,
    siblings: str,
    bridge: str | None = None,
) -> None:
    """A clean slate for a fresh take: new rooms, new AI helpers, policies re-applied.

    Archives the family's two rooms (reversible), deletes the three Claude Code
    helpers (their conversations go with them), re-runs the one-click template
    and re-applies the addressing policies. @ledger and @pillbox keep running
    and join the new rooms on their own within ~15 seconds. Their old records
    belong to the archived rooms, so the new rooms start empty.
    """
    template = Path(__file__).resolve().parents[2] / "templates" / "carecircle.template.yaml"
    with httpx.Client(base_url=base_url, timeout=300) as http:
        _login(http)
        if not machine_online(http):  # check first: nothing below can be undone by hand quickly
            raise SystemExit(
                "Switch Console isn't connected, so the three AI helpers couldn't be recreated.\n"
                "Open Switch Console, wait about 20 seconds, then run this again. Nothing was changed."
            )
        # The three AI helpers are shared by name, so only one family can be live:
        # archive every earlier take (rooms in a "... care circle" group).
        # Archiving is reversible but leaves the Discord channel in place, so use a
        # new family name for each take (sharma2, sharma3, ...) to tell them apart.
        for room in _rows(http.get("/gateway/rooms").json()):
            if str(room.get("group_name", "")).endswith("care circle") and not room.get("archived"):
                http.post(f"/gateway/rooms/{room['id']}/archive").raise_for_status()
                print(f"archived #{room['name']}")
        ids = _agents(http)
        for name in ("meds", "scribe", "coordinator"):
            if name in ids:
                http.delete(f"/gateway/agents/{ids[name]}").raise_for_status()
                print(f"removed old @{name}")
        if bridge is None:
            apps = _rows(http.get("/gateway/collaborations").json())
            bridge = next((a.get("display_name") for a in apps if a.get("bridge_type") == "discord"), None)
        inputs = {"family": family, "parent": parent, "parent_slug": parent_slug, "siblings": siblings,
                  "ledger": "ledger", "pillbox": "pillbox"}
        if bridge:
            inputs["bridge"] = bridge
        print(f"creating fresh rooms and helpers on {bridge or 'the default chat app'} (about a minute)...")
        r = http.post(
            "/gateway/rooms/from-template-document",
            json={"template": template.read_text(encoding="utf-8"), "inputs": inputs, "template_name": "carecircle"},
        )
        if r.status_code != 201:
            raise SystemExit(f"The template run failed ({r.status_code}): {r.text[:400]}")
        made = [x["room_name"] for x in r.json().get("room", {}).get("rooms", [])]
        print("created: " + ", ".join(f"#{n}" for n in made))
    lock(base_url)
    print("Ready. @ledger and @pillbox join the new rooms within ~15 seconds.")


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
