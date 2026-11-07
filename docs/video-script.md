# Demo video script (target 2:40, hard limit 3:00)

**Cast** (use real first names in the room if your friends agree; the script uses these):
- **Abhishek**: you, on the laptop (Discord desktop).
- **Priya**: friend 1, on a phone.
- **Rahul**: friend 2, on a phone.

**Before you press record:** [00-START-HERE.md](00-START-HERE.md) section A (check 14/14, friends registered) and section B (rehearsal, then `reset` for a clean take). Dark theme, Do Not Disturb, close other windows. Family room names below are for family `sharma2`; swap in your current ones.

## The shot list

Each scene is its own clip. **Say the voiceover (VO) lines out loud, slowly, in a separate recording** after you've captured the screens; the lines are written to be read at about 130 words a minute.

### 1. Hook (0:00–0:12)
- **Screen:** dark title card (use [the thumbnail](assets/thumbnail.png)), or a still of a messy family chat. Slow fade in.
- **Caption:** *Three siblings. Three cities. One Ma.*
- **VO:** "Three siblings. Three cities. One mother who lives alone. And a family chat that's trying to be her care team."

### 2. The room (0:12–0:30)
- **Screen (laptop):** Discord → `#sharma2-circle`, with the member list open on the right: `meds`, `scribe`, `coordinator`, `pillbox`, `ledger`. Then click across to `#sharma2-ma`.
- **Caption:** *CareCircle, built on Switch*, then *3 Claude agents · 2 plain-code agents*
- **VO:** "This is CareCircle, built on Switch. One Discord server, two rooms: the family's room, and a calm one just for Ma. Five agents live here. Three are Claude. Two are plain code, with no AI in them at all."

