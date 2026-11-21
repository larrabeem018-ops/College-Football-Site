"use client";
import Link from "next/link";
import { useMemo, useState } from "react";
import type { TeamRef, TProd, TProdTeam, TransferProdFile } from "@/lib/types";
import { fmt, fmtInt } from "@/lib/format";
import TeamBadge from "./TeamBadge";
import { Chips, Segmented } from "./Tabs";
import { StatCard } from "./ui";

type Refs = Record<string, TeamRef & { level?: string | null }>;
export const OFF_GRPS = ["QB", "RB", "WR", "TE"];
export const DEF_GRPS = ["DL", "LB", "DB"];
export const pct = (v: number | null | undefined, d = 0) => (v == null || Number.isNaN(v) ? "—" : `${(v * 100).toFixed(d)}%`);
const n = (v: number | undefined) => v ?? 0;
export const offYds = (p: TProd) => n(p.passYds) + n(p.rushYds) + n(p.recYds);
export const isOffense = (p: TProd) => OFF_GRPS.includes(p.grp) || (!DEF_GRPS.includes(p.grp) && offYds(p) > n(p.tkl));

type Col<T> = { key: string; label: string; get: (r: T) => number | null; show?: (r: T) => string; title?: string };
const OFF_COLS: Col<TProd>[] = [
  { key: "passYds", label: "Pass yds", get: (p) => n(p.passYds) },
  { key: "passTd", label: "Pass TD", get: (p) => n(p.passTd) },
  { key: "rushYds", label: "Rush yds", get: (p) => n(p.rushYds) },
  { key: "rushTd", label: "Rush TD", get: (p) => n(p.rushTd) },
  { key: "rec", label: "Rec", get: (p) => n(p.rec) },
  { key: "recYds", label: "Rec yds", get: (p) => n(p.recYds) },
  { key: "recTd", label: "Rec TD", get: (p) => n(p.recTd) },
  { key: "epa", label: "EPA", get: (p) => p.epa, show: (p) => fmt(p.epa, 1), title: "Expected points added over the season" },
  { key: "offShare", label: "% team yds", get: (p) => p.offShare, show: (p) => pct(p.offShare, 1), title: "Share of his team's passing + rushing + receiving yards" },
];
const DEF_COLS: Col<TProd>[] = [
  { key: "tkl", label: "Tackles", get: (p) => n(p.tkl) },
  { key: "tfl", label: "TFL", get: (p) => n(p.tfl), show: (p) => fmt(n(p.tfl), 1) },
  { key: "sacks", label: "Sacks", get: (p) => n(p.sacks), show: (p) => fmt(n(p.sacks), 1) },
  { key: "int", label: "INT", get: (p) => n(p.int) },
  { key: "pd", label: "PD", get: (p) => n(p.pd), title: "Passes defended" },
  { key: "tklShare", label: "% team tkl", get: (p) => p.tklShare, show: (p) => pct(p.tklShare, 1), title: "Share of his team's tackles" },
];
const TEAM_COLS: Col<TProdTeam>[] = [
  { key: "played", label: "Played", get: (t) => t.played, show: (t) => `${t.played}/${t.n}`, title: "Transfers with stats this season / transfers who arrived" },
  { key: "offShare", label: "Off yds", get: (t) => t.offShare, show: (t) => pct(t.offShare), title: "Share of passing + rushing + receiving yards" },
  { key: "passShare", label: "Pass", get: (t) => t.passShare, show: (t) => pct(t.passShare) },
  { key: "rushShare", label: "Rush", get: (t) => t.rushShare, show: (t) => pct(t.rushShare) },
  { key: "recShare", label: "Rec", get: (t) => t.recShare, show: (t) => pct(t.recShare) },
  { key: "tdShare", label: "Off TD", get: (t) => t.tdShare, show: (t) => pct(t.tdShare) },
  { key: "tklShare", label: "Tackles", get: (t) => t.tklShare, show: (t) => pct(t.tklShare) },
  { key: "sackShare", label: "Sacks", get: (t) => t.sackShare, show: (t) => pct(t.sackShare) },
  { key: "epaT", label: "EPA", get: (t) => t.epaT, show: (t) => fmt(t.epaT, 1), title: "Total EPA from transfers" },
  { key: "epaShare", label: "EPA %", get: (t) => t.epaShare, show: (t) => pct(t.epaShare), title: "Transfers' share of the team's player EPA" },
];

