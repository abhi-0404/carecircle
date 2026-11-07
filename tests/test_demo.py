"""The offline demo judges run must keep telling the whole story."""

import asyncio

from carecircle.demo import events, story


def test_offline_demo_tells_the_whole_story():
    lines: list[str] = []
    asyncio.run(story(lines.append))
    text = "\n".join(lines)
    for expected in [
        "nobody approves their own expense",
        "✅ Recorded #1: ₹2,400 for lab tests — approved by Rahul.",
        "Cousin Vikram isn't in the family circle",
        "✅ Added 4 medicine(s) to Ma's list — approved by Priya.",
        "[#sharma-ma] @pillbox: 📋 Ma, here is your updated medicine plan:",
        "[#sharma-ma] @pillbox: 📅 Ma, your next visit: **Friday 13 Nov, 10:00 AM**",
        "🌅 Ma, time for your morning medicines",
        "⚠️ Nobody confirmed Ma's morning medicines",
        "📞 Rahul is calling Ma.",
        "Priya → Ankit: ₹800",
    ]:
        assert expected in text, expected


def test_replay_events_say_what_is_real_and_what_is_scripted():
    ev = asyncio.run(events())
    assert {e["t"] for e in ev} == {"scene", "say", "card", "tap", "note"}
    cards = [e for e in ev if e["t"] == "card"]
    assert all(c["real"] for c in cards if c["who"] in ("ledger", "pillbox"))  # produced by the real code
    assert any(c["who"] == "coordinator" and c["real"] is False for c in cards)  # the Claude agent is scripted
    assert all(e["real"] is False for e in ev if e["t"] == "tap")  # people's taps are scripted input
