# YouTube package

**Visibility:** *Public* is safest for judges; *Unlisted* also works with a link. Upload at 1080p. Set the thumbnail to [assets/thumbnail.png](assets/thumbnail.png).

## Title (pick one, all under 100 characters)

1. `CareCircle: three siblings, one Ma, and AI that asks before it acts | Flip the Switch hackathon`
2. `CareCircle demo: AI reads the prescription, code checks it, siblings approve | Built on Switch`
3. `Who's taking Ma to the cardiologist? A family care room built on Switch (#HowISwitch)`

## Description (paste as is; fill the two links, then fix the timestamps to match your edit)

```text
Three siblings, three cities, one mother who lives alone. CareCircle is a Discord room where AI agents do the paperwork and a sibling taps Approve before anything changes.

AI reads and writes. Code checks and keeps the records. People decide.

▶ What you'll see
• Claude reads a prescription photo and copies every line verbatim; plain code checks each field against its own line before a sibling approves.
• One tap decides who takes Ma to the cardiologist; Ma is told in her own room.
• A shared expense nobody can approve for themselves; settle-up exact to the paisa.
• A missed-dose reminder that escalates to the family.
• Switch itself refusing a stray agent that tries to add an expense.

⏱ Chapters
0:00 Three siblings, three cities, one Ma
0:12 The room: five agents
0:30 A prescription: Claude reads, code checks, a sibling approves
1:05 Who takes Ma to the cardiologist?
1:30 Money: rules in code
1:58 The missed dose
2:22 Proof: enforced by the Switch server
2:42 Try it

💻 Code (open source): https://github.com/abhi-0404/carecircle
📝 Blog: BLOG_LINK
🧪 Try it offline, no keys needed: uv run carecircle demo

Built on Switch (https://github.com/sandbox-quantum/switch) for the Flip the Switch hackathon by WeMakeDevs and DevTools Academy, Track 02. Five agents: three Claude Code agents (@meds, @scribe, @coordinator) and two plain-Python agents with no AI (@pillbox, @ledger), using native Switch approval cards, addressing policies, room documents, linked rooms and one-click templates.

⚠️ All names, prescriptions and bills in this video are fictional sample data. CareCircle copies what doctors write and flags what's unclear; it does not give medical advice.

#HowISwitch #Switch #AIagents #Discord #Caregiving #Hackathon
```

## Tags

`CareCircle, Switch, SandboxAQ, AI agents, Claude Code, Discord bot, human in the loop, caregiving, family care, elder care, WeMakeDevs, DevTools Academy, HowISwitch, hackathon, multi-agent, approval cards`

## Thumbnail

Already made: [assets/thumbnail.png](assets/thumbnail.png) (1280×720; "Three siblings. Three cities. One Ma." with an approval card). Redraw it with `uv run --no-project --with pillow python demo/make_thumbnail.py`.

## Pinned comment

```text
Try it without Switch, Discord or any keys: git clone https://github.com/abhi-0404/carecircle && cd carecircle && uv sync && uv run carecircle demo
The code is open source. Questions about how a prescription becomes a checked card, or how the Switch server refuses a stray agent, are welcome here.
```

## Other settings
- **Audience:** not made for kids. **Category:** Science & Technology.
- **Language:** English. Add captions if you can: *Subtitles → Auto-generate*, then correct "Switch", "paisa", "Pillbox".
- **Add to a playlist** if you have one for the hackathon; otherwise skip.
