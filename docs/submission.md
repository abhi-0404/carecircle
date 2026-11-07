# Submission answer bank

I couldn't open the submission form (it needs your login), so I don't know its exact fields. Below are answers at several lengths; copy whichever fits. Replace `VIDEO_LINK`, `BLOG_LINK`, `X_LINK`, `LINKEDIN_LINK` once you have them (send me the links and I'll fill these in).

## Basics

| Field | Answer |
|---|---|
| **Project name** | CareCircle |
| **Track** | Track 02: Best Personal or Creative Workflow |
| **Also entering** | Best Blog (side track); #HowISwitch social posts. *Not* Code with Wispr unless you built it by voice with Wispr Flow and have the Insights scorecard. |
| **Repository** | https://github.com/abhi-0404/carecircle (public). There is no LICENSE file yet; if the form asks for a license, tell me which one (MIT is the usual choice) and I'll add it. |
| **Demo video** | VIDEO_LINK (under 3 minutes) |
| **Blog** | BLOG_LINK |
| **Social posts** | X_LINK · LINKEDIN_LINK |
| **Team** | Solo: Abhishek Kumar (GitHub: abhi-0404) |
| **Built with** | Switch (Rooms 0.31, Console 0.40.1), Claude Code (three agents), Python 3.12 with uv, httpx, websockets, Discord, GitHub Actions |

## Tagline (under 100 characters)

```text
AI reads, code checks, siblings decide: shared care for an aging parent, built on Switch.
```

## Short description (about 280 characters)

```text
CareCircle is a Discord room where siblings in different cities share the care of an aging parent. Claude agents read prescriptions and plan visits, plain-code agents check every medicine line and keep the money, and a sibling taps Approve on a Switch card before anything changes.
```

## Long description

```text
THE PROBLEM
Three siblings, three cities, one mother who lives alone. Her care runs on a family chat: the prescription is a blurry photo three days up, nobody is sure who is taking her to the cardiologist on Friday, and one sibling has quietly stopped asking to be paid back for the lab tests. Many families recognise this; in the US alone 63 million people care for a family member, six in ten of them while holding a job (AARP, 2025).

WHAT I BUILT
CareCircle puts five agents in one Discord server with two rooms: the family's room and a calm room just for Ma.
 • @meds (Claude Code) reads a prescription photo and copies every line verbatim.
 • @pillbox (plain Python, no AI) checks each field against the line it came from, keeps Ma's medicine list, sends a "Taken?" card at dose time and escalates a missed dose to the family.
 • @coordinator (Claude Code) asks who takes Ma to each visit, on a card with one button per sibling.
 • @scribe (Claude Code) turns visit notes into a plain-language care log and hands bills to @ledger.
 • @ledger (plain Python, no AI) splits expenses exactly to the paisa and works out the fewest transfers to settle up.

THE PRINCIPLE
AI reads and writes. Code checks and keeps the records. People decide. Every change to money, medicines or the visit rota waits on a native Switch approval card, real buttons on Discord. Switch tells my agents who pressed the button, so the rules are code: only family counts, nobody approves their own expense, a payment is confirmed by whoever received the money.

WHY IT'S SAFE TO TRY
Nothing here is medical advice. A line the checker can't trace to the prescription's own text is kept out and listed on the card. Doses become clock times from a fixed table, never from a model. Money is integer paise. Switch's addressing policies are set so only people (and the named agents) can talk to @ledger and @pillbox: a stray agent writing "@ledger add 50000" is refused by the Switch server before the agent sees it. I tested that live.

PROOF
140 automated tests, 14 live checks against a real Switch server (uv run carecircle check), CI on Linux and Windows, and a one-command offline replay of the whole story with no Switch, Discord or API keys (uv run carecircle demo). All demo data is fictional and watermarked.

HONEST LIMITS
Tested on Windows 11 with Discord only. The checker supports a second independent read of the photo but it isn't wired in (the card says so). Reminders need @pillbox running. People are matched by chat name in a config file.
```

## How is Switch used? (the key answer for the "Use of Switch" criterion)

```text
Switch is the room everything happens in; remove it and the project stops working:
1. Native approval cards: my two custom agents open cards through the agent-sessions approvals API and read the outcomes, including who answered. This is the human gate for every expense, medicine and call rota, and the basis of rules written in code.
2. Agent protocol: @ledger and @pillbox are custom agents written against the raw WebSocket + operations protocol (no SDK).
3. Managed Claude Code agents: @meds, @scribe, @coordinator are created by a one-click template and run on the family's own laptop.
4. Addressing policies: the server refuses a stray agent before @ledger sees the message.
5. Agent-to-agent handoffs by mention: @meds → @pillbox, @coordinator → @pillbox, @scribe → @ledger.
6. Room documents with owners: care-plan (people only), medicine-list, expense-ledger, care-log, appointments.
7. Linked rooms: Ma's room is linked as "parent's room"; @pillbox finds it with list_linked_rooms.
8. Templates: one YAML creates the agents, both rooms, the link, the care plan and a kickoff; Switch's validator reports 0 errors and 0 warnings.
9. Question cards (Claude Code's question tool) for "who takes Ma?", rendered by Switch as buttons.
10. Messaging bridge: Discord today; Switch makes Slack, Teams, Telegram and Mattermost a configuration change (not tested here).
```

## Judging criteria → evidence

| Criterion (weight) | Evidence |
|---|---|
| **Use of Switch (30%)** | The ten uses above; `uv run carecircle check` PASS lines; README "Why Switch is central" table with a "without it" column |
| **Technical execution (25%)** | 140 tests; 14 live checks; CI green on Linux + Windows; one-command offline replay; custom agents on the raw protocol; deterministic checker with property tests; clean-take `reset` command |
| **Creativity and impact (25%)** | A family problem with real numbers; an AI-reads / code-checks / people-decide split; among the entries I could find on 6–7 Nov, none combined money, medicines and visits for elder care (re-check before you make this claim publicly) |
| **Presentation (20%)** | Under-3-minute video of a real run on phones; README with diagram, tables and honest limits; blog with 12 first-timer setup problems |

## What's next (if asked)
- Test on Slack, Teams and Telegram; wire in a second independent OCR read; use Switch's identity linking instead of chat names; more languages; run it as a service for a family without a laptop.

## AI-use disclosure (if asked)
Built with Claude Code as a pair programmer. In the product, three agents are Claude Code agents; two are plain Python with no AI. All sample medical and financial data is fictional.
