"""Builds every image on the profile from live GitHub data.

Runs in GitHub Actions every 6 hours (see .github/workflows/refresh.yml).
No dependencies beyond the standard library.

    GITHUB_TOKEN=... python scripts/build.py
"""

from __future__ import annotations

import json
import math
import os
import re
import urllib.request
from datetime import datetime, timedelta, timezone
from html import escape
from pathlib import Path

USER = "krushna-sahu1"
ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
IST = timezone(timedelta(hours=5, minutes=30))

SANS = "Inter, -apple-system, 'Segoe UI', Helvetica, Arial, sans-serif"
MONO = "ui-monospace, SFMono-Regular, 'JetBrains Mono', Menlo, Consolas, monospace"

THEMES = {
    "dark": dict(bg="#0B0F14", panel="#10161E", line="#1F2935", grid="#1A232E",
                 text="#E8EEF4", dim="#7F8C9B", faint="#3A4757",
                 signal="#6EF2C9", gate="#FFB547"),
    "light": dict(bg="#FBFAF6", panel="#FFFFFF", line="#E3E0D6", grid="#ECE9E0",
                  text="#141920", dim="#5E6773", faint="#B9BDC4",
                  signal="#078A68", gate="#C26400"),
}

# The fleet. Every line here is taken from the project's own README.
FLEET = [
    dict(repo="unified-inbox", name="UNIFIED-INBOX", status="PLUGIN",
         purpose="WhatsApp, Instagram and LinkedIn in one Hermes inbox. Hermes drafts the reply. You send it.",
         pipe=["3 inboxes", "hermes", "draft", "send"], gate="your yes",
         rule="Nothing leaves without your yes.",
         stack="python · hermes agent · 461 offline tests"),
    dict(repo="agentic_dish", name="AGENTIC-DISH", status="LIVE",
         purpose="A restaurant site where conversation replaces clicking, for customers and for the owner.",
         pipe=["chat", "ai host", "cart", "paid"], gate="you tap pay",
         rule="The AI never pays. A DB trigger enforces it.",
         stack="next.js 15 · copilotkit · deepseek · supabase · razorpay"),
    dict(repo="lensbite", name="LENSBITE", status="LIVE",
         purpose="Point your camera at food and talk. A live voice agent estimates calories and reads labels.",
         pipe=["camera", "gemini live", "estimate", "logged"], gate="you confirm",
         rule="A meal is logged only when you confirm it.",
         stack="next.js · gemini live · supabase rls"),
    dict(repo="jarvix", name="JARVIX", status="LOCAL",
         purpose="A desktop agent that monitors, decides and controls your PC. Runs entirely on your machine.",
         pipe=["telegram", "ollama", "decide", "system"], gate="only you",
         rule="Zero cloud. No API keys. Your bot, your machine.",
         stack="python · ollama · telegram"),
    dict(repo="Loan_Agent", name="VOICELOAN", status="AGENT",
         purpose="Apply for a loan by talking. A voice agent keeps only the useful fields and scores the risk.",
         pipe=["voice", "deepgram", "risk score", "decision"], gate="admin",
         rule="Stores the fields, never the recording.",
         stack="next.js · deepgram · supabase"),
    dict(repo="PathoLab_Connects", name="PATHOLAB", status="LIVE",
         purpose="Patients, collection agents, sample tracking and reports for a pathology lab, in one platform.",
         pipe=["patient", "zone agent", "sample", "report"], gate="role check",
         rule="Every screen sits behind role-based access.",
         stack="next.js · twilio whatsapp · rbac"),
]

STACK = [
    ("SENSES", ["WhatsApp, Instagram", "LinkedIn, Gmail", "Telegram", "Deepgram voice", "Gemini Live camera", "PDFs and docs"]),
    ("BRAIN", ["Ollama, fully local", "DeepSeek", "Gemini", "Hermes Agent", "CopilotKit · AG-UI", "RAG over your docs"]),
    ("HANDS", ["Zod-typed tools", "role → check → audit", "no SQL from the model", "desktop control", "Chrome extension"]),
    ("GATE", ["Pay: a human click", "Send: after your yes", "Loans: admin decides", "Meals: you confirm", "backed by DB triggers"]),
    ("MEMORY", ["Supabase Postgres", "Row Level Security", "Realtime · pg_cron", "fields, not audio", "keys stay on server"]),
    ("SURFACE", ["Next.js 15 · React", "Tailwind v4", "Telegram as the UI", "Gmail compose bar", "Vercel"]),
]


