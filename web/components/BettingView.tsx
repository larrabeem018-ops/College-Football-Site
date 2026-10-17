"use client";
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import type { BettingFile, DirectoryTeam } from "@/lib/types";
import { money, recordText } from "@/lib/format";
import Tabs, { Segmented } from "./Tabs";
import { SimpleBars } from "./charts";
import TeamBadge from "./TeamBadge";

export default function BettingView({ seasons, teams }: { seasons: number[]; teams: DirectoryTeam[] }) {
  const [season, setSeason] = useState(seasons[0]);
  const [d, setD] = useState<BettingFile | null>(null);
  useEffect(() => { setD(null); fetch(`/data/betting/${season}.json`).then((r) => r.json()).then(setD); }, [season]);
  const bySchool = useMemo(() => Object.fromEntries(teams.map((t) => [t.school, t])), [teams]);
  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <Segmented label="Season" options={seasons.map((s) => ({ value: s, label: `${s}${s === seasons[0] ? " (in progress)" : ""}` }))} value={season} onChange={setSeason} />
        <label className="flex items-center gap-2 text-[13px] text-muted">One team:
          <select className="field" defaultValue="" onChange={(e) => e.target.value && (window.location.href = `/teams/${e.target.value}/#betting`)}>
            <option value="">Choose a team…</option>
            {teams.filter((t) => t.level === "fbs").sort((a, b) => a.school.localeCompare(b.school)).map((t) => <option key={t.slug} value={t.slug!}>{t.school}</option>)}
          </select></label>
      </div>
      {d ? <Inner d={d} bySchool={bySchool} key={season} /> : <p className="text-muted">Loading…</p>}
    </div>
  );
}