### 3. A prescription (0:30–1:05)
- **Screen (Priya's phone, then laptop):**
  1. Priya uploads the prescription photo and types `@meds please read Ma's new prescription`.
  2. *Cut ahead* (caption **40 seconds later**) to the card from `pillbox`: **Add 4 medicines to Ma's schedule?** Zoom in on the line "⚠️ The photo wasn't read a second time" only if you want to show honesty; otherwise zoom on the four medicines.
  3. Rahul (phone) taps **Approve**.
  4. Switch to `#sharma2-ma` on the laptop: the morning/night plan.
- **Caption:** *Claude reads. Code checks every line. A sibling decides.*
- **VO:** "Priya posts Ma's new prescription. Claude copies every line exactly as printed. Then plain code checks each field against its own line. If the AI invents a medicine, or changes a strength, that line is thrown out. What's left goes on a card. Rahul taps Approve, and only then does Ma's plan appear, in her own room."

### 4. Who takes Ma? (1:05–1:30)
- **Screen (laptop, then phone):**
  1. Abhishek types: `@coordinator Ma has a cardiology follow-up with Dr. Kapoor at Sunrise Heart Clinic, Patna on Friday 13 November 2026 at 10:00 AM.`
  2. *Cut ahead* to the question card with a button per sibling.
  3. Priya (phone) taps her own name.
  4. Show `#sharma2-ma`: "📅 Ma, your next visit: Friday 13 Nov, 10:00 AM … Priya will take you."
- **Caption:** *One tap. Ma is told in her own room.*
- **VO:** "Friday is the cardiologist. Instead of a group-chat argument, a card, with one button per sibling. Priya taps her name. Ma is told in her room, and reminded the evening before."

### 5. Money (1:30–1:58)
- **Screen (laptop; Rahul's phone for the second tap):**
  1. Abhishek types `@ledger add 2400 lab tests`.
  2. Abhishek taps **Approve** on his own expense. `ledger` answers: **"Abhishek can't decide this one: nobody approves their own expense."** Pause on that line for a full second.
  3. Rahul (phone) taps **Approve** on the fresh card → "✅ Recorded #1 … Abhishek is owed ₹1,600".
  4. Abhishek types `@ledger settle` → the two transfers.
- **Caption:** *Rules in code, not in a prompt.*
- **VO:** "Abhishek paid the lab bill. He can't approve his own expense, and that rule is code, not a prompt. Rahul confirms. Settle-up says exactly who owes whom, down to the paisa."

### 6. The missed dose (1:58–2:22)
- **Screen (laptop):**
  1. Abhishek types `@pillbox remind now`.
  2. Show the reminder card in `#sharma2-ma`: **Ma, time for your … medicines** with ✅ Taken / ⏰ Not yet. Nobody taps.
  3. *Cut ahead* (caption **2 minutes later, shortened for the demo**) to the family room: "⚠️ Nobody confirmed Ma's … medicines" and the card **Can someone call Ma?**
  4. Rahul (phone) taps **📞 I'll call** → "📞 Rahul is calling Ma. Thank you!"
- **Caption:** *Switch has no scheduler, so Pillbox keeps its own clock.*
- **VO:** "Every dose time, Ma gets a Taken card. If nobody answers, the family is told, and someone has to say I'll call. Switch has no scheduler, so Pillbox keeps its own clock."

### 7. The proof (2:22–2:42)
- **Screen (laptop):** terminal: `uv run carecircle check`. Let the PASS lines scroll (speed up 2×), pausing on **PASS Switch refuses a stray agent addressing @ledger**. Then flip to Discord and show the refusal: *"You're not permitted to direct messages to me in this room — my operator has restricted who can address me here."*
- **Caption:** *Enforced by the Switch server, before the agent ever sees it.*
- **VO:** "And the money agent is protected by Switch itself. A stray agent trying to add fifty thousand rupees is refused by the server before the message arrives. AI reads and writes. Code checks. People decide."

### 8. Close (2:42–2:52)
- **Screen:** [thumbnail](assets/thumbnail.png) or the README top, then the text `uv run carecircle demo` and `github.com/abhi-0404/carecircle`.
- **Caption:** *CareCircle · Built on Switch · Try it offline in one command*
- **VO:** "CareCircle. Built on Switch. The code is on GitHub."

---

## The voiceover in one piece (read this when recording audio)

> Three siblings. Three cities. One mother who lives alone. And a family chat that's trying to be her care team.
>
> This is CareCircle, built on Switch. One Discord server, two rooms: the family's room, and a calm one just for Ma. Five agents live here. Three are Claude. Two are plain code, with no AI in them at all.
>
> Priya posts Ma's new prescription. Claude copies every line exactly as printed. Then plain code checks each field against its own line. If the AI invents a medicine, or changes a strength, that line is thrown out. What's left goes on a card. Rahul taps Approve, and only then does Ma's plan appear, in her own room.
>
> Friday is the cardiologist. Instead of a group-chat argument, a card, with one button per sibling. Priya taps her name. Ma is told in her room, and reminded the evening before.
>
> Abhishek paid the lab bill. He can't approve his own expense, and that rule is code, not a prompt. Rahul confirms. Settle-up says exactly who owes whom, down to the paisa.
>
> Every dose time, Ma gets a Taken card. If nobody answers, the family is told, and someone has to say I'll call. Switch has no scheduler, so Pillbox keeps its own clock.
>
> And the money agent is protected by Switch itself. A stray agent trying to add fifty thousand rupees is refused by the server before the message arrives. AI reads and writes. Code checks. People decide.
>
> CareCircle. Built on Switch. The code is on GitHub.

If you'd rather talk over it in your own words, keep the same order and these four ideas: **Claude reads, code checks, people decide; cards are real buttons; rules are enforced in code and by Switch; nothing here is medical advice.**

---

## Recording tips

**Phones**
- Record each friend's phone separately, taps visible (Android: Developer options → *Show taps*).
- Hold the phone in portrait; in the edit, place the clip on the right third of the frame beside the laptop.
- Pause 1 second after every tap before the next message appears; it makes the cut cleaner.

**Laptop**
- **Win + Alt + R** records the focused window (Discord). For the terminal scene, focus Windows Terminal and record it the same way.
- Discord zoom: **Ctrl +** two or three times so text is readable at 1080p. Hide other servers' names if you like.
- Resolution 1920×1080, 30 fps.

**Editing in Clipchamp** (free, built into Windows 11)
1. Import the clips, drop them on the timeline in scene order.
2. Cut the waiting: trim to the moment the card appears, add a text overlay such as **"40 seconds later"**.
3. Speed up the terminal scene to 2×.
4. Add the captions as text overlays (white text, dark band behind).
5. Record the voiceover in Clipchamp (Record & create → Audio) or on your phone, and drop it on the audio track.
6. Music: YouTube Audio Library, calm, low (about −20 dB under the voice).
7. Export 1080p. Check there's no watermark and the length is **under 3:00**.

**Retakes:** `uv run carecircle reset --yes --family sharma4` gives a fresh set of rooms and AI helpers in about a minute (Switch Console must be open).

**Honesty reminders on screen:** the medicines and bills are **fictional sample documents**; if you want, add a small caption on the card scene: *Demo data is fictional. Not medical advice.*
