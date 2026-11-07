# CareCircle: start here (test, record, publish)

Everything you need, in the order you need it. Files referenced:

| File | What it is |
|---|---|
| [video-script.md](video-script.md) | shot-by-shot script, exact messages to type, word-for-word voiceover, editing notes |
| [youtube.md](youtube.md) | title, description with chapters, tags, thumbnail, pinned comment |
| [assets/thumbnail.png](assets/thumbnail.png) | YouTube thumbnail (1280×720) |
| [devto.md](devto.md) | the blog post, ready to paste into dev.to (`published: false` until you flip it) |
| [assets/cover.png](assets/cover.png) | dev.to cover image |
| [social.md](social.md) | X post, X thread, LinkedIn, a plain-words caption for family and friends |
| [submission.md](submission.md) | answers for the hackathon submission form |

> **Time check.** Every official page I could find still says submissions close **tonight, 7 Nov, 11:59 PM IST**; I found no extension. If your inside news about an extension is right, ignore this. If not, the short route is: rehearse once (20 min) → record (60 min) → edit (45 min) → upload and publish (30 min).

---

## A. Get ready (about 10 minutes)

**1. The three things that must stay open**

| What | How to know it's fine |
|---|---|
| **Switch Console** (the app) | It runs the three Claude helpers. If you quit it, `@meds`, `@scribe` and `@coordinator` go silent. Open it from the **Start menu**. |
| **The Switch server's black window** | Minimize it, never close it. |
| **`@ledger` and `@pillbox`** | Double-click [`scripts\start.bat`](../scripts/start.bat), or `uv run carecircle run`. Leave the window open. *(I currently have them running; use the bat file if you restart the laptop.)* |

**2. Check everything (30 seconds)**

```powershell
cd "D:\All_Project\Ai Project\Switch"
uv run carecircle check
```
You want **14/14 checks passed**. Anything FAIL says what to do.

**3. Get your two friends in**
1. In Discord, right-click the **family-circle** server → **Invite People** → send the link.
2. Once they've joined, each friend posts `hi` in **#sharma2-circle** (the current family room).
3. Run `uv run carecircle who`. For each friend it prints either `OK … counts as Priya` or `NEW … is not in circle.json`.
4. For each `NEW`, run (use the chat name exactly as printed):
   ```powershell
   uv run carecircle member priya THEIR_CHAT_NAME
   uv run carecircle member rahul THEIR_OTHER_FRIEND_CHAT_NAME
   ```
   The running agents pick it up within a few seconds; no restart. Run `who` again: both should say `OK`.

> **Why this step matters:** a tap only counts if Switch recognises the person. A friend whose name isn't registered gets "isn't in the family circle" on camera.
>
> **Solo fallback** (no friends yet): put `"not_own_entry": false` in `circle.json`; you can then approve your own entries. You lose the "nobody approves their own expense" shot.

**4. On the phones**
- Save the sample prescription to the friend's phone who will post it: open <https://raw.githubusercontent.com/abhi-0404/carecircle/main/demo/samples/prescription-cardiology.png> → press and hold → **Save image**.
- Discord on dark theme; **Do Not Disturb** on (no pop-ups in the recording).
- Android: Settings → Developer options → **Show taps**, so the taps are visible in the video. iPhone: nothing needed.

---

## B. Rehearse once (20 minutes), then reset

Run every step once. Each row says what you type and what should happen. **If a row doesn't match, send me a screenshot and the row number.**

All typing is in **#sharma2-circle** unless stated. After typing `@`, pick the agent from Discord's pop-up list so it becomes a real mention.

| # | Who | Type or tap | What should happen | Wait |
|---|---|---|---|---|
| 1 | friend | Upload the prescription image, add the text `@meds please read Ma's new prescription` | `meds` posts a block starting `@pillbox` with the copied lines, then "I've copied the prescription; pillbox is checking it"; then **a card from pillbox: "Add 4 medicines to Ma's schedule?"** with Approve / Reject buttons | 30–90 s |
| 2 | other friend | Tap **Approve** | `pillbox`: "✅ Added 4 medicine(s) to Ma's list — approved by …". In **#sharma2-ma**: "📋 Ma, here is your updated medicine plan" with morning/night sections | 5 s |
| 3 | you | `@coordinator Ma has a cardiology follow-up with Dr. Kapoor at Sunrise Heart Clinic, Patna on Friday 13 November 2026 at 10:00 AM.` | `coordinator` confirms, then **a question card: "Who takes Ma"** with one button per sibling plus "Nobody can - need help". *(If it shows numbered choices you have to type instead of buttons, tell me: the video script says "buttons".)* | 30–90 s |
| 4 | a friend | Tap a sibling's name | `coordinator` thanks them and saves an `appointments` document; `pillbox`: "📅 Noted: Friday 13 Nov, 10:00 AM …"; **#sharma2-ma** shows "📅 Ma, your next visit …" | 30–60 s |
| 5 | you | `@ledger add 2400 lab tests` | A card: "Record ₹2,400 for lab tests?" "Paid by Abhishek. Split: …" | 3 s |
| 6 | you | Tap **Approve** on your own expense | `ledger`: "⚠️ Abhishek can't decide this one: nobody approves their own expense — another sibling has to confirm it." and a fresh card | 3 s |
| 7 | a friend | Tap **Approve** on the fresh card | `ledger`: "✅ Recorded #1: ₹2,400 for lab tests — approved by …" and who owes whom | 3 s |
| 8 | you | `@ledger settle` | "💸 To settle up (2 transfers): …" | 3 s |
| 9 | you | `@pillbox remind now` | A card appears in **#sharma2-ma**: "🌅/🌙 Ma, time for your … medicines" with ✅ Taken / ⏰ Not yet | 3 s |
| 10 | a friend | Tap **✅ Taken** | `pillbox` in the family room: "✅ Ma took the … medicines (… confirmed by …)" | 3 s |
| 11 | you | `@pillbox remind now` again, and **don't tap** | After ~2 minutes: "⚠️ Nobody confirmed Ma's … medicines within 2 minutes" and a card **"Can someone call Ma?"** | 2–2.5 min |
| 12 | a friend | Tap **📞 I'll call** | `pillbox`: "📞 … is calling Ma. Thank you!" | 3 s |
| 13 | you | In the terminal: `uv run carecircle check` | 14 PASS lines including *"Switch refuses a stray agent addressing @ledger"*; in Discord you see the refusal message | 40 s |

