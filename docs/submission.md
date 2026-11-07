# Submission form: paste-ready answers (matches the form field by field)

The form has 3 parts. Copy each block into the field with the same number. Replace `VIDEO_LINK`, `BLOG_LINK` and `POST_LINK` once you have them (send me the links and I'll fill them in here too). *You can edit your submission until the deadline, so submit as soon as the video is up and add the blog and post links after.*

**Team:** solo, so only your own details. (Abhishek Kumar, GitHub `abhi-0404`.)

---

## PART 1: Project details

### 1. Project title *(required)*
```text
CareCircle
```

### 2. Tracks you are submitting for *(required)*
Tick **Track 02: Best Personal or Creative Workflow** only.
- Not Track 01: this is a family workflow, not a business one.
- Not Track 03: you have no pull request to Switch.
- **Code with Wispr:** the form says everyone with a submission is considered *if* they upload their Wispr usage card. Upload one **only** if you really built it with Wispr Flow and have the real screenshot from Insights. Otherwise leave it empty.

### 3. Project description *(required)*: What problem does your project solve, and who is it for?
```text
Three siblings live in three cities; their mother lives alone. Her care runs on a family chat: the prescription is a blurry photo three days up, nobody is sure who is taking her to Friday's cardiologist, and one sibling has quietly stopped asking to be paid back for the lab tests. In the US alone, 63 million people care for a family member, six in ten of them while holding a job (AARP, 2025). CareCircle is for those families.

It is a Discord room where five AI agents do the paperwork and a sibling taps Approve before anything changes. Claude reads a prescription photo and copies every line; plain code checks each field against its own line and keeps Ma's medicine list; a card asks who takes her to each visit; shared expenses are split exactly to the paisa; and a missed dose escalates to the family with "Can someone call Ma?".

The principle: AI reads and writes, code checks and keeps the records, people decide. Doses and money never come from a model, and nothing here is medical advice.

Everything is open source, runs on a laptop, has 140 tests, and the whole story replays offline with one command (uv run carecircle demo).
```

*Shorter version, if the field has a low limit:*
```text
Siblings in different cities share the care of an aging parent in one Discord room. Claude agents read prescriptions and plan visits; two plain-code agents check every medicine line and keep the money; a sibling taps Approve on a Switch card before anything changes. For families whose parent's care runs on a chat thread. Not medical advice.
```

### 4. GitHub Repository or contribution *(required)*
```text
https://github.com/abhi-0404/carecircle
```
Checked: public, and the README explains the agents, the channel setup, and how to run it (the form asks for exactly those). There is no LICENSE file; add one if you want one (tell me which).

### 5. Demo video *(required)*
```text
VIDEO_LINK
```
Must be: **under 3 minutes**, on **YouTube or Loom**, **public or unlisted**, and for Track 2 it must **show the agent working in a real chat with your teammates**. The script in [video-script.md](video-script.md) is built for that: two friends on their phones tapping the cards in the real Discord server.

### 6. Live demo or deployment
CareCircle runs on the family's own machine, so there is no hosted service. **Optional:** you can paste the interactive replay page, `https://abhi-0404.github.io/carecircle/`, which is a recording of the real agents' output (labelled as such on the page). Leave the field blank if you'd rather not call a replay a live demo.

---

## PART 2: Track details (all optional)

### 7. Pull requests
Leave **blank** (Track 3 only).

### 8. Blog post
```text
BLOG_LINK
```
Publish on dev.to first ([devto.md](devto.md), set `published: true`, keep the `howiswitch` tag). The form says the blog also enters you in **Best Blog**, judged on clarity, accuracy and how much it helps a first-time Switch user; the post has 12 real setup problems and fixes for that reason.

### 9. Your Wispr usage card
Leave **empty** unless you used Wispr Flow (see 2).

### 10. Your #HowISwitch post
```text
POST_LINK
```
One link: use your **X post** (the first post of the thread, with the video clip). The LinkedIn post is a bonus; it doesn't need to go in the form.

---

## PART 3: How you used Switch

### 11. How did you use Switch in your project? *(required)*
```text
AGENTS CONNECTED
• Claude Code, three agents (@meds, @scribe, @coordinator): created by a one-click Switch template as managed agents on my laptop. @meds reads prescription photos; @scribe writes the care log from visit notes; @coordinator asks the family who takes Ma to each visit.
• Two custom agents in plain Python with no AI (@pillbox, @ledger), written against the raw Switch agent protocol (WebSocket + operations, no SDK).

PLATFORM
Discord (tested on Windows 11 with Switch Console 0.40.1 and Switch 0.31.0), in two linked rooms: the family room and a calm room just for the parent. Switch also bridges Slack, Teams, Telegram and Mattermost; I did not test those.

THE REAL WORK, AND HOW THE FAMILY WORKS WITH IT
Siblings post a prescription photo, a visit note, or "add 2400 lab tests". The agents prepare; every change to the medicine list, an expense or the visit rota waits on a native Switch approval card (real buttons on Discord). Switch tells my agents who tapped, so the rules are code: only family counts, nobody approves their own expense, a payment is confirmed by whoever received the money. At dose time the parent gets a "Taken?" card; if nobody answers, the family gets "Can someone call Ma?".

SWITCH FEATURES THE PROJECT DEPENDS ON
Approval and question cards (agent-sessions API) · addressing policies (the server refuses a stray agent before @ledger sees it) · managed Claude Code agents · agent-to-agent handoffs by mention · room documents with owners (agents get a 403 editing the template's care-plan) · linked rooms (list_linked_rooms) · a template that passes Switch's validator with 0 errors and 0 warnings · the agent protocol itself.

Run it: README, or offline with one command: uv run carecircle demo.
```

### 12. What did you like about Switch, and what would you improve? *(required)*
```text
WHAT I LIKED
• Approval cards that say who answered. Human-in-the-loop is a platform feature, not something I had to build, and knowing who tapped let me put the rules in code.
• Addressing policies enforced by the server. I limited @ledger to people and @scribe, then had a stray agent write "@ledger add 50000…". Switch refused it ("my operator has restricted who can address me here") before my agent saw it. A prompt can be talked around; this can't.
• Templates plus the validate endpoint. One YAML created three Claude Code agents, two linked rooms, a document and a kickoff, and the validator checked it before I ran it.
• Document ownership. Agents get a 403 ("did not create document") editing the template's care-plan, which is exactly what a family wants for allergies.
• Linked rooms: list_linked_rooms let my agent find the parent's room without hard-coding it.

WHAT GOT IN THE WAY
• No client library: I wrote the WebSocket, heartbeat, resume and approval-card client myself. The approval endpoints for custom agents weren't in the agent-protocol docs I read; I found them in the source.
• No scheduler: reminders needed my own clock. A scheduled-message operation would remove a whole component.
• Managed agents need Switch Console running. The server stayed healthy while a template run failed with "none of your owner's machines can take it (… is offline)", and Console's Home said "Running" while it couldn't reach the server. A clear "Console isn't connected" state would save time.
• First start on Windows showed "switch-core did not become healthy in time" (Retry fixed it). Launching Console from a VS Code terminal makes it exit silently, because VS Code sets ELECTRON_RUN_AS_NODE=1.
• When one agent mentions another in prose, the second wakes and replies, so agents chatter. A way to mention without addressing would help.
• An approval outcome names a Discord person by a long participant id; a display name would help. Answers are polled; a push event would be nicer.
• Per the adapter source, archiving a room leaves its Discord channel behind (only deleting the room removes it), and the Discord guide lists eight permissions while the adapter's own install link also asks for Create Public Threads and Add Reactions.

WHAT I'D WANT NEXT
Scheduled messages, an official Python agent SDK, and an "approval answered" event on the agent stream.
```

*Shorter version (about 750 characters), if the field has a low limit:*
```text
Liked: approval cards that report who answered (so my rules are code); addressing policies the server enforces (a stray agent's "@ledger add 50000" was refused before my agent saw it); templates plus the validate endpoint; document ownership (agents get a 403 editing the care-plan); linked rooms.
Got in the way: no client library or scheduler (I wrote the WebSocket client and my own reminder clock; approval endpoints weren't in the protocol docs I read); managed agents need Switch Console running, and its Home said "Running" while it couldn't reach the server; first Windows start hit "did not become healthy in time"; agents that mention each other wake each other.
Next: scheduled messages, a Python agent SDK, an "approval answered" event.
```

---

## Before you press Submit

- [ ] Repo is public and the CI badge is green
- [ ] Video: under 3:00, public or unlisted, shows the real chat with friends, link opens in a private window
- [ ] Blog published (`published: true`) and its link opens
- [ ] X post is live with the clip and `#HowISwitch`
- [ ] Nothing in the video, blog or repo shows a token, `.env` or your company
- [ ] You did **not** claim Wispr, Slack, Teams or Telegram testing
- [ ] Fields 3, 11 and 12 pasted; "Live demo" and "Pull requests" left blank

## What I verified live for these answers
Room link lookup (`list_linked_rooms` returns the parent's room), agent 403 editing the care-plan, the refusal of a stray agent, approval cards and who-answered, 14 live checks, 140 tests, CI on Linux and Windows. Not verified: any chat app other than Discord; the exact character limits of the form's text boxes (shorter versions are provided for fields 3 and 12).

## Character counts

| Field | Characters |
|---|---|
| 3. Project description | 1,142 |
| 3. Project description (shorter) | 342 |
| 11. How did you use Switch | 1,742 |
| 12. Like / improve | 2,373 |
| 12. Like / improve (shorter) | 748 |