# ---------------------------------------------------------------- data

def token() -> str | None:
    return os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")


def api(path: str, body: dict | None = None):
    url = path if path.startswith("http") else f"https://api.github.com/{path}"
    req = urllib.request.Request(url, data=json.dumps(body).encode() if body else None)
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("User-Agent", "profile-builder")
    if token():
        req.add_header("Authorization", f"Bearer {token()}")
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def fetch():
    repos = api(f"users/{USER}/repos?per_page=100&sort=pushed")
    own = [r for r in repos if not r["fork"] and r["name"] not in (USER,)]
    q = """{user(login:"%s"){contributionsCollection{contributionCalendar{
      totalContributions weeks{contributionDays{date contributionCount}}}}}}""" % USER
    cal = api("graphql", {"query": q})["data"]["user"]["contributionsCollection"]["contributionCalendar"]
    days = [(d["date"], d["contributionCount"]) for w in cal["weeks"] for d in w["contributionDays"]]
    return own, days, cal["totalContributions"]


# ---------------------------------------------------------------- svg helpers

def t(x, y, s, size, fill, family=SANS, weight=400, anchor="start", extra=""):
    return (f'<text x="{x}" y="{y}" font-family="{family}" font-size="{size}" '
            f'font-weight="{weight}" fill="{fill}" text-anchor="{anchor}" {extra}>{s}</text>')


def svg(w, h, body, c, label):
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="{escape(label)}">
<title>{escape(label)}</title>
<defs>
  <pattern id="dots" width="22" height="22" patternUnits="userSpaceOnUse"><circle cx="1" cy="1" r="1" fill="{c['grid']}"/></pattern>
  <filter id="glow" x="-200%" y="-200%" width="500%" height="500%"><feGaussianBlur stdDeviation="3.2" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
</defs>
<style>
  .spin {{ transform-box: fill-box; transform-origin: center; animation: spin 14s linear infinite; }}
  .spin-r {{ transform-box: fill-box; transform-origin: center; animation: spin 22s linear infinite reverse; }}
  .breathe {{ animation: breathe 3.6s ease-in-out infinite; }}
  .scan {{ animation: scan 7s linear infinite; }}
  .caret {{ animation: caret 1.1s steps(1) infinite; }}
  @keyframes spin {{ to {{ transform: rotate(360deg); }} }}
  @keyframes breathe {{ 0%,100% {{ opacity: .35; }} 50% {{ opacity: 1; }} }}
  @keyframes scan {{ from {{ transform: translateX(0); }} to {{ transform: translateX(1120px); }} }}
  @keyframes caret {{ 50% {{ opacity: 0; }} }}
  @media (prefers-reduced-motion: reduce) {{ * {{ animation: none !important; }} }}
