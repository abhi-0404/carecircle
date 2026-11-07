"""Run CareCircle's code-only agents (@ledger, @pillbox) against a Switch server.

    uv run carecircle register ledger     # once per agent: saves its id and key to .env
    uv run carecircle register pillbox
    uv run carecircle run                 # runs every registered agent

Each agent gets one WebSocket per room it belongs to (rooms are discovered every
15 s), its approval-card answers are polled every 2 s, and @pillbox's reminder
clock ticks every 30 s.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys
from pathlib import Path

from carecircle.circle import Circle
from carecircle.env import load_env, require, set_env_values

log = logging.getLogger("carecircle")

AGENTS = {
    "ledger": dict(
        display_name="Ledger",
        description="Keeps the family's shared expenses. No AI: every amount is computed by code, "
        "and nothing is recorded until a sibling approves the card.",
    ),
    "pillbox": dict(
        display_name="Pillbox",
        description="Keeps the parent's medicine list and reminds them at dose times. No AI: it only "
        "accepts lines it can trace to the prescription, and a sibling approves every change.",
    ),
}


def _room_ids(result) -> list[str]:
    from carecircle.ledger_agent import _dicts

    ids = []
    for r in _dicts(result):
        rid = r.get("room_id") or r.get("id")
        if isinstance(rid, str) and not r.get("archived"):
            ids.append(rid)
    return ids


async def serve(name: str, agent, switch, cfg_path: Path | None = None) -> None:
    from carecircle.switch_client import RoomStream

    streams: dict[str, asyncio.Task] = {}

    async def watch_config() -> None:
        """Pick up edits to circle.json (a friend's chat name) without a restart."""
        last = cfg_path.stat().st_mtime if cfg_path and cfg_path.exists() else None
        while True:
            await asyncio.sleep(3)
            try:
                now = cfg_path.stat().st_mtime if cfg_path and cfg_path.exists() else None
                if now != last:
                    last = now
                    agent.circle = Circle.load(cfg_path)
                    log.info("@%s reloaded %s: %s", name, cfg_path.name, ", ".join(agent.circle.names))
            except Exception as exc:  # noqa: BLE001 - keep the old list if the file is mid-edit
                log.warning("@%s could not reload %s: %s", name, cfg_path, exc)

    async def discover() -> None:
        while True:
            try:
                for rid in _room_ids(await switch.op("list_rooms")):
                    if rid in streams:
                        continue
                    stream = RoomStream(
                        switch,
                        rid,
                        agent.handle_message,
                        start_from=agent.cursor_of(rid),
                        on_cursor=lambda c, rid=rid: agent.remember_cursor(rid, c),
                    )
                    agent.connections[rid] = stream.connection_id
                    streams[rid] = asyncio.create_task(stream.run())
                    log.info("@%s listening in room %s", name, rid)
            except Exception as exc:  # noqa: BLE001
                log.warning("@%s could not list rooms: %s", name, exc)
            await asyncio.sleep(15)

    async def outcomes() -> None:
        while True:
            try:
                await agent.check_outcomes()
            except Exception as exc:  # noqa: BLE001
                log.warning("@%s could not read card answers: %s", name, exc)
            await asyncio.sleep(2)

    async def clock() -> None:
        while True:
            await asyncio.sleep(30)
            try:
                await agent.tick()
            except Exception as exc:  # noqa: BLE001
                log.warning("@%s clock: %s", name, exc)

    loops = [discover(), outcomes(), watch_config()]
    if hasattr(agent, "tick"):
        loops.append(clock())
    await asyncio.gather(*loops)


def _config_path() -> Path:
    cfg = Path(os.environ.get("CARECIRCLE_CONFIG", "circle.json"))
    return cfg if cfg.exists() else Path("circle.example.json")


def _config() -> tuple[str, Circle, Path]:
    base = os.environ.get("SWITCH_URL", "http://127.0.0.1:55618")
    return base, Circle.load(_config_path()), Path(os.environ.get("CARECIRCLE_DATA", "data"))


async def _register(name: str, overwrite: bool) -> None:
    from carecircle.switch_client import SwitchAgent

    base, _, _ = _config()
    spec = AGENTS[name]
    resp = await SwitchAgent.register(
        base,
        require("SWITCH_REGISTRATION_KEY"),
        name=name,
        display_name=spec["display_name"],
        description=spec["description"],
        overwrite=overwrite,
    )
    prefix = name.upper()
    set_env_values(Path(".env"), {f"{prefix}_AGENT_ID": resp["id"], f"{prefix}_API_KEY": resp["api_key"]})
    print(f"Registered @{name} (id {resp['id']}). Its key is saved in .env.")
    print("An agent can't change its own permissions: let your family address it from Switch Console,")
    print("then add it to the family's rooms and run:  uv run carecircle run")


async def _run(only: list[str]) -> None:
    from carecircle.ledger_agent import LedgerAgent
    from carecircle.pillbox_agent import PillboxAgent
    from carecircle.switch_client import SwitchAgent

    base, circle, data = _config()
    jobs, clients = [], []
    for name, cls in (("ledger", LedgerAgent), ("pillbox", PillboxAgent)):
        if only and name not in only:
            continue
        aid, key = os.environ.get(f"{name.upper()}_AGENT_ID"), os.environ.get(f"{name.upper()}_API_KEY")
        if not (aid and key):
            log.info("@%s is not registered here; skipping (uv run carecircle register %s)", name, name)
            continue
        switch = SwitchAgent(base, aid, key)
        clients.append(switch)
        jobs.append(serve(name, cls(switch, circle, data), switch, _config_path()))
        log.info("@%s is running against %s for %s", name, base, ", ".join(circle.names))
    if not jobs:
        raise SystemExit("No agent is registered. Run: uv run carecircle register ledger")
    try:
        await asyncio.gather(*jobs)
    finally:
        for c in clients:
            await c.aclose()


def main(argv: list[str] | None = None) -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    load_env()
    p = argparse.ArgumentParser(prog="carecircle")
    sub = p.add_subparsers(dest="cmd", required=True)
    reg = sub.add_parser("register", help="register a code-only agent with the Switch server (once)")
    reg.add_argument("name", choices=sorted(AGENTS))
    reg.add_argument("--overwrite", action="store_true", help="re-issue the key if it exists")
    run = sub.add_parser("run", help="run the registered agents")
    run.add_argument("--only", nargs="*", default=[], choices=sorted(AGENTS))
    sub.add_parser("demo", help="play the whole story offline (no Switch, no keys)")
    lk = sub.add_parser("lock", help="let only people and the right agents address @ledger and @pillbox")
    lk.add_argument("--unlock", action="store_true", help="open them to anyone again")
    sub.add_parser("check", help="check CareCircle on the live Switch server")
    sub.add_parser("who", help="show who has posted in the family room and whether they count")
    rs = sub.add_parser("reset", help="fresh rooms and AI helpers for a clean take (archives the old rooms)")
    rs.add_argument("--yes", action="store_true", help="confirm: archive the family's rooms and recreate them")
    rs.add_argument("--family", default="sharma", help="lowercase family name for the room names")
    rs.add_argument("--parent", default="Ma")
    rs.add_argument("--slug", default="ma", help="short lowercase name for the parent's room")
    rs.add_argument("--siblings", default=None, help='e.g. "Abhishek, Priya, Rahul" (default: from circle.json)')
    rs.add_argument("--bridge", default=None, help="chat app name in Switch (default: the Discord one)")
    mb = sub.add_parser("member", help="add a family member, or another chat name for one (no restart needed)")
    mb.add_argument("name", help="the family member, e.g. priya")
    mb.add_argument("aliases", nargs="+", help="their chat username(s), as `carecircle who` shows them")
    args = p.parse_args(argv)
    if args.cmd == "reset":
        from carecircle.admin import reset

        if not args.yes:
            raise SystemExit("This archives the family's rooms and recreates them and the 3 AI helpers. "
                             "Add --yes to go ahead.")
        circle = Circle.load(_config_path())
        reset(os.environ.get("SWITCH_URL", "http://127.0.0.1:55618"), family=args.family, parent=args.parent,
              parent_slug=args.slug, siblings=args.siblings or ", ".join(n.title() for n in circle.names),
              bridge=args.bridge)
        return
    if args.cmd == "member":
        from carecircle.circle import add_member

        cfg = _config_path()
        members = add_member(cfg, args.name, args.aliases)
        print(f"{cfg.name}: " + "; ".join(f"{k} = {', '.join(v) or '(no chat names)'}" for k, v in members.items()))
        print("Running agents pick this up within a few seconds; no restart needed.")
        return
    if args.cmd == "who":
        from carecircle.admin import who

        require("LEDGER_AGENT_ID")
        who(os.environ.get("SWITCH_URL", "http://127.0.0.1:55618"), Circle.load(_config_path()),
            os.environ["LEDGER_AGENT_ID"], os.environ["LEDGER_API_KEY"])
        return
    if args.cmd == "check":
        from carecircle.check import run as check

        raise SystemExit(0 if check(os.environ.get("SWITCH_URL", "http://127.0.0.1:55618")) else 1)
    if args.cmd == "lock":
        from carecircle.admin import lock

        lock(os.environ.get("SWITCH_URL", "http://127.0.0.1:55618"), unlock=args.unlock)
        return
    if args.cmd == "demo":
        from carecircle.demo import main as demo_main

        demo_main()
        return
    try:
        asyncio.run(_register(args.name, args.overwrite) if args.cmd == "register" else _run(args.only))
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
