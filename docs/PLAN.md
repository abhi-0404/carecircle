# CareCircle — build plan

Siblings in different cities share the care of an aging parent in one Discord
server. AI agents do the paperwork; a sibling taps a button before anything
happens.

## Prizes we are entering

| Prize | What it needs | Owner |
|---|---|---|
| Track 02 — Best Personal/Creative Workflow ($2,000) | Repo, README, demo video < 3 min | everyone |
| Best Blog (AirPods) | dev.to post: "how we built CareCircle on Switch" | |
| #HowISwitch (keyboard) | X + LinkedIn posts with the hashtag, demo clip | |
| Code with Wispr ($500) | Build by voice with Wispr Flow, submit Insights scorecard | |
| Random swag draw + certificate | Just submit | |
| Star the Switch repo (keyboard draw) | Star github.com/sandbox-quantum/switch | |

## The rooms (Discord channels)

| Room | Who is in it | Purpose |
|---|---|---|
| `#family-circle` | siblings + all agents | where the work happens |
| `#ma-corner` | parent (+ siblings) + `@meds`, `@coordinator` | simple reminders in large plain text |

The rooms are linked (`family-circle` → "parent's room"), created in one click
from `carecircle.template.yaml`.

## The agents

| Agent | Runs on | Job | Human gate |
|---|---|---|---|
| `@meds` | Claude Code | prescription photo → draft schedule; a code checker strikes any line not traceable to the photo text | approval card: "Add these N medicines?" |
| `@coordinator` | Claude Code | appointments, "who takes Ma?" question cards, chases unclaimed tasks | question card: siblings pick who goes |
| `@scribe` | Claude Code | doctor-visit voice note / report photo → plain-language summary in the care log | none (read-only output); siblings can ask follow-ups |
| `@ledger` | custom Python agent (agent protocol, **no LLM**) | records bills, exact split, settle-up | approval card before a split is recorded |

Room documents: `meds-list` (owned by `@meds`), `care-log` (owned by
`@scribe`), `expense-ledger` (owned by `@ledger`). Agents can only edit their
own documents, so each record has exactly one author.

## Safety rules (enforced in code, not prompts)

- No agent changes a dose or gives medical advice; `@meds` only transcribes.
- Every medicine line must match text extracted from the photo, or it is struck.
- All money maths in `@ledger` is plain Python with integer paise.
- Only siblings can answer approval cards (addressing policy).
- Synthetic data only in the demo; self-hosted Switch keeps family data local.

## Proof package (what top entries have, we must match or beat)

- `carecircle.template.yaml` — one-click setup
- "Remove Switch and it breaks" table mapping each Switch feature to evidence
- Offline demo mode (recorded replies, no API key)
- pytest for checker + ledger; CI
- Mermaid architecture diagram, screenshots, real run transcript
- Video: "One week of caring for Ma" on 3 phones in 3 cities, under 3 minutes
- Honest limits section

## Demo story (video script skeleton)

1. Mon — Priya (Pune) uploads Ma's new prescription photo → `@meds` drafts
   schedule → card → Rahul taps **Approve** → `#ma-corner` shows the schedule.
2. Tue — `@coordinator`: "Who takes Ma to cardiology Thu 10:00?" → Ankit taps
   **I'll go**.
3. Thu — Ankit sends a voice note after the visit → `@scribe` posts a summary
   to the care log.
4. Thu — Ankit uploads the ₹2,400 lab bill → `@ledger` proposes the split →
   card → approved → settle-up shows who owes whom.
5. Close: "Three cities, one circle. Built on Switch."

## Milestones

1. Switch Console running on Windows + Discord connected + switch-buddy replies
2. One Claude Code agent answering in `#family-circle`
3. Approval/question cards working on Discord (verify buttons render)
4. `@ledger` custom agent over the agent protocol
5. `@meds` + checker, `@scribe`, `@coordinator`
6. Template that recreates everything
7. Tests, offline demo, README
8. Video, blog, social posts, submit