</style>
<rect x="0.5" y="0.5" width="{w-1}" height="{h-1}" rx="16" fill="{c['bg']}" stroke="{c['line']}"/>
{body}
</svg>"""


def gate_anim(dur, hold=(0.45, 0.72)):
    """Opacity animation for a gate: dim, lights up while a pulse waits, dims again."""
    a, b = hold
    kt = f"0;{a - .01:.3f};{a + .01:.3f};{b:.3f};{b + .02:.3f};1"
    return (f'<animate attributeName="opacity" dur="{dur}s" repeatCount="indefinite" '
            f'keyTimes="{kt}" values=".3;.3;1;1;.3;.3"/>')


def pulse(path, frac, dur, color, r=4.5, hold=(0.45, 0.72)):
    """A dot that runs along `path`, waits at `frac` (the gate), then passes."""
    a, b = hold
    return (f'<circle r="{r}" fill="{color}" filter="url(#glow)">'
            f'<animateMotion dur="{dur}s" repeatCount="indefinite" calcMode="linear" '
            f'keyPoints="0;{frac:.4f};{frac:.4f};1" keyTimes="0;{a};{b};1" path="{path}"/>'
            f'<animate attributeName="opacity" dur="{dur}s" repeatCount="indefinite" '
            f'keyTimes="0;0.04;0.94;1" values="0;1;1;0"/></circle>')


def gate(x, y, h, c, dur, label=None, label_y=None):
    out = [f'<g>{gate_anim(dur)}',
           f'<rect x="{x - 9}" y="{y}" width="4" height="{h}" rx="2" fill="{c["gate"]}"/>',
           f'<rect x="{x + 5}" y="{y}" width="4" height="{h}" rx="2" fill="{c["gate"]}"/></g>']
    if label:
        out.append(t(x, label_y, escape(label), 13, c["gate"], MONO, 600, "middle", 'letter-spacing="0.5"'))
    return "".join(out)


# ---------------------------------------------------------------- hero

def hero(c, stats):
    W, H = 1200, 440
    now = stats["now"]
    shift = "night shift — agents on watch" if now.hour >= 22 or now.hour < 6 else "day shift"
    b = [f'<rect x="1" y="1" width="{W-2}" height="{H-2}" rx="16" fill="url(#dots)" opacity=".7"/>',
         t(48, 46, f'krushna-sahu1 <tspan fill="{c["faint"]}">/</tspan> field log', 14, c["dim"], MONO),
         t(W - 48, 46, f'last sync {now:%d %b · %H:%M} IST <tspan fill="{c["faint"]}">·</tspan> {shift}'.lower(),
           14, c["dim"], MONO, anchor="end"),
         f'<line x1="48" y1="66" x2="{W-48}" y2="66" stroke="{c["line"]}"/>',
         t(46, 158, "Krushna Sahu", 66, c["text"], SANS, 700, extra='letter-spacing="-2"'),
         t(48, 210, f'I build AI agents that <tspan fill="{c["gate"]}">ask before they act</tspan>.', 27, c["text"], SANS, 500),
         t(48, 256, "Inbox, restaurant, loans, food logging, desktop control.", 17, c["dim"]),
         t(48, 282, "The agent does the work. The step you can't undo waits for a human yes.", 17, c["dim"]),
         t(48, 322, f'<tspan fill="{c["signal"]}">$</tspan> open an issue titled /whoami to talk to this page'
           f'<tspan class="caret" fill="{c["signal"]}"> ▍</tspan>', 15, c["dim"], MONO)]

    # diagram: three senses -> agent core -> gate -> act
    dur = 4.8
    cx, cy, gx, ox = 940, 200, 1052, 1124
    ins = [("messages", 120), ("voice", 200), ("camera", 280)]
    for name, y in ins:
        b.append(f'<path d="M 836 {y} C 880 {y}, 880 {cy}, {cx - 46} {cy}" fill="none" stroke="{c["faint"]}" stroke-width="1.4"/>')
        b.append(f'<rect x="740" y="{y - 17}" width="96" height="34" rx="8" fill="{c["panel"]}" stroke="{c["line"]}"/>')
        b.append(t(788, y + 5, name, 13, c["dim"], MONO, anchor="middle"))
    b.append(f'<line x1="{cx + 46}" y1="{cy}" x2="{ox - 18}" y2="{cy}" stroke="{c["faint"]}" stroke-width="1.4"/>')
    b.append(f'<circle cx="{cx}" cy="{cy}" r="46" fill="{c["panel"]}" stroke="{c["line"]}"/>')
    b.append(f'<circle class="spin" cx="{cx}" cy="{cy}" r="56" fill="none" stroke="{c["signal"]}" stroke-width="1.2" stroke-dasharray="2 9" opacity=".8"/>')
    b.append(f'<circle class="spin-r" cx="{cx}" cy="{cy}" r="66" fill="none" stroke="{c["faint"]}" stroke-width="1" stroke-dasharray="30 14 4 14"/>')
    b.append(t(cx, cy + 5, "agent", 14, c["text"], MONO, 600, "middle"))
    b.append(gate(gx, cy - 36, 72, c, dur, "your yes", cy - 48))
    b.append(f'<circle cx="{ox}" cy="{cy}" r="16" fill="none" stroke="{c["signal"]}" stroke-width="1.4"/>')
    b.append(f'<circle class="breathe" cx="{ox}" cy="{cy}" r="6" fill="{c["signal"]}"/>')
    b.append(t(ox, cy + 44, "act", 13, c["dim"], MONO, anchor="middle"))
    for name, y in ins:
        # length-weighted fraction where the gate sits on this path
        curve = math.hypot(cx - 46 - 836, cy - y) * 1.08
        tail1, tail2 = gx - (cx + 46), ox - 18 - gx
        p = f"M 836 {y} C 880 {y}, 880 {cy}, {cx - 46} {cy} L {ox - 18} {cy}"
        b.append(pulse(p, (curve + tail1) / (curve + tail1 + tail2), dur, c["signal"]))

    # status bar
    b.append(f'<line x1="48" y1="362" x2="{W-48}" y2="362" stroke="{c["line"]}"/>')
    s = stats
    items = [(48, f'<tspan fill="{c["signal"]}" class="breathe">●</tspan> {len(FLEET)} agents in the fleet'),
             (318, f'{s["live"]} live on vercel'),
             (520, f'{s["total"]} contributions / 12 mo'),
             (800, f'last push → <tspan fill="{c["text"]}">{escape(s["last_repo"])}</tspan> · {s["last_ago"]}')]
    for x, txt in items:
        b.append(t(x, 404, txt, 15, c["dim"], MONO))
    return svg(W, H, "\n".join(b), c, "Krushna Sahu. I build AI agents that ask before they act.")


# ---------------------------------------------------------------- fleet card

def wrap(text, n):
    lines, cur = [], ""
    for w in text.split():
        if len(cur) + len(w) + 1 > n:
            lines.append(cur)
            cur = w
        else:
            cur = f"{cur} {w}".strip()
    return lines + [cur]


def card(i, f, c, repo):
    W, H = 600, 350
    dur = 4.2 + (i % 3) * 0.35
    status = f["status"]
    pill_c = c["signal"] if status == "LIVE" else c["dim"]
    pw = 18 + len(status) * 9 + 18
    b = [t(32, 52, f"{i + 1:02d}", 15, c["faint"], MONO, 600),
         t(66, 52, f["name"], 22, c["text"], MONO, 700, extra='letter-spacing="1"'),
         f'<rect x="{W - 32 - pw}" y="30" width="{pw}" height="28" rx="14" fill="none" stroke="{pill_c}" opacity=".7"/>',
         f'<circle class="{"breathe" if status == "LIVE" else ""}" cx="{W - 32 - pw + 15}" cy="44" r="3.5" fill="{pill_c}"/>',
         t(W - 32 - pw + 26, 49, status, 13, pill_c, MONO, 600, extra='letter-spacing="1.5"')]
    for k, line in enumerate(wrap(f["purpose"], 54)[:2]):
        b.append(t(32, 100 + k * 27, escape(line), 18.5, c["dim"]))

    # pipeline: n1 n2 n3 | gate | n4
    y, xs, gx = 206, [82, 200, 318, 512], 418
    b.append(f'<line x1="{xs[0]}" y1="{y}" x2="{xs[-1]}" y2="{y}" stroke="{c["faint"]}" stroke-width="1.4" stroke-dasharray="1 5" stroke-linecap="round"/>')
    for k, (x, name) in enumerate(zip(xs, f["pipe"])):
        last = k == len(xs) - 1
        b.append(f'<rect x="{x - 52}" y="{y - 18}" width="104" height="36" rx="9" fill="{c["panel"]}" '
                 f'stroke="{c["signal"] if last else c["line"]}" stroke-opacity="{.6 if last else 1}"/>')
        b.append(t(x, y + 5, escape(name), 14, c["text"] if last else c["dim"], MONO, 500, "middle"))
    b.append(gate(gx, y - 26, 52, c, dur, f["gate"], y + 50))
    b.append(pulse(f"M {xs[0]} {y} L {xs[-1]} {y}", (gx - xs[0]) / (xs[-1] - xs[0]), dur, c["signal"], 4))

    b.append(f'<line x1="32" y1="282" x2="{W-32}" y2="282" stroke="{c["line"]}"/>')
    b.append(t(32, 311, "RULE", 12, c["gate"], MONO, 700, extra='letter-spacing="2"'))
    b.append(t(84, 312, escape(f["rule"]), 16.5, c["text"], SANS, 500))
    b.append(t(32, 334, escape(f["stack"]), 12.5, c["dim"], MONO))
    return svg(W, H, "\n".join(b), c, f'{f["name"]}: {f["purpose"]} Rule: {f["rule"]}')


# ---------------------------------------------------------------- stack

def stack(c):
    W, H = 1200, 470
    dur = 6.0
    colw, gap, x0 = 172, 13, 40
    b = [t(40, 46, "how my agents are built", 14, c["dim"], MONO),
         t(W - 40, 46, "same six layers, every project", 14, c["faint"], MONO, anchor="end")]
    hy = 112
    centers = [x0 + i * (colw + gap) + colw / 2 for i in range(6)]
    b.append(f'<line x1="{centers[0]}" y1="{hy}" x2="{centers[-1]}" y2="{hy}" stroke="{c["faint"]}" stroke-width="1.4"/>')
    for i, (head, items) in enumerate(STACK):
        x = x0 + i * (colw + gap)
        is_gate = head == "GATE"
        col = c["gate"] if is_gate else c["text"]
        b.append(t(x + colw / 2, 86, f'<tspan fill="{c["faint"]}">{i + 1:02d}</tspan> {head}', 15, col, MONO, 700,
                   "middle", 'letter-spacing="1.5"'))
        if is_gate:
            b.append(gate(x + colw / 2, hy - 14, 28, c, dur))
        else:
            b.append(f'<circle cx="{x + colw / 2}" cy="{hy}" r="5" fill="{c["bg"]}" stroke="{c["signal"]}" stroke-width="1.4"/>')
        b.append(f'<rect x="{x}" y="140" width="{colw}" height="{H - 140 - 32}" rx="12" fill="{c["panel"]}" '
                 f'stroke="{c["gate"] if is_gate else c["line"]}" stroke-opacity="{.55 if is_gate else 1}"/>')
        for j, item in enumerate(items):
            iy = 178 + j * 44
            b.append(t(x + 16, iy, escape(item), 14.5, c["text"] if j == 0 else c["dim"], SANS, 500 if j == 0 else 400))
            if j < len(items) - 1:
                b.append(f'<line x1="{x + 16}" y1="{iy + 18}" x2="{x + colw - 16}" y2="{iy + 18}" stroke="{c["line"]}" stroke-dasharray="2 4"/>')
    frac = (centers[3] - centers[0]) / (centers[-1] - centers[0])
    b.append(pulse(f"M {centers[0]} {hy} L {centers[-1]} {hy}", frac, dur, c["signal"], 5))
    return svg(W, H, "\n".join(b), c, "How my agents are built: senses, brain, hands, a human gate, memory, surface.")


# ---------------------------------------------------------------- signal

def signal(c, days, total):
    W, H = 1200, 320
    x0, x1, y0, y1 = 40, 1160, 92, 246
    counts = [n for _, n in days]
    peak_i = max(range(len(counts)), key=counts.__getitem__)
    mx = max(1, counts[peak_i])
    # light smoothing so the line reads as a signal, peaks kept honest
    sm = [max(counts[i], sum(counts[max(0, i - 1):i + 2]) / 3) for i in range(len(counts))]
    pts = [(x0 + i * (x1 - x0) / (len(sm) - 1), y1 - math.sqrt(v / mx) * (y1 - y0)) for i, v in enumerate(sm)]

    def smooth(p):
        d = f"M {p[0][0]:.1f} {p[0][1]:.1f}"
        for i in range(len(p) - 1):
            a, b_, cc, dd = p[max(0, i - 1)], p[i], p[i + 1], p[min(len(p) - 1, i + 2)]
            c1 = (b_[0] + (cc[0] - a[0]) / 6, b_[1] + (cc[1] - a[1]) / 6)
            c2 = (cc[0] - (dd[0] - b_[0]) / 6, cc[1] - (dd[1] - b_[1]) / 6)
            d += f" C {c1[0]:.1f} {min(y1, c1[1]):.1f}, {c2[0]:.1f} {min(y1, c2[1]):.1f}, {cc[0]:.1f} {cc[1]:.1f}"
        return d

    line = smooth(pts)
    active = sum(1 for n in counts if n)
    streak = best = 0
    for n in counts:
        streak = streak + 1 if n else 0
        best = max(best, streak)
    pd = datetime.fromisoformat(days[peak_i][0])
    b = [f'<defs><linearGradient id="fill" x1="0" y1="0" x2="0" y2="1">'
         f'<stop offset="0" stop-color="{c["signal"]}" stop-opacity=".28"/><stop offset="1" stop-color="{c["signal"]}" stop-opacity="0"/></linearGradient>'
         f'<linearGradient id="beam" x1="0" y1="0" x2="1" y2="0">'
         f'<stop offset="0" stop-color="{c["signal"]}" stop-opacity="0"/><stop offset="1" stop-color="{c["signal"]}" stop-opacity=".22"/></linearGradient>'
         f'<clipPath id="plot"><rect x="{x0}" y="{y0 - 20}" width="{x1 - x0}" height="{y1 - y0 + 21}"/></clipPath></defs>',
         t(40, 46, f'signal <tspan fill="{c["faint"]}">·</tspan> daily contributions, last 12 months', 14, c["dim"], MONO),
         t(W - 40, 46, f'<tspan fill="{c["text"]}">{total}</tspan> contributions  '
           f'<tspan fill="{c["text"]}">{active}</tspan> active days  '
           f'<tspan fill="{c["text"]}">{best}</tspan>-day best streak', 14, c["dim"], MONO, anchor="end",
           extra='xml:space="preserve"')]
    for k in range(4):
        gy = y1 - k * (y1 - y0) / 3
        b.append(f'<line x1="{x0}" y1="{gy:.1f}" x2="{x1}" y2="{gy:.1f}" stroke="{c["line"]}" stroke-dasharray="{"none" if k == 0 else "2 6"}"/>')
    for i, (d, _) in enumerate(days):
        if d.endswith("-01"):
            x = x0 + i * (x1 - x0) / (len(days) - 1)
            b.append(f'<line x1="{x:.1f}" y1="{y1}" x2="{x:.1f}" y2="{y1 + 6}" stroke="{c["faint"]}"/>')
            b.append(t(f"{x:.1f}", y1 + 26, datetime.fromisoformat(d).strftime("%b").lower(), 12, c["dim"], MONO, anchor="middle"))
    b.append(f'<g clip-path="url(#plot)">'
             f'<path d="{line} L {x1} {y1} L {x0} {y1} Z" fill="url(#fill)"/>'
             f'<path d="{line}" fill="none" stroke="{c["signal"]}" stroke-width="1.8" stroke-linejoin="round"/>'
             f'<g class="scan"><rect x="{x0 - 90}" y="{y0 - 20}" width="90" height="{y1 - y0 + 20}" fill="url(#beam)"/>'
             f'<rect x="{x0 - 1}" y="{y0 - 20}" width="1.5" height="{y1 - y0 + 20}" fill="{c["signal"]}" opacity=".8"/></g></g>')
    px, py = pts[peak_i]
    py = y1 - (y1 - y0)
    b.append(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="4" fill="{c["gate"]}"/>')
    b.append(f'<circle class="breathe" cx="{px:.1f}" cy="{py:.1f}" r="9" fill="none" stroke="{c["gate"]}"/>')
    anchor = "end" if px > W - 200 else "start"
    b.append(t(f"{px + (-14 if anchor == 'end' else 14):.1f}", f"{py + 5:.1f}",
               f'peak · {counts[peak_i]} on {pd:%d %b}'.lower(), 13, c["gate"], MONO, 600, anchor))
    return svg(W, H, "\n".join(b), c, f"{total} contributions in the last 12 months, {active} active days.")


# ---------------------------------------------------------------- readme "now" block

def ago(iso, now):
    d = now - datetime.fromisoformat(iso.replace("Z", "+00:00"))
    if d.days >= 1:
        return f"{d.days}d ago"
    return f"{max(1, d.seconds // 3600)}h ago"


def now_block(repos, now):
    recent = [r for r in repos if r["name"] not in ("Portfolio",)][:3]
    rows = [f"`{ago(r['pushed_at'], now):>7}`  [**{r['name']}**]({r['html_url']})" for r in recent]
    return ("<!-- NOW:START -->\n" + "<br>\n".join(rows) +
            f"\n\n<sub>updated {now:%d %b %Y, %H:%M} IST by <code>scripts/build.py</code></sub>\n<!-- NOW:END -->")


def main():
    repos, days, total = fetch()
    now = datetime.now(IST)
    last = repos[0]
    stats = dict(now=now, total=total, last_repo=last["name"], last_ago=ago(last["pushed_at"], now),
                 live=sum(1 for r in repos if (r.get("homepage") or "").find("vercel.app") > -1))
    by_name = {r["name"]: r for r in repos}
    ASSETS.mkdir(exist_ok=True)
    for mode, c in THEMES.items():
        (ASSETS / f"hero-{mode}.svg").write_text(hero(c, stats), encoding="utf-8")
        (ASSETS / f"stack-{mode}.svg").write_text(stack(c), encoding="utf-8")
        (ASSETS / f"signal-{mode}.svg").write_text(signal(c, days, total), encoding="utf-8")
        for i, f in enumerate(FLEET):
            (ASSETS / f"fleet-{i + 1:02d}-{mode}.svg").write_text(card(i, f, c, by_name.get(f["repo"])), encoding="utf-8")
    readme = ROOT / "README.md"
    if readme.exists():
        text = readme.read_text(encoding="utf-8")
        text = re.sub(r"<!-- NOW:START -->.*?<!-- NOW:END -->", lambda _: now_block(repos, now), text, flags=re.S)
        readme.write_text(text, encoding="utf-8")
    print(f"built {2 * (3 + len(FLEET))} images · {total} contributions · last push {last['name']}")


if __name__ == "__main__":
    main()
