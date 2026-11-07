---
title: "Who's taking Ma to the cardiologist? Building a family care room on Switch"
published: false
description: "Three siblings, three cities, one Ma. AI agents read and write, plain code checks and keeps the records, and a sibling taps Approve on Discord. #HowISwitch"
tags: howiswitch, hackathon, ai, opensource
cover_image: https://raw.githubusercontent.com/abhi-0404/carecircle/main/demo/samples/lab-bill.png
---

*"Ankit paid ₹2,400 for Ma's lab tests and quietly stopped asking to be paid back."*

Picture a family WhatsApp group: three siblings, three cities, one mother living alone. Her care runs on that chat thread: a blurry prescription photo three days up, nobody sure who is taking her to the doctor on Friday, and money nobody wants to bring up. Many Indian families with children working in other cities will recognise it.

For the **Flip the Switch** hackathon I built **CareCircle**: a Discord server where AI agents do the paperwork and a sibling taps **Approve** before anything changes. This post is how it works, what Switch made possible, and every setup problem I hit as a first-time Switch user, so you don't have to.

> 🎬 **Demo (under 3 min):** _add your YouTube link here_

{% github abhi-0404/carecircle %}

## Switch in one paragraph

[Switch](https://github.com/sandbox-quantum/switch) turns a chat channel (Slack, Teams, Discord, Telegram, Mattermost) into a **room** that people and AI agents share. An agent is anything that speaks Switch's agent protocol: Claude Code, Codex, or your own program. A room carries **instructions** every agent reads, **documents**, **roles**, and **links** to other rooms. When an agent needs a decision, it can raise an **approval card**, which shows up as real buttons on Discord or Slack. A **template** is a YAML file that creates agents and rooms in one go.

![The sample prescription @meds reads (fictional, watermarked)](https://raw.githubusercontent.com/abhi-0404/carecircle/main/demo/samples/prescription-cardiology.png)

## The design: AI reads and writes, code checks and keeps the records, people decide

Five agents, two rooms:

| Agent | What it is | Job |
|---|---|---|
| `@meds` | Claude Code | reads a prescription photo, copies every line verbatim |
| `@pillbox` | Python, **no AI** | checks the transcript, keeps Ma's medicine list, reminds her at dose times |
| `@coordinator` | Claude Code | asks the family who takes Ma to each visit |
| `@scribe` | Claude Code | turns visit notes into a care log |
| `@ledger` | Python, **no AI** | shared expenses, exact to the paisa |

`#sharma-circle` is the siblings' room. `#sharma-ma` is a calm room for Ma that only shows today's medicines and the next visit. The two are **linked**, which is how `@pillbox` finds Ma's room.

The split matters. I wanted Claude where it is genuinely good (reading a photo of handwriting-ish print, understanding "Ma has a follow-up with Dr. Kapoor next Friday at 10") and plain code wherever a mistake would hurt (doses, money).

### A prescription, end to end

1. Priya posts the photo and writes `@meds please read Ma's new prescription`.
2. `@meds` downloads the attachment, copies each line exactly (`Tab. Amlodipine 5mg 1-0-1 x 30 days after food`), fills in fields using only words from that line, and hands `@pillbox` a JSON transcript.
3. `@pillbox` checks every field against its own line. A field counts only if its words and numbers appear **side by side and in order** in that line. So if the model writes `Atenolol` for a line that says `Amlodipine`, or `10 mg` for `5mg`, the line is kept out. (My first version did a substring check, and a test caught that "10" matched inside "1-0-1". Tests earn their keep.)
4. Dose codes become times from a fixed table: `1-0-1` is 8 AM and 9 PM, `BD` the same, `TDS` adds 2 PM, `SOS` is "only when needed".
5. `@pillbox` raises an approval card listing the four medicines. Only when a family member taps **Approve** does it update the `medicine-list` document and post the plan in Ma's room.

When I tested this live, Claude copied all four lines perfectly. Then, in a later test, I sent `@scribe` some visit notes ("doctor increased Amlodipine to 10 mg twice daily"). It wrote the care log and then, unprompted, pointed out that the list still said 5 mg and asked the family to send the new prescription, adding that starting the new dose was a question for the doctor. That is exactly the behaviour you want from an AI near medicine: notice, and hand it to a human.

### Reminders, because Switch has no scheduler

Switch doesn't schedule messages, so `@pillbox` keeps its own clock. At 8 AM it posts a card in Ma's room: **"🌅 Ma, time for your morning medicines"** with **✅ Taken** and **⏰ Not yet**. If nobody answers in 30 minutes, it withdraws the card and tells the siblings, with a **📞 I'll call** card. The first sibling to tap it is named in the room.

### Money

`@ledger` has a fixed grammar (`add 2400 lab tests paid by ankit`, `settle`) and does every sum in integer paise. A split always adds up exactly (property-tested over thousands of random cases), and settle-up finds the fewest transfers.

## What Switch gave me that I couldn't have built in two days

**Approval cards from my own code.** My two Python agents call `POST /agent-sessions/{session}/approvals` with Approve/Reject options, then poll `/agent-sessions/approvals/outcomes`. Switch draws the card on Discord as buttons and tells me **who** tapped. That identity is what makes code rules possible:

- only someone in the family list counts (a cousin's tap re-issues the card);
- nobody approves their own expense;
- a settle-up payment is confirmed by the person who received the money.

**Addressing policies, enforced by the server.** I set `@ledger` to accept messages only from people and from `@scribe`:

```json
{"rules": [{"users": "*", "agents": []},
           {"users": [], "agents": ["<scribe's id>"]}]}
```

Then I had a stray agent post `@ledger add 50000 gold chain paid by abhishek`. `@ledger` never saw it. Switch answered for it: *"You're not permitted to direct messages to me in this room — my operator has restricted who can address me here."* Prompts can be talked around; this can't.

**Claude Code as a room member.** `@meds`, `@scribe` and `@coordinator` are ordinary Claude Code agents, created by my template, running on my laptop. `@coordinator` asks "who takes Ma?" with Claude Code's own question tool, and Switch renders it as a card with one button per sibling.

**Documents with owners.** `care-plan` is created by the template, so agents can read it but not change it: Ma's allergies stay in people's hands. `medicine-list` and `expense-ledger` are edited only by the agent that created them.

**Templates.** One YAML file creates the three Claude Code agents, both rooms, the link, the care plan and a welcome message. Switch's validator gives it 0 errors and 0 warnings.

## Setup problems I hit (so you don't)

I'm on Windows 11 with Switch Console 0.40.1 and Switch 0.31.0. In order:

1. **"switch-core did not become healthy in time" on first start.** Nothing was broken: the first start compiles and scans thousands of files and took longer than Console waits. Click **Retry**, don't click *Start over*. The second start took 66 seconds.
2. **Don't close the black cmd window.** On Windows the local server runs in a console window. Closing it kills the server instantly (exit code `0xC000013A`), with nothing in the logs. Minimize it.
3. **Restart lives under Admin → Status.** When the server stops, Home may still say *Running*. The Restart button is in **Admin → Status**.
4. **No "API keys" page in Console 0.40.1.** Registration keys for custom agents come from the server's gateway (`POST /gateway/api-keys`), not Console's Settings in this version.
5. **An agent can't change its own permissions.** `update_agent_detail` on yourself is a 403: "Your owner changes them". Set addressing as the owner (gateway, or Console).
6. **Check which Discord server you connected.** I created a new server and kept posting there, while Switch was still connected to my old one (the log says `connected as … (guild <id>)`). The guild id lives in the connection config and can be changed without re-entering the token.
7. **Two bot permissions the guide doesn't list.** Switch's Discord adapter also uses **Create Public Threads** and **Add Reactions**.
8. **`{$creator}` in a template needs a linked identity.** If your Switch account isn't linked to your Discord account, a template that puts `{$creator}` in a room is refused. On Discord, public channels are visible to the server anyway, so I dropped it.
9. **Posting in the wrong channel.** Agents only hear rooms they're members of. Switch tells you plainly: "Meds isn't in this room."
10. **Agents waking each other.** When `@meds` wrote "@pillbox is checking it", `@pillbox` replied with help text, and `@meds` then asked where the card was. Two fixes: code agents ignore agents that mention them in passing, and AI agents are told to write other agents' names without "@" unless they're handing over work.

## Try it

```bash
git clone https://github.com/abhi-0404/carecircle && cd carecircle
uv sync
uv run carecircle demo     # the whole story, offline: no Switch, no Discord, no keys
uv run pytest              # 137 tests
```

With a Switch server running: register the two code agents, run the template, `uv run carecircle lock`, and `uv run carecircle check` (12 live checks, including the refusal above).

## Honest limits

- Not medical advice. The agents copy and flag; decisions stay with the family and their doctors.
- The prescription is read once by Claude; the checker supports a second, independent OCR read, but I didn't wire one in, and the card says so.
- People are recognised by chat names in a config file; Switch's identity linking would be stronger.
- Tested on Windows + Discord only.

---

*All demo data is fictional: the prescription and lab bill are watermarked samples, and the Sharma family is made up. I built this with Claude Code as a pair programmer.*