function useSort<T>(cols: Col<T>[], initial: string) {
  const [key, setKey] = useState(initial);
  const [asc, setAsc] = useState(false);
  const col = cols.find((c) => c.key === key) ?? cols[0];
  const sort = (rows: T[]) => [...rows].sort((a, b) => {
    const x = col.get(a), y = col.get(b);
    if (x == null && y == null) return 0;
    if (x == null) return 1;
    if (y == null) return -1;
    return asc ? x - y : y - x;
  });
  const th = (c: Col<T>) => (
    <th key={c.key} className="text-right" title={c.title}>
      <button type="button" onClick={() => (key === c.key ? setAsc(!asc) : (setKey(c.key), setAsc(false)))} aria-sort={key === c.key ? (asc ? "ascending" : "descending") : undefined}>
        {c.label}{key === c.key ? (asc ? " ↑" : " ↓") : ""}
      </button>
    </th>
  );
  return { sort, th, setKey };
}

export function School({ t, refs, hash = "transfers" }: { t: string; refs: Refs; hash?: string }) {
  const r = refs[t];
  const inner = <span className="flex items-center gap-2">{r && <TeamBadge team={r} size={24} ring={false} />}<span className="font-semibold">{t}</span></span>;
  return r?.slug ? <Link href={`/teams/${r.slug}/#${hash}`} className="text-ink hover:text-accent">{inner}</Link> : inner;
}

/** Sortable list of transfers with their stats at the new school. Shared by the Portal page and team pages. */
export function PlayerTable({ players, cols, refs, show, initial, limit }: {
  players: TProd[]; cols: Col<TProd>[]; refs: Refs; show: "both" | "from" | "to"; initial: string; limit?: number;
}) {
  const { sort, th } = useSort(cols, initial);
  const rows = sort(players);
  const shown = limit ? rows.slice(0, limit) : rows;
  return (
    <div className="card max-h-[640px] overflow-auto">
      <table className="tbl min-w-[760px]">
        <thead className="sticky top-0 bg-surface"><tr>
          <th>Player</th><th>Pos</th>
          {show !== "to" && <th>{show === "both" ? "From" : "Came from"}</th>}
          {show !== "from" && <th>{show === "both" ? "Now at" : "Now at"}</th>}
          {cols.map(th)}
        </tr></thead>
        <tbody>
          {shown.map((p, i) => (
            <tr key={`${p.name}-${p.to}-${i}`}>
              <td className="font-semibold">{p.name}{p.stars ? <span className="ml-1.5 text-[12px] font-normal text-muted">{p.stars}★</span> : null}</td>
              <td className="text-soft">{p.pos}</td>
              {show !== "to" && <td><School t={p.from} refs={refs} /></td>}
              {show !== "from" && <td><School t={p.to} refs={refs} /></td>}
              {cols.map((c) => <td key={c.key} className="mono text-right">{c.show ? c.show(p) : fmtInt(c.get(p))}</td>)}
            </tr>
          ))}
          {!shown.length && <tr><td colSpan={cols.length + 4} className="text-muted">No transfers with stats yet.</td></tr>}
        </tbody>
      </table>
      {limit && rows.length > limit && <div className="px-3.5 pb-3 pt-1 text-[12px] text-muted">Showing the top {limit} of {rows.length}. Filter by position or search to see more.</div>}
    </div>
  );
}
export { OFF_COLS, DEF_COLS };