**Also try once** (not in the video): tap **Approve** with someone who is *not* in the family list. You should get "isn't in the family circle" and a fresh card.

### Reset to a clean take (1–2 minutes)

The rehearsal leaves a recorded expense, a medicine list and a visit behind. For a clean recording:

```powershell
uv run carecircle reset --yes --family sharma3
```

- Use a **new family name each take** (`sharma3`, `sharma4`, …). Archiving leaves the old Discord channels in place, so new names stop you mixing them up.
- It **checks that Switch Console is running first**, and stops without changing anything if it isn't.
- Your friends' names stay registered. The new channels appear in the same Discord server.
- The rooms are named `#sharma3-circle` and `#sharma3-ma`; the script uses them as written. Change `sharma2` to your family name in the typed steps above.

---

## C. Record

Follow [video-script.md](video-script.md). In short:

1. **Record each scene as its own clip**, not one long take.
2. Claude takes 30–90 seconds to answer. **Don't wait on camera**: speed those parts up (2×) or cut.
3. Keep the final video **under 3:00** (the rules reported for this hackathon say a demo video under 3 minutes on YouTube or Loom; confirm on the rules page).
4. Record the voiceover separately, reading the script out loud, slowly.

Free tools: phone screen recorder (built in), **Win + Alt + R** (Windows Game Bar) for the laptop window, **Clipchamp** (built into Windows 11) to cut, speed up, add text and voiceover. Check that your Clipchamp export has no watermark with a 5-second test export first.

---

## D. Publish (in this order)

1. **Upload to YouTube** (public or unlisted). Title, description and thumbnail are in [youtube.md](youtube.md).
2. **Send me the YouTube link.** I'll put it in the README, the blog, the social posts and the submission answers, run the tests, and push to GitHub. (30 seconds of my work.)
3. **dev.to**: Create Post → paste [devto.md](devto.md), set `published: true` → publish. Keep the `howiswitch` tag.
4. **X and LinkedIn** from [social.md](social.md), with a 20–30 second clip.
5. **Submit** on the WeMakeDevs hackathon page using [submission.md](submission.md).

---

## If something breaks

| What you see | Why | Fix |
|---|---|---|
| "Meds isn't in this room, so your message won't reach it" | Wrong channel | Use the current family room (**#sharma2-circle** or your newest) |
| No card after 2 minutes | `@ledger`/`@pillbox` window closed, or Switch Console closed | Run `start.bat`; open Switch Console; `uv run carecircle check` |
| Card shows numbers like "1. Approve" you must type, not buttons | The Discord bot lacks **Manage Webhooks** | Discord → Server Settings → Roles → *CareCircle* → turn on **Manage Webhooks** |
| "… isn't in the family circle" | Friend's chat name not registered | `uv run carecircle who`, then `uv run carecircle member …` |
| `@meds`, `@scribe` or `@coordinator` never answer | Switch Console isn't open | Open it from the Start menu, wait 20 s. (Don't start it from a VS Code terminal: VS Code sets a variable that makes the app quit at once.) |
| Home says "Cannot reach the server" | The server's black window was closed | Switch Console → **Admin → Status → Start** |
| "I can't find Ma's room" | The two rooms aren't linked | `uv run carecircle reset --yes --family sharmaN` |
| "… has already passed" on a visit | The date is in the past | Use a future Friday in the `@coordinator` message |
| `reset` says Switch Console isn't connected | Console closed | Open it, wait 20 s, run `reset` again. Nothing was changed. |

---

## What you can safely say, and what not to

**True and verified:** 140 automated tests; 14 live checks pass on a real Switch server; tested on Windows 11 with Switch Console 0.40.1 / Switch 0.31.0 and Discord; CI green on Linux and Windows; the offline demo `uv run carecircle demo` needs no Switch, Discord or keys; Switch itself refused a stray agent's `@ledger add 50000…` (shown in the video); all demo data is fictional and watermarked.

**Don't claim:** that it gives medical advice (it explicitly doesn't); that it was tested on Slack, Teams or Telegram; that the prescription is read twice (the checker supports a second read, but it isn't wired in, and the card says so); that reminders arrive when `@pillbox` isn't running; that it was built with Wispr Flow (enter the Wispr side track only if you really used it).
