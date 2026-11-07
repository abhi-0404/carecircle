"""Build docs/index.html: an interactive replay of the CareCircle story (served by GitHub Pages).

    uv run python demo/make_replay.py

The events come from running the real @ledger and @pillbox code offline
(carecircle.demo.events). The page is a recording, not the live system, and says
so; each message is tagged "real" (produced by that code) or "scripted".
No external scripts, fonts or trackers.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from carecircle.demo import events

ROOT = Path(__file__).resolve().parents[1]
SITE = "https://abhi-0404.github.io/carecircle"
REPO = "https://github.com/abhi-0404/carecircle"

PAGE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>CareCircle: interactive replay</title>
<meta name="description" content="Three siblings, three cities, one Ma. AI reads and writes, code checks and keeps the records, people decide. A recorded replay of the real agents' output.">
<meta property="og:title" content="CareCircle: interactive replay">
<meta property="og:description" content="Siblings share an aging parent's care in one Switch room: AI proposes, plain code checks, a sibling taps Approve.">
<meta property="og:image" content="__SITE__/assets/thumbnail.png">
<style>
:root{--bg:#0f172a;--pane:#111827;--line:#1f2937;--text:#e5e7eb;--dim:#94a3b8;--amber:#fbbf24;--green:#16a34a;--card:#f8fafc;--ink:#0f172a}
*{box-sizing:border-box}
body{margin:0;overflow-x:hidden;background:var(--bg);color:var(--text);font:16px/1.5 system-ui,-apple-system,Segoe UI,Roboto,sans-serif}
a{color:var(--amber)}
header,footer{max-width:1100px;margin:0 auto;padding:20px 16px}
h1{margin:0 0 4px;font-size:clamp(1.5rem,4vw,2.1rem)}
.lead{color:var(--dim);margin:0 0 14px}
.note{background:#1e293b;border-left:4px solid var(--amber);padding:12px 14px;border-radius:8px;font-size:.92rem}
.note b{color:var(--amber)}
.bar{max-width:1100px;margin:0 auto;padding:0 16px 12px;display:flex;gap:8px;align-items:center;flex-wrap:wrap}
.bar button{background:#1e293b;color:var(--text);border:1px solid #334155;border-radius:8px;padding:8px 14px;font:inherit;cursor:pointer}
.bar button:hover{border-color:var(--amber)}
#scene{color:var(--amber);font-weight:600;margin-left:6px}
main{max-width:1100px;margin:0 auto;padding:0 16px;display:grid;grid-template-columns:3fr 2fr;gap:12px}
@media(max-width:820px){main{grid-template-columns:1fr}}
.pane{min-width:0;background:var(--pane);border:1px solid var(--line);border-radius:12px;overflow:hidden;display:flex;flex-direction:column}
.pane h2{margin:0;padding:10px 14px;font-size:.95rem;border-bottom:1px solid var(--line);color:var(--dim)}
.log{padding:12px;height:560px;overflow-y:auto;overflow-x:hidden;scroll-behavior:smooth}
@media(max-width:820px){.log{height:420px}}
.msg{display:flex;gap:10px;margin:0 0 12px}
.av{flex:0 0 34px;height:34px;border-radius:50%;display:grid;place-items:center;font-weight:700;color:#fff}
.body{min-width:0}
.meta{font-size:.82rem;color:var(--dim);display:flex;gap:6px;align-items:center;flex-wrap:wrap}
.meta b{color:var(--text)}
.badge{background:#4f46e5;color:#fff;border-radius:4px;padding:0 5px;font-size:.68rem;font-weight:700}
.chip{border:1px solid #475569;color:var(--dim);border-radius:10px;padding:0 7px;font-size:.68rem}
.chip.real{border-color:var(--green);color:#4ade80}
.txt{overflow-wrap:anywhere;font-size:.93rem}
.txt .h{font-weight:700;margin-top:6px}
.txt .gap{height:6px}
code{background:#1e293b;border-radius:4px;padding:0 4px}
.sys{color:var(--dim);font-size:.82rem;margin:0 0 12px 44px}
.divider{margin:14px 0;text-align:center;color:var(--amber);font-size:.82rem;border-top:1px solid var(--line);padding-top:8px}
.card{background:var(--card);color:var(--ink);border-radius:12px;padding:12px 14px;margin:0 6px 14px 44px;min-width:0;box-shadow:0 2px 10px #0006}
.card h3{margin:0 0 6px;font-size:.98rem}
.card .detail{white-space:pre-wrap;font-size:.85rem;color:#334155;margin-bottom:10px}
.btns{display:flex;gap:8px;flex-wrap:wrap}
.btns button{border:0;border-radius:8px;padding:8px 14px;font:inherit;font-weight:600;cursor:pointer;background:#cbd5e1;color:var(--ink)}
.btns button.first{background:var(--green);color:#fff}
.btns button.chosen{outline:3px solid #2563eb}
.btns button.dim{opacity:.35}
.tapped{margin-top:8px;font-size:.82rem;color:#2563eb;font-weight:600}
.card.gone{opacity:.45}
footer{color:var(--dim);font-size:.88rem}
</style>
</head>
<body>
<header>
  <h1>CareCircle: interactive replay</h1>
  <p class="lead">Three siblings, three cities, one Ma. <b>AI reads and writes, code checks and keeps the records, people decide.</b></p>
  <div class="note"><b>This is a recorded replay, not the live system.</b> CareCircle runs in Discord on a family's own machine. The replay below comes from running the project's real <code>@ledger</code> and <code>@pillbox</code> code offline (<code>uv run carecircle demo</code>). Each message is tagged <span class="chip real">real</span> (produced by that code) or <span class="chip">scripted</span> (people's messages and taps, and the two Claude Code agents <code>@meds</code> and <code>@coordinator</code>). Every name and number is fictional. Not medical advice.</div>
</header>
<div class="bar">
  <button id="restart" type="button">⟲ Restart</button>
  <button id="step" type="button">Step ▶</button>
  <button id="play" type="button">⏸ Pause</button>
  <span id="scene"></span>
</div>
<main>
  <section class="pane"><h2># sharma-circle <span style="opacity:.6">(the siblings and the agents)</span></h2><div class="log" id="log-sharma-circle" role="log" aria-live="polite"></div></section>
  <section class="pane"><h2># sharma-ma <span style="opacity:.6">(Ma's room)</span></h2><div class="log" id="log-sharma-ma" role="log" aria-live="polite"></div></section>
</main>
<footer>
  <p>Code, tests and the one-click Switch template: <a href="__REPO__">github.com/abhi-0404/carecircle</a> · Try it yourself: <code>git clone __REPO__ &amp;&amp; cd carecircle &amp;&amp; uv sync &amp;&amp; uv run carecircle demo</code></p>
  <p>Built on <a href="https://github.com/sandbox-quantum/switch">Switch</a> for the Flip the Switch hackathon (Track 02). #HowISwitch</p>
</footer>
<script>
const EVENTS = __DATA__;
const logs = {"sharma-circle": document.getElementById("log-sharma-circle"), "sharma-ma": document.getElementById("log-sharma-ma")};
const COLORS = {ledger:"#0ea5e9", pillbox:"#a855f7", meds:"#f97316", coordinator:"#14b8a6", Ankit:"#e11d48", Priya:"#db2777", Rahul:"#2563eb", "Cousin Vikram":"#6b7280"};
const DELAY = {scene:900, say:1300, card:1900, tap:1100, note:900};
let i = 0, playing = true, timer = null, open = [];

function esc(s){ return s.replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c])); }
function fmt(text){
  return text.split("\n").map(line => {
    if (!line.trim()) return '<div class="gap"></div>';
    if (/^#{1,2} /.test(line)) return '<div class="h">' + esc(line.replace(/^#{1,2} /, "")) + "</div>";
    return "<div>" + esc(line).replace(/\*\*(.+?)\*\*/g, "<b>$1</b>").replace(/`([^`]+)`/g, "<code>$1</code>").replace(/^- /, "• ").replace(/^_(.+)_$/, "<i>$1</i>") + "</div>";
  }).join("");
}
function put(room, el){ const log = logs[room]; log.appendChild(el); log.scrollTop = log.scrollHeight; }
function chip(real){ return real ? '<span class="chip real">real</span>' : '<span class="chip">scripted</span>'; }

function addSay(ev){
  const d = document.createElement("div"); d.className = "msg";
  d.innerHTML = '<span class="av" style="background:' + (COLORS[ev.who] || "#475569") + '">' + esc(ev.who[0].toUpperCase()) + '</span>' +
    '<div class="body"><div class="meta"><b>' + (ev.agent ? "@" : "") + esc(ev.who) + "</b>" + (ev.agent ? '<span class="badge">APP</span>' : "") + chip(ev.real) +
    '</div><div class="txt">' + fmt(ev.text) + "</div></div>";
  put(ev.room, d);
}
function addNote(ev){
  const d = document.createElement("div"); d.className = "sys"; d.textContent = ev.text; put(ev.room, d);
  if (/withdrawn/.test(ev.text)) {
    const idx = open.map(c => c.ev.room).lastIndexOf(ev.room);
    if (idx >= 0) { open[idx].el.classList.add("gone"); open.splice(idx, 1); }
  }
}
function addCard(ev){
  const el = document.createElement("div"); el.className = "card";
  el.innerHTML = '<div class="meta" style="color:#64748b">card from <b style="color:#0f172a">@' + esc(ev.who) + "</b> " + chip(ev.real) + "</div><h3>" + esc(ev.title) + "</h3>" +
    (ev.detail ? '<div class="detail">' + esc(ev.detail) + "</div>" : "") + '<div class="btns"></div>';
  const btns = el.querySelector(".btns");
  ev.options.forEach((label, n) => {
    const b = document.createElement("button"); b.type = "button"; b.textContent = label; if (/approve|taken|call/i.test(label)) b.className = "first";
    b.addEventListener("click", () => { if (open.length && open[open.length - 1].el === el && EVENTS[i] && EVENTS[i].t === "tap") { stopPlaying(); step(); } });
    btns.appendChild(b);
  });
  put(ev.room, el); open.push({el, ev});
}
function addTap(ev){
  const c = open.pop(); if (!c) return;
  c.el.querySelectorAll("button").forEach(b => b.classList.add(b.textContent === ev.label ? "chosen" : "dim"));
  const t = document.createElement("div"); t.className = "tapped"; t.textContent = "👆 " + ev.who + " tapped “" + ev.label + "”"; c.el.appendChild(t);
}
function step(){
  if (i >= EVENTS.length) return false;
  const ev = EVENTS[i++];
  if (ev.t === "scene") { document.getElementById("scene").textContent = ev.title;
    const d = document.createElement("div"); d.className = "divider"; d.textContent = ev.title; put("sharma-circle", d); }
  else if (ev.t === "say") addSay(ev);
  else if (ev.t === "note") addNote(ev);
  else if (ev.t === "card") addCard(ev);
  else if (ev.t === "tap") addTap(ev);
  return ev;
}
function loop(){ clearTimeout(timer); if (!playing) return;
  const ev = step(); if (!ev) { setPlaying(false); return; }
  timer = setTimeout(loop, DELAY[ev.t] || 1000); }
function setPlaying(p){ playing = p; document.getElementById("play").textContent = p ? "⏸ Pause" : (i >= EVENTS.length ? "✓ Done" : "▶ Play"); if (p) loop(); else clearTimeout(timer); }
function stopPlaying(){ setPlaying(false); }
function restart(){ clearTimeout(timer); Object.values(logs).forEach(l => l.innerHTML = ""); i = 0; open = []; document.getElementById("scene").textContent = ""; setPlaying(true); }

document.getElementById("restart").onclick = restart;
document.getElementById("step").onclick = () => { stopPlaying(); step(); };
document.getElementById("play").onclick = () => { if (i >= EVENTS.length) restart(); else setPlaying(!playing); };
if (location.hash === "#end") { playing = false; while (step()) {} document.getElementById("play").textContent = "⟲ Replay"; document.getElementById("play").onclick = restart; }
else setTimeout(loop, 600);
</script>
</body>
</html>
"""


def main() -> None:
    data = json.dumps(asyncio.run(events()), ensure_ascii=False).replace("</", "<\\/")
    page = PAGE.replace("__DATA__", data).replace("__SITE__", SITE).replace("__REPO__", REPO)
    out = ROOT / "docs" / "index.html"
    out.write_text(page, encoding="utf-8")
    (ROOT / "docs" / ".nojekyll").write_text("", encoding="utf-8")
    print(f"wrote {out} ({len(page):,} bytes)")


if __name__ == "__main__":
    main()
