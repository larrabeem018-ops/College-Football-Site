"""
injuries.py -- turn the conferences' player availability reports into model inputs.

Sources (either or both):
  data/Injury Reports/*.csv       tables exported from each conference's availability page
                                  (ACC, AAC, Big Ten, Big 12, Mountain West, SEC so far)
  data/availability_{year}.csv    written by `python update_data.py --only-availability`
                                  (ACC, Big Ten, Big 12, SEC, pulled automatically)
One row per player listed on a team's report for a game.

What gets used
--------------
The reports list a lot of players, and most of them are long-term absences
(season-ending injuries, redshirts) the team has already been playing without,
which the ratings already reflect. So the model only looks at *changes*:

  qb_out    -- chance the team's most recent starting QB (most pass attempts in
               its last game) misses this game, from his report status.
  new_out   -- how many players are out this game who were NOT out for the
               team's previous reported game.

Status -> chance of missing the game:
  Out 1.0, Doubtful 0.8, Game Time Decision / Questionable 0.4, Probable 0.1,
  Available / Exempt 0.
Before kickoff the latest status posted is used; once a game-day report exists
that is what's used (so backtests see who actually sat).
"""
import os
import re

import numpy as np
import pandas as pd

DATA = "data"
REPORT_CONFS = {"ACC", "Big Ten", "Big 12", "SEC"}

TEAM_FIX = {"Miami (FL)": "Miami"}

STATUS_P = {
    "out": 1.0, "out - (1st half)": 0.5, "out (1st half)": 0.5, "out (full game)": 1.0,
    "out (season)": 1.0, "doubtful": 0.8,
    "game time decision": 0.4, "questionable": 0.4, "probable": 0.1,
    "available": 0.0, "exempt": 0.0,
}


def status_p(s):
    if not isinstance(s, str) or not s.strip():
        return 0.0
    s = s.strip().lower()
    if s in STATUS_P:
        return STATUS_P[s]
    return 1.0 if s.startswith("out") else 0.0


_SUFFIX = re.compile(r"\b(jr|sr|ii|iii|iv|v)\b")


def norm_name(n):
    n = str(n).lower().replace("’", "'")
    n = re.sub(r"[^a-z' ]", " ", n).replace("'", "")
    n = _SUFFIX.sub(" ", n)
    return " ".join(n.split())


def _read_export(path):
    """One conference's report table as exported from its website (columns vary by conference:
    Team, Date/Game Date, Opponent, Number/#, Player/Player Name, [Position], then one column per
    report in order, ending with the game-day / final status)."""
    raw = pd.read_csv(path, header=None, dtype=str, encoding="utf-8-sig")
    hdr = raw.index[raw.iloc[:, 0].astype(str).str.strip().eq("Team")]
    if not len(hdr):
        return None
    d = raw.iloc[hdr[0] + 1:].copy()
    d.columns = [str(c).replace("↑", "").strip() for c in raw.iloc[hdr[0]]]
    d = d.dropna(subset=["Team"])
    pick = lambda *names: next((n for n in names if n in d.columns), None)
    date_c, num_c = pick("Date", "Game Date"), pick("Number", "#")
    player_c, pos_c = pick("Player", "Player Name"), pick("Position")
    used = {"Team", date_c, "Opponent", num_c, player_c, pos_c}
    status_cols = [c for c in d.columns if c not in used and "status" in c.lower()]

    def last_posted(row):
        posted = [str(row[c]).strip() for c in status_cols
                  if isinstance(row[c], str) and row[c].strip() not in ("", "-")]
        return posted[-1] if posted else ""

    out = pd.DataFrame({
        "team": d["Team"].str.strip(),
        "opponent": d["Opponent"].str.strip(),
        "game_date": pd.to_datetime(d[date_c], format="mixed").dt.strftime("%Y-%m-%d"),
        "number": d[num_c].astype(str).str.lstrip("#").str.strip(),
        "player": d[player_c].str.strip(),
        "position": d[pos_c].str.strip() if pos_c else None,
        "status": d.apply(last_posted, axis=1),
        "source": os.path.basename(path),
    })
    out["season"] = pd.to_datetime(out["game_date"]).dt.year
    return out


