"""Build docs/index.html: an interactive replay of the CareCircle story (served by GitHub Pages).

    uv run python demo/make_replay.py

The events come from running the real @ledger and @pillbox code offline
(carecircle.demo.events). The page is a recording, not the live system, and says
so; agent messages carry a green dot when that code produced them. No external
scripts, fonts or trackers: the Inter font is self-hosted (docs/assets/fonts).
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
<meta name="description" content="Three siblings, three cities, one Ma. AI reads and writes, code checks and keeps the records, people decide. A recorded replay of the real agents.">
<meta property="og:title" content="CareCircle: interactive replay">
<meta property="og:description" content="Siblings share an aging parent's care in one Switch room: AI proposes, plain code checks, a sibling taps Approve.">
<meta property="og:image" content="__SITE__/assets/linkedin.png">
<link rel="preload" href="assets/fonts/inter-latin-wght-normal.woff2" as="font" type="font/woff2" crossorigin>
<style>
@font-face{font-family:"Inter";src:url("assets/fonts/inter-latin-wght-normal.woff2") format("woff2");font-weight:100 900;font-style:normal;font-display:swap}
:root{--ink:#0f1b3a;--muted:#6b7a99;--line:#e7ecf6;--blue:#3b82f6;--blue2:#5aa2ff;--soft:#eaf2ff;--green:#16a34a;--rose:#f43f5e;--shadow:0 12px 32px rgba(31,64,140,.10)}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{margin:0;color:var(--ink);font:15px/1.5 Inter,"Segoe UI Variable Text","Segoe UI",system-ui,-apple-system,Roboto,sans-serif;min-height:100vh;
  background:radial-gradient(900px 500px at 12% -10%,#fff,transparent 60%),linear-gradient(180deg,#eef2fb,#e2e8f6)}
button{font:inherit;color:inherit}
a{color:var(--blue)}
:focus-visible{outline:3px solid #93c5fd;outline-offset:2px}
.stage{padding:24px 16px 18px;display:flex;flex-direction:column;align-items:center;gap:14px}
.app{width:min(1280px,100%);height:min(800px,calc(100vh - 84px));min-height:640px;display:grid;grid-template-columns:248px 340px minmax(0,1fr);
  background:#f6f8fe;border-radius:28px;box-shadow:0 30px 80px rgba(31,64,140,.16);overflow:hidden}

/* sidebar */
.side{background:#fff;padding:26px 18px 18px;display:flex;flex-direction:column;gap:18px;min-height:0}
.brand{display:flex;gap:11px;align-items:center}
.logo{width:40px;height:40px;border-radius:13px;background:linear-gradient(135deg,#3b82f6,#7aa8ff);display:grid;place-items:center;box-shadow:0 8px 18px rgba(59,130,246,.35)}
.brand b{display:block;font-size:17px;letter-spacing:-.01em}
.brand small{color:var(--muted);font-size:12px}
.family{display:flex;flex-direction:column;gap:8px;align-items:flex-start;background:#f4f7fd;border-radius:16px;padding:12px}
.stack{display:flex}
.stack .av{width:28px;height:28px;font-size:12px;border:2px solid #f4f7fd;margin-left:-8px}
.stack .av:first-child{margin-left:0}
.family b{font-size:13px;display:block}
.family small{font-size:11.5px;color:var(--muted)}
.navlabel{font-size:11px;letter-spacing:.08em;color:var(--muted);font-weight:650;margin:2px 0 8px 6px}
#chapters{list-style:none;margin:0;padding:0;display:flex;flex-direction:column;gap:2px}
.ch{display:flex;align-items:center;gap:10px;padding:10px;border-radius:12px;cursor:pointer;border:0;background:none;width:100%;text-align:left;position:relative;color:#41507a;font-weight:560;font-size:14px}
.ch:hover{background:#f4f7fd}
.ch .n{width:24px;height:24px;border-radius:50%;background:#eef2fb;display:grid;place-items:center;font-size:12px;font-weight:700;color:#5b6b92;flex:none}
.ch.active{color:var(--blue);background:var(--soft)}
.ch.active::before{content:"";position:absolute;left:-18px;top:8px;bottom:8px;width:4px;border-radius:0 4px 4px 0;background:var(--blue)}
.ch.active .n{background:var(--blue);color:#fff}
.ch.done .n{background:#dcfce7;color:var(--green)}
.side-foot{margin-top:auto;display:flex;flex-direction:column;gap:10px}
.legend{font-size:12px;color:var(--muted);background:#f4f7fd;border-radius:14px;padding:10px 12px;line-height:1.5}
.legend p{margin:0 0 3px}
.dot{display:inline-block;width:9px;height:9px;border-radius:50%;vertical-align:-1px;margin-right:4px}
.dot.real{background:var(--green)}
.dot.fake{border:2px solid #a5b1cc}
.linkbtn{display:flex;gap:8px;align-items:center;justify-content:center;padding:10px;border-radius:12px;background:var(--ink);color:#fff;text-decoration:none;font-weight:600;font-size:13px}
.copy{border:1px dashed #b9c6e4;background:#fff;border-radius:12px;padding:8px 10px;font:12px ui-monospace,Consolas,monospace;color:#41507a;cursor:pointer;text-align:left}

/* middle list */
.list{padding:26px 18px 0;display:flex;flex-direction:column;min-height:0}
.listhead{display:flex;justify-content:space-between;align-items:flex-start;gap:10px}
.list h2{margin:0;font-size:28px;letter-spacing:-.02em;line-height:1.15}
.list .sub{color:var(--muted);font-size:13px;margin-top:2px}
.cta{border:0;border-radius:12px;padding:11px 16px;background:linear-gradient(135deg,#3b82f6,#6aa9ff);color:#fff;font-weight:650;cursor:pointer;box-shadow:0 10px 22px rgba(59,130,246,.35);white-space:nowrap}
.seg{display:flex;background:#fff;border-radius:14px;padding:4px;margin:18px 0 8px;box-shadow:var(--shadow)}
.seg button{flex:1;border:0;background:none;padding:9px;border-radius:10px;font-weight:600;color:var(--muted);cursor:pointer}
.seg button.on{background:var(--soft);color:var(--blue)}
.listbody{flex:1;min-height:0}
.listbody .scroll{height:100%}
.scroll{overflow-y:auto;overflow-x:hidden;scroll-behavior:smooth;scrollbar-width:thin;scrollbar-color:#cfd8ee transparent}
.ghost{padding-top:22px;padding-bottom:72px;
  -webkit-mask-image:linear-gradient(to bottom,transparent 0,#000 24px,#000 calc(100% - 72px),transparent 100%);
  mask-image:linear-gradient(to bottom,transparent 0,#000 24px,#000 calc(100% - 72px),transparent 100%)}
.row{display:flex;gap:12px;align-items:center;padding:12px;margin:0 2px 10px;background:#fff;border-radius:18px;box-shadow:var(--shadow);border:2px solid transparent}
.row.room{cursor:pointer}
.row.room.active{border-color:var(--blue2)}
.row .m{min-width:0;flex:1}
.row b{font-size:14.5px;display:block}
.row small{display:block;color:var(--muted);font-size:12.5px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.row small .st{color:var(--blue);font-weight:600}
.row.speaking{border-color:#a9c8ff;--x:4px}
.row.off{opacity:.55}
.badge{background:var(--rose);color:#fff;border-radius:99px;min-width:20px;height:20px;padding:0 6px;display:grid;place-items:center;font-size:11px;font-weight:700}
.badge[hidden]{display:none}
.tag{font-size:10.5px;font-weight:700;border-radius:99px;padding:2px 8px;margin-left:6px;vertical-align:1px;white-space:nowrap}
.tag.claude{background:#f3e8ff;color:#7e22ce}
.tag.code{background:#dcfce7;color:#15803d}
.tag.sibling{background:#e0ecff;color:#1d4ed8}
.tag.outside{background:#eef0f4;color:#64748b}
.av{width:42px;height:42px;border-radius:50%;display:grid;place-items:center;color:#fff;font-weight:700;flex:none}
.av.agent{border-radius:13px}
.groupname{font-size:11px;letter-spacing:.08em;color:var(--muted);font-weight:650;margin:6px 6px 10px}

/* conversation */
.chat{margin:16px 16px 16px 0;background:#fff;border-radius:22px;box-shadow:var(--shadow);display:flex;flex-direction:column;min-width:0;min-height:0;overflow:hidden}
.chead{display:flex;align-items:center;gap:12px;padding:16px 20px;border-bottom:1px solid var(--line)}
.chead .t{min-width:0;flex:1}
.chead b{display:block;font-size:16px}
.chead small{color:var(--blue);font-weight:550;font-size:12.5px}
.iconbtn{width:40px;height:40px;border-radius:50%;border:0;background:#fff;box-shadow:0 4px 14px rgba(31,64,140,.14);cursor:pointer;display:grid;place-items:center;color:#41507a}
.tabs{display:none;gap:6px}
.tabs button{border:0;background:#eef2fb;border-radius:99px;padding:6px 12px;font-weight:600;font-size:12.5px;color:var(--muted);cursor:pointer}
.tabs button.on{background:var(--soft);color:var(--blue)}
.caption{margin:12px 20px 0;padding:10px 14px;border-radius:14px;background:var(--soft);color:#1e3a8a;font-size:13.5px;line-height:1.45}
.caption b{margin-right:6px}
.panes{position:relative;flex:1;min-height:0}
.pane{position:absolute;inset:0;padding:0 20px;opacity:0;pointer-events:none;transition:opacity .25s}
.pane.on{opacity:1;pointer-events:auto}
.pane .scroll{height:100%}
.msg{display:flex;gap:10px;margin:0 0 14px;max-width:90%}
.msg.me{margin-left:auto;flex-direction:row-reverse}
.bubble{background:#f2f6ff;border-radius:6px 18px 18px 18px;padding:10px 14px;min-width:0}
.msg.me .bubble{background:linear-gradient(135deg,#3b82f6,#5aa2ff);color:#fff;border-radius:18px 6px 18px 18px;box-shadow:0 8px 20px rgba(59,130,246,.28)}
.who{font-size:12px;font-weight:650;margin-bottom:2px;display:flex;align-items:center;gap:4px;flex-wrap:wrap}
.msg.me .who{color:#dbeafe;justify-content:flex-end}
.txt{overflow-wrap:anywhere;font-size:14.5px}
.txt .h{font-weight:700;margin-top:6px}
.txt .gap{height:6px}
.txt code{background:rgba(15,27,58,.07);border-radius:5px;padding:0 4px;font-size:.92em}
.msg.me .txt code{background:rgba(255,255,255,.2)}
.typing{display:inline-flex;gap:4px;padding:13px 15px;background:#f2f6ff;border-radius:6px 18px 18px 18px}
.typing i{width:6px;height:6px;border-radius:50%;background:#9db2dd;animation:bounce 1s infinite}
.typing i:nth-child(2){animation-delay:.15s}
.typing i:nth-child(3){animation-delay:.3s}
@keyframes bounce{0%,60%,100%{transform:none;opacity:.5}30%{transform:translateY(-4px);opacity:1}}
.card{margin:0 0 14px 52px;background:#fff;border:1px solid var(--line);border-radius:18px;padding:14px 16px;box-shadow:0 12px 28px rgba(31,64,140,.12);max-width:560px}
.card .k{font-size:11px;font-weight:700;letter-spacing:.06em;color:var(--muted);text-transform:uppercase;display:flex;gap:4px;align-items:center;flex-wrap:wrap}
.card h3{margin:4px 0 6px;font-size:16px;line-height:1.3}
.card .detail{white-space:pre-wrap;color:#4a5a80;font-size:13px;margin-bottom:12px}
.btns{display:flex;gap:8px;flex-wrap:wrap}
.btns button{border:0;border-radius:11px;padding:9px 16px;font-weight:650;cursor:pointer;background:#eef2fb;color:#41507a;transition:transform .15s}
.btns button:hover{transform:translateY(-1px)}
.btns button.go{background:linear-gradient(135deg,#3b82f6,#5aa2ff);color:#fff;box-shadow:0 8px 18px rgba(59,130,246,.3)}
.btns button.chosen{outline:3px solid #93c5fd}
.btns button.dim{opacity:.35}
.btns button.pulse{animation:pulse 1.4s infinite}
@keyframes pulse{0%{box-shadow:0 0 0 0 rgba(59,130,246,.55)}70%{box-shadow:0 0 0 12px rgba(59,130,246,0)}100%{box-shadow:0 0 0 0 rgba(59,130,246,0)}}
.card.gone{opacity:.5}
.tapchip{margin:-6px 0 14px auto;width:fit-content;background:linear-gradient(135deg,#3b82f6,#5aa2ff);color:#fff;border-radius:99px;padding:5px 12px;font-size:12.5px;font-weight:600}
.sys{text-align:center;color:var(--muted);font-size:12.5px;margin:0 0 14px}
.divider{display:flex;align-items:center;gap:10px;color:var(--blue);font-weight:650;font-size:12.5px;margin:18px 0 14px}
.divider::before,.divider::after{content:"";flex:1;height:1px;background:var(--line)}
.item,.row{opacity:calc(.2 + .8*var(--g,1));transform:translateX(var(--x,0)) scale(calc(.95 + .05*var(--g,1)));transition:opacity .25s,transform .25s,border-color .2s}
.item{animation:pop .4s ease backwards}
@keyframes pop{from{opacity:0;transform:translateY(12px)}to{opacity:1;transform:none}}
.empty{display:grid;place-items:center;text-align:center;height:100%;color:var(--muted);line-height:1.5}
.empty b{display:block;color:var(--ink);font-size:17px;margin-bottom:4px}
.dock{border-top:1px solid var(--line);padding:12px 20px 16px;display:flex;flex-direction:column;gap:10px}
.bar{height:4px;background:#e9eef9;border-radius:99px;overflow:hidden}
.bar i{display:block;height:100%;width:0;background:linear-gradient(90deg,#3b82f6,#7ab0ff);transition:width .4s}
.ctrl{display:flex;align-items:center;gap:10px}
.hint{flex:1;color:var(--muted);font-size:13.5px;min-width:0}
.send{width:46px;height:46px;border-radius:50%;border:0;background:linear-gradient(135deg,#3b82f6,#6aa9ff);color:#fff;cursor:pointer;display:grid;place-items:center;box-shadow:0 10px 22px rgba(59,130,246,.4)}
.foot{max-width:1280px;color:#5b6b92;font-size:12.5px;text-align:center;margin:0}

@media(max-width:1100px){.app{grid-template-columns:220px minmax(0,1fr)}.list{display:none}.tabs{display:flex}.chead .t small{display:none}}
@media(max-width:760px){
  .app{grid-template-columns:minmax(0,1fr);height:auto;min-height:0;border-radius:22px}
  .side{min-width:0}
  .side{padding:16px;gap:10px}
  .family,.navlabel,.side-foot{display:none}
  #chapters{flex-direction:row;overflow-x:auto;gap:6px;padding-bottom:2px}
  .ch{width:auto;white-space:nowrap;padding:8px 12px;background:#f4f7fd}
  .ch.active::before{display:none}
  .chat{margin:0 10px 12px;height:76vh;min-height:540px}
  .card{margin-left:0}
  .msg{max-width:100%}
}
@media(prefers-reduced-motion:reduce){*{animation:none!important;scroll-behavior:auto!important;transition:none!important}.item,.row{opacity:1!important;transform:none!important}}
</style>
</head>
<body>
<div class="stage">
<div class="app">
  <aside class="side">
    <div class="brand"><span class="logo"><svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="#fff" stroke-width="2" aria-hidden="true"><circle cx="9" cy="12" r="6"/><circle cx="15" cy="12" r="6"/></svg></span><div><b>CareCircle</b><small>Interactive replay</small></div></div>
    <div class="family"><div class="stack" id="stack"></div><div><b>The Sharma family</b><small>3 siblings · Ma · 5 agents</small></div></div>
    <nav aria-label="Story scenes"><div class="navlabel">THE STORY · 5 SHORT SCENES</div><ol id="chapters"></ol></nav>
    <div class="side-foot">
      <div class="legend"><p><span class="dot real"></span>Produced by the real code</p><p><span class="dot fake"></span>Scripted in this replay</p><p>Recorded replay, not the live system. Fictional data. Not medical advice.</p></div>
      <button class="copy" id="copy" type="button" title="Copy the command">$ uv run carecircle demo</button>
      <a class="linkbtn" href="__REPO__">View the code on GitHub</a>
    </div>
  </aside>

  <section class="list" aria-label="Rooms and people">
    <div class="listhead"><div><h2>Rooms</h2><div class="sub">Who is talking to whom</div></div><button class="cta" id="cta" type="button">▶ Play story</button></div>
    <div class="seg" role="tablist"><button class="on" id="seg-rooms" type="button">Rooms</button><button id="seg-who" type="button">Who's here</button></div>
    <div class="listbody"><div class="scroll ghost" id="listscroll"></div></div>
  </section>

  <section class="chat" aria-label="Conversation">
    <div class="chead">
      <span class="av" id="hav" style="background:linear-gradient(135deg,#3b82f6,#7aa8ff);border-radius:14px">#</span>
      <div class="t"><b id="htitle"># sharma-circle</b><small id="hsub">Siblings and agents</small></div>
      <div class="tabs" id="tabs"></div>
      <button class="iconbtn" id="restart" type="button" aria-label="Restart" title="Restart"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 12a9 9 0 1 0 3-6.7"/><path d="M3 4v5h5"/></svg></button>
    </div>
    <div class="caption" id="caption"><b>Welcome.</b>Three siblings share their mother's care in one chat. Press play and watch.</div>
    <div class="panes">
      <div class="pane on" id="pane-sharma-circle"><div class="scroll ghost" id="log-sharma-circle" role="log" aria-live="polite"></div></div>
      <div class="pane" id="pane-sharma-ma"><div class="scroll ghost" id="log-sharma-ma" role="log" aria-live="polite"></div></div>
    </div>
    <div class="dock">
      <div class="bar" aria-hidden="true"><i id="bar"></i></div>
      <div class="ctrl">
        <div class="hint" id="hint">Press ▶ to watch, or pick a scene on the left.</div>
        <button class="iconbtn" id="step" type="button" aria-label="Next step" title="Next step"><svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor"><path d="M6 5l9 7-9 7V5zM17 5h2v14h-2z"/></svg></button>
        <button class="send" id="play" type="button" aria-label="Play"></button>
      </div>
    </div>
  </section>
</div>
<p class="foot">A recording of the project's real <code>@ledger</code> and <code>@pillbox</code> code run offline (<code>uv run carecircle demo</code>); the Claude agents and the people are scripted. Built on <a href="https://github.com/sandbox-quantum/switch">Switch</a> for the Flip the Switch hackathon · #HowISwitch</p>
</div>
<script>
const EVENTS = __DATA__;
const FAMILY = "sharma-circle", MA = "sharma-ma";
const REPO = "__REPO__";
const ROOMS = {
  "sharma-circle": {title: "# sharma-circle", sub: "Siblings and agents", short: "Family room", letter: "#"},
  "sharma-ma": {title: "# sharma-ma", sub: "Ma's room: only her medicines and visits", short: "Ma's room", letter: "M"}
};
const CAPTIONS = [
  ["A shared bill", "Ankit logs ₹2,400 for Ma's lab tests. He can't approve his own expense (that rule is code, not a prompt), so Rahul confirms."],
  ["A new prescription", "Claude reads the photo. Plain code checks every line before a sibling approves. A cousin outside the family can't."],
  ["Who takes Ma?", "One tap decides, and Ma hears about it in her own room."],
  ["A missed dose", "Nobody confirmed? The family is told, and someone has to say “I'll call”."],
  ["Settle up", "Exact to the paisa: who pays whom."]
];
const PEOPLE = {
  "Ankit": {color: "#f43f5e", type: "sibling", sub: "Paid the lab bill"}, "Priya": {color: "#ec4899", type: "sibling", sub: "Sends the prescription"},
  "Rahul": {color: "#2563eb", type: "sibling", sub: "Confirms, takes Ma to the doctor"}, "Cousin Vikram": {color: "#94a3b8", type: "outside", sub: "Not on the family list"}
};
const AGENTS = {
  ledger: {color: "#0ea5e9", kind: "code", sub: "Keeps the money"}, pillbox: {color: "#8b5cf6", kind: "code", sub: "Keeps Ma's medicines"},
  meds: {color: "#f97316", kind: "claude", sub: "Reads prescriptions"}, coordinator: {color: "#14b8a6", kind: "claude", sub: "Plans visits"},
  scribe: {color: "#94a3b8", kind: "claude", sub: "Care log (not in this replay)", off: true}
};
const TAGS = {sibling: ["sibling", "Sibling"], outside: ["outside", "Outside"], claude: ["claude", "Claude"], code: ["code", "Plain code"]};
const DELAY = {scene: 1100, say: 1500, card: 2300, tap: 1300, note: 1100};
const SCENES = EVENTS.map((e, n) => e.t === "scene" ? n : -1).filter(n => n >= 0);
const ICON_PLAY = '<svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor"><path d="M7 4.5v15l13-7.5z"/></svg>';
const ICON_PAUSE = '<svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor"><path d="M6 4h4v16H6zM14 4h4v16h-4z"/></svg>';

const $ = id => document.getElementById(id);
const logs = {[FAMILY]: $("log-sharma-circle"), [MA]: $("log-sharma-ma")};
const panes = {[FAMILY]: $("pane-sharma-circle"), [MA]: $("pane-sharma-ma")};
let i = 0, playing = false, token = 0, open = [], current = FAMILY, follow = true, instant = false, active = -1, view = "rooms", typingEl = null;
const unread = {[FAMILY]: 0, [MA]: 0}, preview = {[FAMILY]: "No messages yet", [MA]: "No messages yet"};

const sleep = ms => new Promise(r => setTimeout(r, ms));
const esc = s => s.replace(/[&<>"]/g, c => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;"}[c]));
function el(tag, cls, html){ const d = document.createElement(tag); if (cls) d.className = cls; if (html != null) d.innerHTML = html; return d; }
function fmt(text){
  return text.split("\n").map(line => {
    if (!line.trim()) return '<div class="gap"></div>';
    if (/^#{1,2} /.test(line)) return '<div class="h">' + esc(line.replace(/^#{1,2} /, "")) + "</div>";
    return "<div>" + esc(line).replace(/\*\*(.+?)\*\*/g, "<b>$1</b>").replace(/`([^`]+)`/g, "<code>$1</code>").replace(/^- /, "• ").replace(/^_(.+)_$/, "<i>$1</i>") + "</div>";
  }).join("");
}
function firstLine(t){ const l = t.split("\n").find(x => x.trim() && !/^#/.test(x)) || t; return l.replace(/[*`_]/g, "").slice(0, 64); }
function info(name){ return AGENTS[name] || PEOPLE[name] || {color: "#64748b"}; }
function avatar(name){ const a = !!AGENTS[name]; return '<span class="av' + (a ? " agent" : "") + '" style="background:' + info(name).color + '">' + esc(name.replace(/^Cousin /, "")[0].toUpperCase()) + "</span>"; }
function tagHTML(name){ const a = AGENTS[name]; const t = a ? TAGS[a.kind] : TAGS[(PEOPLE[name] || {}).type]; return t ? '<span class="tag ' + t[0] + '">' + t[1] + "</span>" : ""; }
function dotHTML(ev){ return '<span class="dot ' + (ev.real ? "real" : "fake") + '" title="' + (ev.real ? "Produced by the real code" : "Scripted in this replay") + '"></span>'; }
function nameHTML(ev){ return ev.agent ? "@" + esc(ev.who) + tagHTML(ev.who) + dotHTML(ev) : esc(ev.who); }

/* ----- static parts ----- */
["Ankit", "Priya", "Rahul"].forEach(n => $("stack").insertAdjacentHTML("beforeend", avatar(n)));
SCENES.forEach((idx, k) => {
  const li = el("li"); const b = el("button", "ch", '<span class="n">' + (k + 1) + "</span>" + esc(CAPTIONS[k][0])); b.type = "button"; b.onclick = () => jump(k); li.appendChild(b); $("chapters").appendChild(li);
});
function renderList(){
  const box = $("listscroll"); box.innerHTML = ""; queueMicrotask(() => ghost(box));
  if (view === "rooms") {
    Object.keys(ROOMS).forEach(room => {
      const r = el("div", "row room" + (room === current ? " active" : ""), '<span class="av" style="background:linear-gradient(135deg,#3b82f6,#7aa8ff);border-radius:14px">' + ROOMS[room].letter + '</span><div class="m"><b>' + ROOMS[room].short + "</b><small>" + esc(preview[room]) + '</small></div><span class="badge"' + (unread[room] ? "" : " hidden") + ">" + unread[room] + "</span>");
      r.onclick = () => { follow = false; switchRoom(room); }; box.appendChild(r);
    });
  } else {
    [["PEOPLE", ["Ankit", "Priya", "Rahul", "Cousin Vikram"]], ["AGENTS", ["ledger", "pillbox", "meds", "coordinator", "scribe"]]].forEach(([g, names]) => {
      box.appendChild(el("div", "groupname", g));
      names.forEach(n => { const a = AGENTS[n], p = PEOPLE[n];
        const r = el("div", "row" + (a && a.off ? " off" : ""), avatar(n) + '<div class="m"><b>' + (a ? "@" : "") + esc(n) + tagHTML(n) + '</b><small data-st="' + esc(n) + '">' + esc((a || p).sub) + "</small></div>");
        r.dataset.who = n; box.appendChild(r); });
    });
  }
}
function setView(v){ view = v; $("seg-rooms").classList.toggle("on", v === "rooms"); $("seg-who").classList.toggle("on", v === "who"); renderList(); }
$("seg-rooms").onclick = () => setView("rooms"); $("seg-who").onclick = () => setView("who");
function renderTabs(){ const t = $("tabs"); t.innerHTML = ""; Object.keys(ROOMS).forEach(room => { const b = el("button", room === current ? "on" : "", ROOMS[room].short + (unread[room] ? " (" + unread[room] + ")" : "")); b.type = "button"; b.onclick = () => { follow = false; switchRoom(room); }; t.appendChild(b); }); }

function switchRoom(room){
  current = room; unread[room] = 0;
  Object.keys(panes).forEach(r => panes[r].classList.toggle("on", r === room));
  $("htitle").textContent = ROOMS[room].title; $("hsub").textContent = ROOMS[room].sub; $("hav").textContent = ROOMS[room].letter;
  renderList(); renderTabs();
  const lg = logs[room]; lg.scrollTo({top: lg.scrollHeight, behavior: "instant"}); ghost(lg);
}
function touch(room, text){ if (!room) return; preview[room] = text; if (room !== current) unread[room]++; renderList(); renderTabs(); }
function flash(name, text){
  const s = document.querySelector('[data-st="' + name + '"]'); if (!s) return; const row = s.closest(".row"); const def = (AGENTS[name] || PEOPLE[name]).sub;
  s.innerHTML = '<span class="st">' + text + "</span>"; row.classList.add("speaking");
  setTimeout(() => { s.textContent = def; row.classList.remove("speaking"); }, 1400);
}
function put(room, node, afterEl){ const lg = logs[room]; const e = lg.querySelector(".empty"); if (e) e.remove(); if (instant) { node.style.animation = "none"; node.style.transition = "none"; } if (afterEl) afterEl.insertAdjacentElement("afterend", node); else lg.appendChild(node); lg.scrollTo({top: lg.scrollHeight, behavior: instant ? "instant" : "smooth"}); ghost(lg); }

/* ----- ghost scrolling: items fade and shrink slightly as they leave the visible area ----- */
const EMPTY = '<div class="empty"><div><b>A family, one chat, five agents</b>Press ▶ to watch how they share Ma’s care.</div></div>';
function ghost(box){
  const L = box.getBoundingClientRect(), up = box.scrollTop > 4, down = box.scrollTop + box.clientHeight < box.scrollHeight - 4;
  box.querySelectorAll(".item,.row").forEach(n => {
    const r = n.getBoundingClientRect();
    const d = Math.min(up ? r.top - L.top : 999, down ? L.bottom - r.bottom - 60 : 999);
    n.style.setProperty("--g", Math.max(0, Math.min(1, d / 90 + 0.3)).toFixed(3));
  });
}
[logs[FAMILY], logs[MA], $("listscroll")].forEach(b => { let q = 0; b.addEventListener("scroll", () => { if (!q) q = requestAnimationFrame(() => { q = 0; ghost(b); }); }, {passive: true}); });

/* ----- events ----- */
function addSay(ev){
  const me = !ev.agent; const d = el("div", "msg item" + (me ? " me" : ""), avatar(ev.who) + '<div class="bubble"><div class="who">' + nameHTML(ev) + '</div><div class="txt">' + fmt(ev.text) + "</div></div>");
  put(ev.room, d); touch(ev.room, ev.who + ": " + firstLine(ev.text)); if (!instant) flash(ev.who, "typing…");
}
function addNote(ev){
  put(ev.room, el("div", "sys item", esc(ev.text)));
  if (/withdrawn/.test(ev.text)) { const idx = open.map(c => c.ev.room).lastIndexOf(ev.room); if (idx >= 0) { open[idx].el.classList.add("gone"); open.splice(idx, 1); } }
}
function addCard(ev){
  const c = el("div", "card item", '<div class="k">Approval card · @' + esc(ev.who) + tagHTML(ev.who) + dotHTML(ev) + "</div><h3>" + esc(ev.title) + "</h3>" + (ev.detail ? '<div class="detail">' + esc(ev.detail) + "</div>" : "") + '<div class="btns"></div>');
  const btns = c.querySelector(".btns");
  ev.options.forEach(label => {
    const b = el("button", /approve|taken|call/i.test(label) ? "go" : "", esc(label)); b.type = "button";
    b.onclick = () => { const top = open[open.length - 1]; if (top && top.el === c && EVENTS[i] && EVENTS[i].t === "tap") { pause(); step(false); run(); } };
    btns.appendChild(b);
  });
  put(ev.room, c); open.push({el: c, ev}); touch(ev.room, "Card: " + ev.title);
  const nxt = EVENTS[i]; if (nxt && nxt.t === "tap") [...btns.children].forEach(b => { if (b.textContent === nxt.label) b.classList.add("pulse"); });
}
function addTap(ev){
  const c = open.pop(); if (!c) return;
  c.el.querySelectorAll("button").forEach(b => { b.classList.remove("pulse"); b.classList.add(b.textContent === ev.label ? "chosen" : "dim"); });
  put(c.ev.room, el("div", "tapchip item", "👆 " + esc(ev.who) + " tapped “" + esc(ev.label) + "”"), c.el);
  if (!instant) flash(ev.who, "tapping…");
}
function setChapter(k){
  active = k; document.querySelectorAll(".ch").forEach((b, n) => { b.classList.toggle("active", n === k); b.classList.toggle("done", n < k); });
  $("caption").innerHTML = "<b>Scene " + (k + 1) + " of " + SCENES.length + ".</b>" + esc(CAPTIONS[k][1]);
}
function addScene(ev, idx){ const k = SCENES.indexOf(idx); setChapter(k); put(FAMILY, el("div", "divider item", "Scene " + (k + 1) + " · " + esc(CAPTIONS[k][0]))); }

function step(inst){
  if (i >= EVENTS.length) return null;
  instant = !!inst; const idx = i, ev = EVENTS[i++];
  const room = ev.room || (ev.t === "tap" && open.length ? open[open.length - 1].ev.room : null);
  if (room && follow && room !== current) switchRoom(room);
  if (ev.t === "scene") addScene(ev, idx); else if (ev.t === "say") addSay(ev); else if (ev.t === "note") addNote(ev); else if (ev.t === "card") addCard(ev); else if (ev.t === "tap") addTap(ev);
  instant = false; sync(); return ev;
}

/* ----- playback ----- */
function showTyping(ev){
  hideTyping(); typingEl = el("div", "msg item", avatar(ev.who) + '<div class="typing"><i></i><i></i><i></i></div>'); put(ev.room, typingEl);
}
function hideTyping(){ if (typingEl) { typingEl.remove(); typingEl = null; } }
async function run(){
  const my = ++token; playing = true; sync();
  while (playing && my === token && i < EVENTS.length) {
    const nxt = EVENTS[i];
    if (nxt.t === "say" && nxt.agent) {
      if (nxt.room !== current && follow) switchRoom(nxt.room);
      showTyping(nxt); flash(nxt.who, "typing…"); await sleep(750); hideTyping(); if (my !== token) return;
    }
    const ev = step(false); await sleep(DELAY[ev.t] || 1000);
  }
  if (my === token) { playing = false; sync(); }
}
function pause(){ token++; playing = false; hideTyping(); sync(); }
function resetDom(){
  Object.values(logs).forEach(l => l.innerHTML = ""); logs[FAMILY].innerHTML = EMPTY; open = []; i = 0; active = -1; follow = true; hideTyping();
  unread[FAMILY] = unread[MA] = 0; preview[FAMILY] = preview[MA] = "No messages yet";
  document.querySelectorAll(".ch").forEach(b => b.classList.remove("active", "done"));
  $("caption").innerHTML = "<b>Welcome.</b>Three siblings share their mother's care in one chat. Press play and watch.";
  switchRoom(FAMILY);
}
function restart(){ pause(); resetDom(); run(); }
function jump(k){ pause(); resetDom(); while (i < SCENES[k]) step(true); run(); }
function sync(){
  $("play").innerHTML = playing ? ICON_PAUSE : ICON_PLAY; $("play").setAttribute("aria-label", playing ? "Pause" : "Play");
  $("cta").textContent = playing ? "⏸ Pause" : (i >= EVENTS.length ? "⟲ Replay" : (i === 0 ? "▶ Play story" : "▶ Resume"));
  $("bar").style.width = (i / EVENTS.length * 100) + "%";
  $("hint").innerHTML = i >= EVENTS.length ? 'That is the story. Replay it, or <a href="' + REPO + '">open the code</a>.' :
    (playing ? "Playing · tap any glowing button to move on." : (i === 0 ? "Press ▶ to watch, or pick a scene on the left." : "Paused. Press ▶, or step one move at a time."));
}
$("play").onclick = $("cta").onclick = () => { if (i >= EVENTS.length) restart(); else if (playing) pause(); else run(); };
$("step").onclick = () => { pause(); if (i >= EVENTS.length) return; const ev = EVENTS[i]; if (ev.t === "say" && ev.agent && ev.room !== current && follow) switchRoom(ev.room); step(false); };
$("restart").onclick = restart;
document.addEventListener("keydown", e => { if (e.target.closest("button,a")) return; if (e.code === "Space") { e.preventDefault(); $("play").click(); } if (e.code === "ArrowRight") $("step").click(); });
$("copy").onclick = async () => { try { await navigator.clipboard.writeText("uv run carecircle demo"); $("copy").textContent = "Copied ✓"; setTimeout(() => $("copy").textContent = "$ uv run carecircle demo", 1500); } catch (e) {} };

/* ----- start ----- */
setView("rooms"); renderTabs(); sync(); logs[FAMILY].innerHTML = EMPTY;
const h = location.hash, upto = /^#upto=(\d+)/.exec(h); if (/who/.test(h)) setView("who");
if (h === "#end" || upto || matchMedia("(prefers-reduced-motion: reduce)").matches) {
  const n = upto ? Math.min(+upto[1], EVENTS.length) : EVENTS.length; while (i < n) step(true); sync();
  if (h === "#end") { follow = false; }
} else setTimeout(run, 700);
</script>
</body>
</html>
"""


def main() -> None:
    data = json.dumps(asyncio.run(events()), ensure_ascii=False).replace("</", "<\\/")
    page = PAGE.replace("__DATA__", data).replace("__SITE__", SITE).replace("__REPO__", REPO)
    out = ROOT / "docs" / "index.html"
    out.write_bytes(page.encode("utf-8"))  # bytes: keep LF line endings on Windows
    (ROOT / "docs" / ".nojekyll").write_bytes(b"")
    print(f"wrote {out} ({len(page):,} bytes)")


if __name__ == "__main__":
    main()