export default function TransferProdView({ data, refs }: { data: TransferProdFile; refs: Refs }) {
  const [level, setLevel] = useState<"fbs" | "all">("fbs");
  const [side, setSide] = useState<"off" | "def">("off");
  const [pos, setPos] = useState("All");
  const [q, setQ] = useState("");
  const [tq, setTq] = useState("");
  const inLevel = (t: string) => level === "all" || refs[t]?.level === "fbs";
  const teams = useMemo(() => data.teams.filter((t) => inLevel(t.team)), [data, level]); // eslint-disable-line react-hooks/exhaustive-deps
  const players = useMemo(() => data.players.filter((p) => inLevel(p.to)), [data, level]); // eslint-disable-line react-hooks/exhaustive-deps

  const offT = teams.reduce((a, t) => a + t.offT, 0), offAll = teams.reduce((a, t) => a + t.offAll, 0);
  const tklT = teams.reduce((a, t) => a + t.tklT, 0), tklAll = teams.reduce((a, t) => a + t.tklAll, 0);
  const topEpa = [...players].filter((p) => p.epa != null).sort((a, b) => (b.epa ?? 0) - (a.epa ?? 0))[0];
  const topTkl = [...players].sort((a, b) => n(b.tkl) - n(a.tkl))[0];

  const minOff = level === "fbs" ? 1500 : 500, minTkl = level === "fbs" ? 150 : 50;
  const offBoard = [...teams].filter((t) => t.offAll >= minOff && t.offShare != null).sort((a, b) => (b.offShare ?? 0) - (a.offShare ?? 0)).slice(0, 10);
  const defBoard = [...teams].filter((t) => t.tklAll >= minTkl && t.tklShare != null).sort((a, b) => (b.tklShare ?? 0) - (a.tklShare ?? 0)).slice(0, 10);

  const s = q.trim().toLowerCase();
  const grps = side === "off" ? OFF_GRPS : DEF_GRPS;
  const plist = players.filter((p) => (side === "off" ? isOffense(p) : !isOffense(p)))
    .filter((p) => pos === "All" || p.grp === pos)
    .filter((p) => !s || p.name.toLowerCase().includes(s) || p.to.toLowerCase().includes(s) || p.from.toLowerCase().includes(s));
  const ts = tq.trim().toLowerCase();
  const { sort: sortTeams, th: thTeam } = useSort(TEAM_COLS, "offShare");
  const tlist = sortTeams(teams.filter((t) => !ts || t.team.toLowerCase().includes(ts)));

  const Board = ({ title, rows, get, sub }: { title: string; rows: TProdTeam[]; get: (t: TProdTeam) => number | null; sub: (t: TProdTeam) => string | null }) => (
    <section className="card flex flex-col gap-2.5 p-5">
      <h2 className="display m-0 text-[22px]">{title}</h2>
      {rows.map((t) => (
        <div key={t.team} className="grid grid-cols-[minmax(0,1fr)_110px_52px] items-center gap-3 text-[14px]">
          <div className="min-w-0"><School t={t.team} refs={refs} />{sub(t) && <div className="truncate pl-8 text-[12px] text-muted">{sub(t)}</div>}</div>
          <div className="h-2 overflow-hidden rounded bg-chip"><div className="h-full rounded bg-accent" style={{ width: `${Math.min(1, get(t) ?? 0) * 100}%` }} /></div>
          <span className="mono text-right font-semibold text-accent">{pct(get(t))}</span>
        </div>
      ))}
      {!rows.length && <p className="m-0 text-muted">No data yet.</p>}
    </section>
  );

  return (
    <div className="flex flex-col gap-8">
      <Segmented label="Level" options={[{ value: "fbs", label: "FBS" }, { value: "all", label: "All schools" }]} value={level} onChange={setLevel} />
      <div className="grid grid-cols-[repeat(auto-fit,minmax(200px,1fr))] gap-3">
        <StatCard label="Transfers who've played" value={fmtInt(players.length)} sub={`at ${teams.filter((t) => t.played).length} schools`} />
        <StatCard label="Offensive yards from transfers" value={pct(offAll ? offT / offAll : null)} sub={`${fmtInt(offT)} of ${fmtInt(offAll)} yds`} tone="good" />
        <StatCard label="Tackles from transfers" value={pct(tklAll ? tklT / tklAll : null)} sub={`${fmtInt(tklT)} of ${fmtInt(tklAll)}`} tone="good" />
        <StatCard label="Top transfer by EPA" value={topEpa ? fmt(topEpa.epa, 1) : "—"} sub={topEpa ? `${topEpa.name}, ${topEpa.to}` : undefined} />
        <StatCard label="Top transfer tackler" value={topTkl ? fmtInt(topTkl.tkl) : "—"} sub={topTkl ? `${topTkl.name}, ${topTkl.to}` : undefined} />
      </div>
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Board title="Most transfer-driven offenses" rows={offBoard} get={(t) => t.offShare} sub={(t) => (t.topOff ? `Led by ${t.topOff}` : null)} />
        <Board title="Most transfer-driven defenses" rows={defBoard} get={(t) => t.tklShare} sub={(t) => (t.topDef ? `Led by ${t.topDef}` : null)} />
      </div>

      <section className="flex flex-col gap-3">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 className="display m-0 text-[26px]">Transfer leaderboard</h2>
          <label className="sr-only" htmlFor="tpq">Search players or schools</label>
          <input id="tpq" type="search" className="field w-64" placeholder="Search players or schools" value={q} onChange={(e) => setQ(e.target.value)} />
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <Segmented label="Side of the ball" options={[{ value: "off", label: "Offense" }, { value: "def", label: "Defense" }]} value={side} onChange={(v) => { setSide(v); setPos("All"); }} />
          <Chips label="Position" options={["All", ...grps].map((g) => ({ value: g, label: g }))} value={pos} onChange={setPos} />
        </div>
        {side === "off"
          ? <PlayerTable key="off" players={plist} cols={OFF_COLS} refs={refs} show="both" initial="epa" limit={150} />
          : <PlayerTable key="def" players={plist} cols={DEF_COLS} refs={refs} show="both" initial="tkl" limit={150} />}
      </section>

      <section className="flex flex-col gap-3">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 className="display m-0 text-[26px]">How much each school leans on transfers</h2>
          <label className="sr-only" htmlFor="tpt">Search schools</label>
          <input id="tpt" type="search" className="field w-64" placeholder="Search schools" value={tq} onChange={(e) => setTq(e.target.value)} />
        </div>
        <div className="card max-h-[640px] overflow-auto">
          <table className="tbl min-w-[980px]">
            <thead className="sticky top-0 bg-surface"><tr><th>School</th>{TEAM_COLS.map(thTeam)}<th>Top transfers</th></tr></thead>
            <tbody>{tlist.map((t) => (
              <tr key={t.team}>
                <td><School t={t.team} refs={refs} /></td>
                {TEAM_COLS.map((c) => <td key={c.key} className="mono text-right">{c.show ? c.show(t) : fmtInt(c.get(t))}</td>)}
                <td className="text-[13px] text-soft">{[t.topOff, t.topDef].filter(Boolean).join(" · ") || "—"}</td>
              </tr>
            ))}</tbody>
          </table>
        </div>
        <p className="m-0 text-[12px] leading-relaxed text-muted">
          Shares are each school&apos;s {data.season} season totals that came from players who arrived through the portal this cycle.
          Off yds counts passing + rushing + receiving yards, so a transfer QB throwing to a transfer WR counts on both sides.
          EPA is expected points added (CFBD&apos;s PPA) summed over a player&apos;s plays. CFBD credits each pass to both the passer and his target, so EPA % is the transfers&apos; share of the school&apos;s summed player EPA (shown only when both are positive), not of the offense&apos;s EPA.
          Only transfers who were on a {data.season - 1} FBS/FCS roster are matched.
        </p>
      </section>
    </div>
  );
}