function Inner({ d, bySchool }: { d: BettingFile; bySchool: Record<string, DirectoryTeam> }) {
  const [minGames, setMin] = useState(5);
  const [role, setRole] = useState<"all" | "fav" | "dog">("all");
  const [wager, setWager] = useState(10);
  const [q, setQ] = useState("");
  const maxGames = Math.max(1, ...d.rankings.map((r) => r.all.games));
  const qualified = d.rankings.filter((r) => r.all.games >= 5).sort((a, b) => b.all.pct - a.all.pct);
  const ranked = d.rankings.filter((r) => r[role].games >= minGames).sort((a, b) => b[role].pct - a[role].pct);
  const top = d.upsets[0];
  const Name = ({ t }: { t: string }) => {
    const r = bySchool[t];
    const inner = <span className="flex items-center gap-2.5">{r && <TeamBadge team={r} size={26} ring={false} />}<span className="font-semibold">{t}</span></span>;
    return r ? <Link href={`/teams/${r.slug}/#betting`} className="text-ink hover:text-accent">{inner}</Link> : inner;
  };
  const card = (label: string, value: React.ReactNode, sub?: string) => (
    <div className="card p-5"><div className="text-[13px] font-semibold text-muted">{label}</div><div className="mt-2 text-[22px] font-bold leading-tight">{value}</div>{sub && <div className="mt-1 text-[13px] text-soft">{sub}</div>}</div>
  );
  const s = q.trim().toLowerCase();
  const log = d.games.filter((g) => !s || g.home.toLowerCase().includes(s) || g.away.toLowerCase().includes(s));

  const rankings = (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center gap-4">
        <Segmented label="Games as" options={[{ value: "all", label: "Overall" }, { value: "fav", label: "As favorite" }, { value: "dog", label: "As underdog" }]} value={role} onChange={setRole} />
        <label className="flex items-center gap-3 text-[13px] font-semibold text-muted">Min. games <span className="mono text-ink">{minGames}</span>
          <input type="range" min={1} max={maxGames} value={minGames} onChange={(e) => setMin(Number(e.target.value))} /></label>
      </div>
      <div className="card max-h-[680px] overflow-auto">
        <table className="tbl min-w-[600px]">
          <thead className="sticky top-0 bg-surface"><tr><th>#</th><th>Team</th><th className="text-right">Games</th><th className="text-right">Record</th><th className="text-right">ATS</th><th className="w-[200px]">Cover %</th></tr></thead>
          <tbody>{ranked.map((r, i) => { const x = r[role]; return (
            <tr key={r.team}><td className="mono text-muted">{i + 1}</td><td><Name t={r.team} /></td><td className="mono text-right">{x.games}</td><td className="mono text-right">{recordText(x.w, x.l)}</td><td className="mono text-right">{recordText(x.cover, x.noCover, x.push)}</td>
              <td><div className="flex items-center gap-2"><div className="h-2 flex-1 overflow-hidden rounded bg-chip"><div className="h-full rounded bg-accent" style={{ width: `${x.pct}%` }} /></div><span className="mono w-12 text-right text-[13px]">{x.pct.toFixed(1)}%</span></div></td></tr>); })}</tbody>
        </table>
      </div>
    </div>
  );
  const small = (title: string, sub: string, rows: React.ReactNode) => (
    <section className="flex flex-col gap-2"><h3 className="display m-0 text-[22px]">{title}</h3><p className="m-0 text-[13px] text-muted">{sub}</p><div className="card overflow-x-auto">{rows}</div></section>
  );
  const upsets = (
    <div className="grid grid-cols-1 gap-6 xl:grid-cols-3">
      {small("Biggest upsets", "Underdogs who won outright, by points they were getting.",
        <table className="tbl"><thead><tr><th>Wk</th><th>Winner</th><th className="text-right">Line</th><th className="text-right">Score</th></tr></thead>
          <tbody>{d.upsets.map((u, i) => <tr key={i}><td className="mono text-muted">{u.week}</td><td><Name t={u.team} /><div className="pl-9 text-[12px] text-muted">{u.home ? "vs" : "@"} {u.opp}</div></td><td className="mono text-right">+{u.line}</td><td className="mono text-right">{u.score}</td></tr>)}</tbody></table>)}
      {small("Nail-biters", "Decided against the spread by the smallest margin.",
        <table className="tbl"><thead><tr><th>Wk</th><th>Game</th><th className="text-right">Score</th><th className="text-right">Margin</th></tr></thead>
          <tbody>{d.nailBiters.map((g, i) => <tr key={i}><td className="mono text-muted">{g.week}</td><td className="text-[13px]">{g.away} @ {g.home}</td><td className="mono text-right">{g.score}</td><td className="mono text-right">{g.margin}</td></tr>)}</tbody></table>)}
      {small("Biggest covers", "Home teams who beat the spread by the most.",
        <table className="tbl"><thead><tr><th>Wk</th><th>Game</th><th className="text-right">Score</th><th className="text-right">Margin</th></tr></thead>
          <tbody>{d.bigCovers.map((g, i) => <tr key={i}><td className="mono text-muted">{g.week}</td><td className="text-[13px]">{g.away} @ {g.home}</td><td className="mono text-right">{g.score}</td><td className="mono text-right">+{g.margin}</td></tr>)}</tbody></table>)}
    </div>
  );
  const sim = (
    <div className="flex flex-col gap-6">
      <section className="card flex flex-col gap-2 p-5">
        <h3 className="display m-0 text-[22px]">How games finished against the spread</h3>
        <SimpleBars data={Object.entries(d.outcomes).map(([label, value]) => ({ label, value }))} valueLabel="Games" />
      </section>
      <section className="card flex flex-col gap-4 p-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h3 className="display m-0 text-[22px]">Moneyline every game</h3>
          <label className="flex items-center gap-2 text-[14px] text-soft">Wager per game $<input type="number" min={1} max={1000} value={wager} onChange={(e) => setWager(Math.max(1, Number(e.target.value) || 1))} className="field w-24" /></label>
        </div>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          {card("Betting every favorite", <span className={d.favProfit >= 0 ? "text-accent" : "text-loss"}>{money(d.favProfit * wager)}</span>, `${d.graded} graded games`)}
          {card("Betting every underdog", <span className={d.dogProfit >= 0 ? "text-accent" : "text-loss"}>{money(d.dogProfit * wager)}</span>, `${d.graded} graded games`)}
        </div>
      </section>
    </div>
  );
  const full = (
    <div className="flex flex-col gap-3">
      <input type="search" aria-label="Search games" className="field w-64" placeholder="Search teams" value={q} onChange={(e) => setQ(e.target.value)} />
      <div className="card max-h-[680px] overflow-auto">
        <table className="tbl min-w-[720px]">
          <thead className="sticky top-0 bg-surface"><tr><th>Wk</th><th>Away</th><th>Home</th><th className="text-right">Score</th><th>Line</th><th>Outcome</th></tr></thead>
          <tbody>{log.slice(0, 400).map((g, i) => <tr key={i}><td className="mono text-muted">{g.week}</td><td>{g.away}</td><td>{g.home}</td><td className="mono text-right">{g.homeScore != null ? `${g.awayScore}–${g.homeScore}` : "—"}</td><td className="mono text-soft">{g.line ?? "—"}</td><td className="text-soft">{g.category ?? "—"}</td></tr>)}</tbody>
        </table>
      </div>
      {log.length > 400 && <p className="m-0 text-[12px] text-muted">Showing 400 of {log.length}. Search to narrow it down.</p>}
    </div>
  );

  return (
    <>
      <div className="grid grid-cols-[repeat(auto-fit,minmax(220px,1fr))] gap-3">
        {card("Games analyzed", d.gamesAnalyzed.toLocaleString())}
        {qualified[0] && card("Best ATS team", <Name t={qualified[0].team} />, `${qualified[0].all.pct}% cover · min. 5 games`)}
        {qualified.length > 1 && card("Worst ATS team", <Name t={qualified[qualified.length - 1].team} />, `${qualified[qualified.length - 1].all.pct}% cover`)}
        {top && card("Biggest upset", <Name t={top.team} />, `+${top.line} · beat ${top.opp} ${top.score}`)}
      </div>
      <Tabs label="ATS sections" tabs={[
        { id: "rankings", label: "ATS rankings", content: rankings },
        { id: "upsets", label: "Upsets & nail-biters", content: upsets },
        { id: "simulator", label: "Betting simulator", content: sim },
        { id: "log", label: "Full game log", content: full },
      ]} />
    </>
  );
}
