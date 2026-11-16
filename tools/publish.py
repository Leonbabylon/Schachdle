#!/usr/bin/env python3
"""Assemble the folder that goes online (public/).

Copies the page and only the puzzle files players are allowed to have: everything up to tomorrow (UTC),
because the first time zones reach a new date 14 hours before UTC does. Later puzzles stay out, so
nobody can read next week's answers from the site.

  python tools/publish.py           what the live site should contain right now
  python tools/publish.py --all     every built puzzle, for previewing on your own machine
"""
import argparse, datetime as dt, json, os, shutil

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CFG = json.load(open(os.path.join(ROOT, "tools", "config.json")))
OUT = os.path.join(ROOT, "public")

ap = argparse.ArgumentParser()
ap.add_argument("--all", action="store_true")
args = ap.parse_args()

cutoff = (dt.datetime.now(dt.timezone.utc).date() + dt.timedelta(days=1)).isoformat()
shutil.rmtree(OUT, ignore_errors=True)
os.makedirs(os.path.join(OUT, "puzzles"))
shutil.copy(os.path.join(ROOT, "site", "index.html"), OUT)
open(os.path.join(OUT, ".nojekyll"), "w").close()
if CFG.get("domain"):
    open(os.path.join(OUT, "CNAME"), "w").write(CFG["domain"] + "\n")
names = sorted(n for n in os.listdir(os.path.join(ROOT, "puzzles")) if n.endswith(".json"))
shipped = [n for n in names if args.all or n[:-5] <= cutoff]
for n in shipped:
    shutil.copy(os.path.join(ROOT, "puzzles", n), os.path.join(OUT, "puzzles", n))
held = len(names) - len(shipped)
print(f"public/: index.html + {len(shipped)} puzzle file(s)" + (f", {held} future puzzle(s) held back" if held else ""))
if not args.all and cutoff[:10] + ".json" not in names:
    print(f"WARNING: no puzzle is built for {cutoff}. Add positions to queue.json.")
