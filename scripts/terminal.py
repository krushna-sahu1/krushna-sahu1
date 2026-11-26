"""Answers issues whose title is a command, like /whoami.

Triggered by .github/workflows/terminal.yml. The issue title is untrusted
input: it only ever selects a key from REPLIES and is never executed.
"""

from __future__ import annotations

import json
import os
import re
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO = os.environ["GITHUB_REPOSITORY"]
NUMBER = os.environ["ISSUE_NUMBER"]
TITLE = os.environ.get("ISSUE_TITLE", "").strip().lower()
AUTHOR = re.sub(r"[^A-Za-z0-9-]", "", os.environ.get("ISSUE_AUTHOR", ""))
README = Path(__file__).resolve().parent.parent / "README.md"
IST = timezone(timedelta(hours=5, minutes=30))

FOOT = "\n\n---\n<sub>answered by <code>scripts/terminal.py</code> · try <code>/whoami</code> <code>/fleet</code> <code>/stack</code> <code>/rule</code> <code>/contact</code></sub>"

REPLIES = {
    "/whoami": """```
krushna sahu
builds: ai agents, end to end (voice, vision, chat, desktop)
rule:   agents do the work. a human makes the irreversible call.
```
Everything on my profile is drawn by a script from live GitHub data. This reply is too.""",
    "/fleet": """| agent | what it does | the line it won't cross |
|---|---|---|
| [unified-inbox](https://github.com/krushna-sahu1/unified-inbox) | WhatsApp, Instagram and LinkedIn in one Hermes inbox | sends only after your yes |
| [agentic-dish](https://agentic-dish.vercel.app) | a restaurant you order from by talking | never pays; you tap Pay |
| [lensbite](https://lensbite-seven.vercel.app) | camera + voice food tracker | logs only when you confirm |
| [jarvix](https://github.com/krushna-sahu1/jarvix) | local desktop agent over Telegram | never touches the cloud |
| [VoiceLoan](https://github.com/krushna-sahu1/Loan_Agent) | loan application by voice | admin makes the decision |
| [PathoLab](https://patholab-connects.vercel.app) | pathology lab logistics | every screen behind a role |""",
    "/stack": """```
senses   whatsapp · instagram · linkedin · gmail · telegram · deepgram · gemini live
brain    ollama (local) · deepseek · gemini · hermes agent · copilotkit
hands    zod-typed tools · guarded runner · no sql from the model
gate     a human click for anything you can't undo
memory   supabase postgres · row level security · realtime · pg_cron
surface  next.js 15 · react · tailwind v4 · telegram · chrome extensions
```""",
    "/rule": """**Agents do the boring 90%. The last step waits for a human.**

In agentic-dish there is no payment tool at all: the agent prepares the order and a database trigger rejects any status change to *paid* that doesn't come from the payment webhook. In unified-inbox, Hermes drafts and you send. That pattern is in every project here.""",
    "/contact": """Thanks for writing. This issue stays open, and Krushna reads every one.
Leave your message (and how to reach you) as a comment below.""",
}


def gh(method, path, body=None):
    req = urllib.request.Request(f"https://api.github.com/repos/{REPO}/{path}", method=method,
                                 data=json.dumps(body).encode() if body else None)
    req.add_header("Authorization", f"Bearer {os.environ['GITHUB_TOKEN']}")
    req.add_header("Accept", "application/vnd.github+json")
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def main():
    cmd = TITLE.split()[0] if TITLE else ""
    known = cmd in REPLIES
    reply = REPLIES.get(cmd, f"`{cmd[:20]}`: command not found. Try one of the commands below.")
    gh("POST", f"issues/{NUMBER}/comments", {"body": reply + FOOT})
    if cmd != "/contact":
        gh("PATCH", f"issues/{NUMBER}", {"state": "closed", "state_reason": "completed"})
    if not known:
        return

    now = datetime.now(IST)
    entry = f"<sub><code>{now:%d %b %H:%M}</code> &nbsp;{AUTHOR} ran <code>{cmd}</code></sub>"
    text = README.read_text(encoding="utf-8")
    m = re.search(r"<!-- LOG:START -->\n(.*?)<!-- LOG:END -->", text, re.S)
    old = [l for l in m.group(1).splitlines() if "</code>" in l and " ran " in l] if m else []
    log = "<br>\n".join([entry] + old[:4]) + "\n"
    text = re.sub(r"<!-- LOG:START -->\n.*?<!-- LOG:END -->",
                  lambda _: f"<!-- LOG:START -->\n{log}<!-- LOG:END -->", text, flags=re.S)
    README.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