def load_reports(lines, folder=os.path.join(DATA, "Injury Reports")):
    """Every report row in data/Injury Reports/*.csv (plus data/availability_*.csv from
    update_data.py, if present) with a gameId attached.
    lines: espnBetLines rows (id or gameId, startDate, homeTeam, awayTeam)."""
    frames = []
    if os.path.isdir(folder):
        for f in sorted(os.listdir(folder)):
            if f.lower().endswith(".csv"):
                t = _read_export(os.path.join(folder, f))
                if t is not None:
                    frames.append(t)
    for f in sorted(os.listdir(DATA)):
        if f.startswith("availability_") and f.endswith(".csv"):
            a = pd.read_csv(os.path.join(DATA, f), dtype={"number": str})
            a["status"] = np.where(a["game_day"].fillna("").astype(str).str.len() > 0,
                                   a["game_day"], a["latest"].fillna(""))
            a["position"], a["source"] = None, f
            frames.append(a[["team", "opponent", "game_date", "number", "player", "position",
                             "status", "source", "season"]])
    if not frames:
        return None
    r = pd.concat(frames, ignore_index=True)
    r["team"] = r["team"].replace(TEAM_FIX)
    r["p_out"] = r["status"].map(status_p)
    r["name_key"] = r["player"].map(norm_name)

    # attach gameId: same team, kickoff on the report's date (US Eastern) or a day either side
    l = lines.rename(columns={"id": "gameId"}) if "id" in lines.columns else lines
    l = l[["gameId", "startDate", "homeTeam", "awayTeam"]].drop_duplicates("gameId")
    ko = pd.to_datetime(l["startDate"], utc=True).dt.tz_convert("America/New_York").dt.tz_localize(None).dt.normalize()
    long = pd.concat([pd.DataFrame({"gameId": l["gameId"], "team": l["homeTeam"], "ko": ko}),
                      pd.DataFrame({"gameId": l["gameId"], "team": l["awayTeam"], "ko": ko})])
    r["gd"] = pd.to_datetime(r["game_date"])
    m = r.merge(long, on="team", how="left")
    m = m[(m["ko"] - m["gd"]).abs() <= pd.Timedelta(days=1)]
    m = m.sort_values("gameId").drop_duplicates(["team", "game_date", "name_key", "number"])
    return m.drop(columns=["gd", "ko"])


def team_game_features(reports, starter_lookup):
    """One row per (gameId, team) that has a report: qb_out, new_out, n_out, out_names.

    starter_lookup(team, gameId) -> normalized name of the team's last starting QB before this game, or None.
    """
    if reports is None or reports.empty:
        return pd.DataFrame(columns=["gameId", "team", "qb_out", "new_out", "n_out", "qb_name", "qb_status",
                                     "new_out_names"])
    rows = []
    for team, tg in reports.sort_values("game_date").groupby("team"):
        prev_out = None
        for (gid, gdate), g in tg.groupby(["gameId", "game_date"], sort=False):
            out_now = set(g.loc[g["p_out"] >= 0.8, "name_key"])
            starter = starter_lookup(team, gid)
            qb_rows = g[g["name_key"] == starter] if starter else g.iloc[0:0]
            qb_p = float(qb_rows["p_out"].max()) if len(qb_rows) else 0.0
            if prev_out is None:
                new = set()          # first report we have for this team: no baseline to compare with
            else:
                new = out_now - prev_out
            rows.append({"gameId": gid, "team": team, "qb_out": qb_p,
                         "qb_name": qb_rows["player"].iloc[0] if len(qb_rows) else None,
                         "qb_status": qb_rows["status"].iloc[0] if len(qb_rows) else None,
                         "new_out": float(len(new - ({starter} if starter else set()))),
                         "n_out": float(len(out_now)),
                         "new_out_names": "; ".join(sorted(g.loc[g["name_key"].isin(new), "player"]))})
            prev_out = out_now
    return pd.DataFrame(rows)
