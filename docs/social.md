# Social posts (#HowISwitch)

Replace `VIDEO_LINK` and `BLOG_LINK` once they exist (send me the links and I'll do it). Attach a **20–30 second clip**: Rahul's phone tapping **Approve** on the card, then Ma's room showing her plan. Post natively (upload the clip to X / LinkedIn) rather than only linking, since native video gets seen more.

Don't tag accounts I couldn't verify. If you know the official handles for WeMakeDevs, DevTools Academy and Switch, add them.

---

## X: single post (under 280 characters)

```text
Three siblings, three cities, one Ma.

CareCircle on Switch: Claude reads the prescription, plain code checks every line, and a sibling taps Approve on Discord. Missed a dose? It asks who'll call.

🎬 VIDEO_LINK
💻 github.com/abhi-0404/carecircle

#HowISwitch
```

## X: thread (post as replies, with the clip on the first)

```text
1/ Three siblings, three cities, one mother who lives alone. Her care ran on a WhatsApp group. So for the Flip the Switch hackathon I built CareCircle: a Discord room where AI agents do the paperwork and a sibling taps Approve first. 🎬 VIDEO_LINK #HowISwitch

2/ The rule I built around: AI reads and writes, code checks and keeps the records, people decide. Claude copies a prescription line by line; plain Python checks every field against its own line. An invented medicine or a changed strength is thrown out.

3/ Every change waits on a native Switch approval card, real buttons on Discord. Switch tells my code who tapped, so the rules are code: only family counts, nobody approves their own expense, a payment is confirmed by whoever received the money.

4/ Missed a dose? Switch has no scheduler, so a small agent keeps the clock: Ma gets a "Taken?" card at dose time; if nobody answers, the family gets "Can someone call Ma?" and the first to tap is named.

5/ And Switch itself enforces who may talk to the money agent: a stray agent writing "@ledger add 50000" is refused by the server before the agent sees it. I checked it live. 140 tests, offline demo: uv run carecircle demo. Code: github.com/abhi-0404/carecircle #HowISwitch
```

## LinkedIn

```text
Three siblings in three cities, one mother living alone, and a WhatsApp group doing the job of a care team.

For the Flip the Switch hackathon (WeMakeDevs × DevTools Academy) I built CareCircle on Switch, the open-source layer that turns a chat channel into a room shared by people and AI agents.

How it works
• @meds (Claude Code) reads a prescription photo and copies every line verbatim.
• @pillbox (plain Python, no AI) checks each field against the line it came from, then raises a native Switch approval card. Only a sibling's tap updates Ma's list.
• At dose time Ma gets a "Taken?" card. If nobody answers, the siblings get "Can someone call Ma?"
• @coordinator asks who takes Ma to the cardiologist, with one button per sibling.
• @ledger splits the lab bill to the paisa. Nobody can approve their own expense.

The principle: AI reads and writes, code checks and keeps the records, people decide. Switch enforces it at the server: an agent that isn't allowed to address the money keeper is refused before the message arrives (I tested it live).

What I'd tell another builder
1. Put the safety-critical bits (doses, money) in plain code; use the model where it's strong (reading a photo).
2. Make the human step a real button, and use *who* pressed it in your rules.
3. Use the platform's access rules instead of prompts to say who may talk to what.

It runs on a laptop, 140 tests, 14 live checks, and the whole story plays offline with one command: uv run carecircle demo.

Video: VIDEO_LINK
Write-up: BLOG_LINK
Interactive replay (no install): https://abhi-0404.github.io/carecircle/
Code: https://github.com/abhi-0404/carecircle

Demo data is fictional, and CareCircle is not medical advice.

#HowISwitch #AIAgents #OpenSource #Caregiving #Hackathon
```

## For family, friends and WhatsApp status (no jargon)

```text
I built something for families like ours. 🧓📱

Three siblings in three cities share the care of one parent. Our "AI helpers" read a prescription photo, remind Ma about her medicines, ask who is taking her to the doctor, and split bills fairly. But nothing changes until one of us taps Approve.

2-minute video: VIDEO_LINK
```

## Dev community post (WeMakeDevs Discord, Reddit r/developersIndia, Hashnode cross-post)

```text
Built CareCircle for the Flip the Switch hackathon: a Discord room where Claude agents + two plain-Python agents help siblings share an aging parent's care (prescriptions, visits, medicines, expenses).

Things that might help if you're building on Switch:
• Native approval cards from a custom agent: POST /agent-sessions/{id}/approvals, then poll /approvals/outcomes. `answeredBy` lets you write rules in code.
• Addressing policies are enforced by the server: a stray agent can't reach your money agent.
• Switch has no scheduler: keep your own clock for reminders.
• On my machine, launching Switch Console from a VS Code terminal made it quit instantly: VS Code had set ELECTRON_RUN_AS_NODE=1. Open it from the Start menu.

Code (tests + offline demo): https://github.com/abhi-0404/carecircle · Video: VIDEO_LINK · Blog: BLOG_LINK  #HowISwitch
```

---

**Posting tips**
- Post the X thread and LinkedIn **after** the video and blog are live, so every post has working links.
- X counts every link as 23 characters, whatever its length.
- Reply to comments in the first hour; hackathon organisers often look at replies.
