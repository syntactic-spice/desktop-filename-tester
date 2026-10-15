#!/usr/bin/env python3
"""Render results/results.json (saved from the results page) as RESULTS.md.

GitHub strips CSS from Markdown, so status colour comes from emoji.
Usage: python3 tools/render_results.py [results.json] [RESULTS.md]
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "results" / "results.json"
OUT = Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / "RESULTS.md"

STATUS = {"works": "✅", "partial": "🟡", "broken": "❌", "na": "➖", "": "·"}
LEGEND = "✅ works · 🟡 partly works · ❌ broken · ➖ not applicable · · not tested"

ENVS = [("gnome", "GNOME", "GNOME"), ("kde", "KDE Plasma", "KDE"), ("noctalia", "Noctalia + niri", "Noctalia")]
COLS = [
    ("A", "A: original name", "install \"$AI\""),
    ("B", "B: renamed", "install \"$AI\" --as dtprobe-renamed"),
    ("C", "C: renamed + StartupWMClass", "install \"$AI\" --as dtprobe-renamed --wmclass"),
    ("D", "D: in a subdirectory", "install \"$AI\" --subdir appimages"),
]
ROWS = [
    ("win", "1 · Window ↔ launcher"),
    ("fdo", "2 · Notification, this process"),
    ("fdochild", "2 · Notification, child process"),
    ("gnotif", "2b · GNotification"),
    ("clickaction", "2c · Notification with click action"),
    ("badge", "3 · Badge + progress"),
    ("rtscheme", "4 · `dtprobe://` registered at runtime"),
    ("staticscheme", "4 · `dtprobe-static://` declared in file"),
    ("portal", "5 · Portal `Registry.Register`"),
    ("mpris", "6 · MPRIS media widget"),
]
META = [("distro", "Distro"), ("desktop", "Desktop / shell"), ("session", "Session"),
        ("portal", "xdg-desktop-portal"), ("extras", "Dock / extensions")]


def md(text):
    return " ".join(str(text).split()).replace("|", "\\|")


def tested(env):
    return any(c.get("s") for c in env.get("cells", {}).values())


def main():
    data = json.loads(SRC.read_text())
    envs = [(eid, name, data["envs"].get(eid, {})) for eid, name, _ in ENVS]
    short = {eid: s for eid, _, s in ENVS}
    done = [(eid, name, env) for eid, name, env in envs if tested(env)]

    out = ["# Desktop ID Probe results", "",
           "What breaks when an AppImage's `.desktop` file is installed under a different name.",
           "Install modes:", ""]
    out += [f"- **{label}**: `./dtprobe-integrate.sh {cmd}`" for _, label, cmd in COLS]
    out += ["", LEGEND, ""]

    # Overview: every tested desktop side by side, status only.
    out += ["## Overview", ""]
    head = "| Test | " + " | ".join(f"{short[eid]} {c}" for eid, _, _ in done for c, _, _ in COLS) + " |"
    out += [head, "|---|" + "|".join(":-:" for _ in done for _ in COLS) + "|"]
    for rid, rlabel in ROWS:
        cells = [STATUS[env["cells"].get(f"{rid}|{c}", {}).get("s", "")] for _, _, env in done for c, _, _ in COLS]
        out.append(f"| {rlabel} | " + " | ".join(cells) + " |")
    out.append("")

    for eid, name, env in envs:
        out += [f"## {name}", ""]
        if not tested(env):
            out += ["Not tested yet.", ""]
            continue
        meta = [f"{label}: {md(env['meta'][key])}" for key, label in META if env.get("meta", {}).get(key)]
        if meta:
            out += [" · ".join(meta), ""]
        notes = env.get("annotations", {})
        marks = {}
        out += ["| Test | " + " | ".join(label for _, label, _ in COLS) + " |", "|---|---|---|---|---|"]
        for rid, rlabel in ROWS:
            row = []
            for c, _, _ in COLS:
                key = f"{rid}|{c}"
                cell = env["cells"].get(key, {})
                text = STATUS[cell.get("s", "")] + (f" {md(cell['n'])}" if cell.get("n") else "")
                if key in notes:
                    marks[key] = len(marks) + 1
                    text += f" [^{eid}{marks[key]}]"
                row.append(text)
            out.append(f"| {rlabel} | " + " | ".join(row) + " |")
        out.append("")
        if env.get("notes"):
            out += [md(env["notes"]), ""]
        if env.get("analysis"):
            out += ["> " + md(env["analysis"]), ""]
        for key, n in marks.items():
            out += [f"[^{eid}{n}]: {md(notes[key])}", ""]

    if data.get("savedAt"):
        out += [f"<sub>Results saved {data['savedAt'][:10]}.</sub>", ""]
    OUT.write_text("\n".join(out))
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
