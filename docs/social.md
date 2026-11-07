# #HowISwitch posts (drafts)

Attach a 20–30 second clip: a sibling's phone tapping **Approve** on @pillbox's card, then Ma's room showing her plan.

## X (≤ 280 characters)

Three siblings, three cities, one Ma. I built CareCircle on @SwitchAgents: Claude reads the prescription, plain code checks every line, and a sibling taps Approve on Discord before anything changes. Missed dose? It asks who'll call. #HowISwitch @WeMakeDevs

## LinkedIn

Three siblings in three cities, one mother living alone, and a WhatsApp group doing the job of a care team.

For the Flip the Switch hackathon (WeMakeDevs × DevTools Academy) I built **CareCircle** on Switch, the open-source layer that turns a chat channel into a room shared by people and AI agents.

How it works:
• @meds (Claude Code) reads a prescription photo and copies every line verbatim.
• @pillbox (plain Python, no AI) checks each line against the text it came from, then shows a native Switch approval card. Only a sibling's tap updates Ma's list.
• At 8 AM Ma gets a "Taken?" card. If nobody answers, the siblings get "Can someone call Ma?"
• @coordinator asks who takes Ma to the cardiologist; @ledger splits the lab bill to the paisa.

The rule I designed around: **AI reads and writes, code checks and keeps the records, people decide.** Switch enforces it at the server: an agent that isn't allowed to address the money keeper is refused before the message arrives.

Try it offline in one command: `uv run carecircle demo`
Code: https://github.com/abhi-0404/carecircle · Demo: _link_

#HowISwitch #AI #OpenSource #Caregiving
