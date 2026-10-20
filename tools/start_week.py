"""Start-of-week routine for the site (run from anywhere):
  1. refresh 2026 data (final scores for last week, stats, lines)
  2. figure out the upcoming week (first week with games not yet played)
  3. pull that week's schedule + spreads
  4. run the score model for that week
  5. rebuild the website data (web/public/data)
Optional: python tools/start_week.py 8   to force a week number.
"""
import os, subprocess, sys
from datetime import datetime, timezone
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
PY = sys.executable

def run(*args):
    print("\n>>> python " + " ".join(args), flush=True)
    r = subprocess.run([PY, *args])
    if r.returncode != 0:
        sys.exit(f"Step failed: {' '.join(args)}")

run("update_data.py", "--seasons", "2026")

if len(sys.argv) > 1:
    week = int(sys.argv[1])
else:
    lines = pd.read_csv("data/espnBetLines_2026.csv")
    lines = lines[lines["seasonType"] == "regular"] if "seasonType" in lines else lines
    start = pd.to_datetime(lines["startDate"], utc=True)
    upcoming = lines[(start > datetime.now(timezone.utc)) & lines["homeScore"].isna()]
    week = int(upcoming["week"].min()) if len(upcoming) else int(lines.loc[lines["homeScore"].notna(), "week"].max()) + 1
print(f"\n=== Upcoming week: {week} ===", flush=True)

run("update_data.py", "--seasons", "2026", "--week", str(week),
    "--skip-qb", "--skip-lines", "--skip-team-stats", "--skip-model-inputs")
run("score_model.py", "--week", str(week))
run("export_web_data.py")
print(f"\nAll done: week {week} picks are built. Commit and push in GitHub Desktop to publish.")
