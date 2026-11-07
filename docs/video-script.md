# Demo video script (target 2:30, hard limit 3:00)

**Cast:** Abhishek (Ankit's role), friend 1 (Rahul), friend 2 (Priya; can also tap for Ma). Each on their own phone in the Discord app, all in the family-circle server. Screen-record one laptop (Discord desktop) plus one phone recording.

**Before recording:** re-run the template with a fresh family name (e.g. `kumar`), so the rooms are clean, and add the friends' Discord handles to `circle.json`. Run `uv run carecircle run` and `uv run carecircle check` (12/12). Set `"not_own_entry": true`.

| Time | Scene | On screen | Caption |
|---|---|---|---|
| 0:00–0:12 | Hook | Three phones side by side, a messy chat | "Three siblings. Three cities. One Ma." |
| 0:12–0:25 | The room | Discord: `#kumar-circle`, `#kumar-ma`, 5 agents in the member list | "Switch turns this channel into a room people and agents share." |
| 0:25–0:55 | Prescription | Priya posts the photo → @meds replies → @pillbox card with 4 medicines → Rahul taps **Approve** | "Claude reads. Code checks every line. A sibling decides." |
| 0:55–1:05 | Ma's room | `#kumar-ma` shows the morning/night plan | "Ma only sees what she needs." |
| 1:05–1:30 | Visit | "@coordinator Ma has cardiology Friday 10 AM" → question card with each sibling → Rahul taps **Rahul** → Ma's room: "Rahul will take you" | "Nobody has to chase." |
| 1:30–1:55 | Money | Ankit: `@ledger add 2400 lab tests` → Ankit taps Approve → "nobody approves their own expense" → Rahul approves → `settle` | "Rules in code, not in a prompt." |
| 1:55–2:15 | Missed dose | `@pillbox remind now` → Ma's card → (cut) → "Nobody confirmed…" → "Can someone call Ma?" → Rahul taps **I'll call** | "Switch has no scheduler, so @pillbox keeps the clock." |
| 2:15–2:30 | Safety | Terminal: `carecircle check` → "Switch refuses a stray agent addressing @ledger" PASS | "Enforced by the Switch server." |
| 2:30–2:40 | Close | README top + `uv run carecircle demo` | "CareCircle. Built on Switch. Try it offline in one command." |

For the missed-dose scene, set `"timeout_minutes": 2` in `circle.json` so you can cut after 2 minutes.
