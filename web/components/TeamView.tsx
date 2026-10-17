"use client";
import Link from "next/link";
import { useMemo, useState } from "react";
import type { TeamDoc, TeamRef } from "@/lib/types";
import { dateShort, fmt, fmtInt, heightText, money, recordText, signed } from "@/lib/format";
import Tabs, { Segmented } from "./Tabs";
import TeamBadge from "./TeamBadge";
import { ProductionChart, SimpleBars } from "./charts";

type Refs = Record<string, TeamRef>;
const POS_ORDER = ["QB", "RB", "WR", "TE", "OL", "DL", "LB", "DB", "K", "P", "LS"];
const STAT_NAMES: Record<string, string> = {
  passing_YDS: "Pass yds", passing_TD: "Pass TD", passing_COMPLETIONS: "Completions", passing_ATT: "Attempts", passing_INT: "INT thrown",
  rushing_YDS: "Rush yds", rushing_TD: "Rush TD", rushing_CAR: "Carries", receiving_YDS: "Rec yds", receiving_TD: "Rec TD", receiving_REC: "Receptions",
  defensive_TOT: "Tackles", defensive_TFL: "TFL", defensive_SACKS: "Sacks", defensive_PD: "Passes defended", interceptions_INT: "INT",
  kickReturns_YDS: "KR yds", puntReturns_YDS: "PR yds", kicking_PTS: "Kicking pts",
};

function Metric({ label, value, sub, tone }: { label: string; value: React.ReactNode; sub?: React.ReactNode; tone?: "good" | "bad" }) {
  return (
    <div className="card p-4">
      <div className="text-[12px] font-semibold text-muted">{label}</div>
      <div className="mono mt-1 text-[24px] font-semibold">{value}</div>
      {sub && <div className={`mt-0.5 text-[12px] font-semibold ${tone === "good" ? "text-accent" : tone === "bad" ? "text-loss" : "text-muted"}`}>{sub}</div>}
    </div>
  );
}
function Opp({ name, refs }: { name: string; refs: Refs }) {
  const r = refs[name];
  const inner = <span className="flex items-center gap-2.5">{r && <TeamBadge team={r} size={26} ring={false} />}<span className="font-semibold">{name}</span></span>;
  return r?.slug ? <Link href={`/teams/${r.slug}/`} className="text-ink hover:text-accent">{inner}</Link> : inner;
}
function H3({ children }: { children: React.ReactNode }) {
  return <h3 className="display m-0 text-[22px]">{children}</h3>;
}

export default function TeamView({ doc, refs }: { doc: TeamDoc; refs: Refs }) {
  const t = doc.team;
  const played = doc.schedule.filter((s) => s.us != null);
  const wins = played.filter((s) => (s.us ?? 0) > (s.them ?? 0)).length;
  const seasons = Object.keys(doc.betting).sort().reverse();
  const curBet = doc.betting[seasons[0]];

  const overview = (
    <div className="flex flex-col gap-8">
      <div className="grid grid-cols-[repeat(auto-fit,minmax(170px,1fr))] gap-3">
        <Metric label={`Record · ${seasons[0] ?? ""}`} value={recordText(wins, played.length - wins)} />
        {curBet && <Metric label="Against the spread" value={recordText(curBet.summary.cover, curBet.summary.noCover, curBet.summary.push)} sub={`${curBet.summary.pct}% covers`} tone={curBet.summary.pct >= 50 ? "good" : "bad"} />}
        <Metric label="Returning production" value={doc.returning?.pct != null ? `${Math.round(doc.returning.pct)}%` : "—"} sub={doc.returning ? `${doc.returning.returning_players} of ${doc.returning.total_players} players back` : undefined} />
        <Metric label="Roster net impact" value={signed(doc.units.Total, 0)} sub="Gains minus losses this offseason" tone={doc.units.Total >= 0 ? "good" : "bad"} />
      </div>
      <div className="flex flex-wrap items-start gap-6">
        <section className="flex min-w-0 flex-[999_1_520px] flex-col gap-3">
          <H3>Schedule &amp; results</H3>
          <div className="card overflow-x-auto">
            <table className="tbl min-w-[560px]">
              <thead><tr><th>Wk</th><th>Opponent</th><th>Result</th><th>Line</th><th /></tr></thead>
              <tbody>
                {doc.schedule.map((s) => {
                  const res = s.us == null ? null : s.us > s.them! ? "W" : s.us < s.them! ? "L" : "T";
                  return (
                    <tr key={s.id}>
                      <td className="mono text-muted">{s.week}</td>
                      <td><span className="flex items-center gap-2"><span className="w-5 text-[12px] text-muted">{s.home ? "vs" : "@"}</span><Opp name={s.opp} refs={refs} /></span></td>
                      <td className="mono whitespace-nowrap">{res ? <><b className={res === "W" ? "text-accent" : res === "L" ? "text-loss" : ""}>{res}</b> {s.us}–{s.them}</> : <span className="text-muted">{dateShort(s.kick)}</span>}</td>
                      <td className="mono whitespace-nowrap text-soft">{s.line ?? "—"}</td>
                      <td className="text-right">{s.hasPage && <Link href={`/games/${s.id}/`} className="whitespace-nowrap text-[13px] font-bold">Preview →</Link>}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </section>
        <section className="flex min-w-0 flex-[1_1_300px] flex-col gap-3">
          <H3>Season stats</H3>
          {doc.stats ? (
            <div className="card p-1">
              <table className="tbl">
                <tbody>
                  {([["Points / game", doc.stats.off_points_pg, 1], ["Yards / game", doc.stats.off_yards_pg, 0], ["3rd down %", doc.stats.off_third_down_pct, 1], ["Points allowed / game", doc.stats.def_points_pg, 1], ["Yards allowed / game", doc.stats.def_yards_pg, 0], ["3rd down % allowed", doc.stats.def_third_down_pct, 1], ["Turnover margin / game", doc.stats.turnover_margin_pg, 2]] as [string, number, number][]).map(([l, v, d]) => (
                    <tr key={l}><td className="text-soft">{l}</td><td className="mono text-right font-semibold">{fmt(v, d)}</td></tr>
                  ))}
                </tbody>
              </table>
              <div className="px-3.5 pb-3 pt-1 text-[12px] text-muted">{doc.stats.season} season · {doc.stats.games} games</div>
            </div>
          ) : <p className="text-muted">No season stats yet.</p>}
        </section>
      </div>
    </div>
  );

  return (
    <Tabs label={`${t.school} sections`} tabs={[
      { id: "overview", label: "Overview", content: overview },
      { id: "turnover", label: "Roster turnover", content: <Turnover doc={doc} refs={refs} /> },
      { id: "transfers", label: "Transfers", content: <Transfers doc={doc} refs={refs} /> },
      { id: "betting", label: "Betting", content: <Betting doc={doc} refs={refs} /> },
      { id: "roster", label: "Roster", content: <Roster doc={doc} /> },
    ]} />
  );
}

function Turnover({ doc, refs }: { doc: TeamDoc; refs: Refs }) {
  const o = doc.overview;
  const tot = doc.production.reduce((a, p) => ({ r: a.r + p.returning, l: a.l + p.lost, i: a.i + p.incoming }), { r: 0, l: 0, i: 0 });
  const net = tot.r + tot.i - tot.l;
  const groups = useMemo(() => POS_ORDER.filter((p) => doc.roster.some((r) => r.grp === p) || doc.production.some((x) => x.pos === p)), [doc]);
  const [pos, setPos] = useState(groups[0] ?? "QB");
  const pp = doc.production.find((p) => p.pos === pos);
  const grpOf = (p: string | null) => {
    const m: Record<string, string> = { CB: "DB", S: "DB", SAF: "DB", FS: "DB", SS: "DB", DE: "DL", DT: "DL", NT: "DL", EDGE: "DL", OT: "OL", G: "OL", C: "OL", IOL: "OL", PK: "K", ATH: "ATH" };
    const u = (p ?? "").toUpperCase();
    return m[u] ?? u;
  };
  return (
    <div className="flex flex-col gap-8">
      <div className="grid grid-cols-[repeat(auto-fit,minmax(150px,1fr))] gap-3">
        <Metric label="Current roster" value={o.roster} />
        <Metric label="Recruits signed" value={o.recruits} />
        <Metric label="Transfers in" value={o.transfersIn} sub={`Net ${signed(o.transfersIn - o.transfersOut, 0)}`} tone={o.transfersIn >= o.transfersOut ? "good" : "bad"} />
        <Metric label="Transfers out" value={o.transfersOut} />
        <Metric label="Drafted" value={o.drafted} />
      </div>

      <section className="card flex flex-col gap-4 p-5">
        <div className="flex flex-wrap items-baseline justify-between gap-2">
          <H3>Production returning, lost and added</H3>
          <span className="text-[13px] text-muted">Weighted stat score from last season, by position</span>
        </div>
        {doc.production.length ? <ProductionChart data={doc.production} /> : <p className="text-muted">No production data.</p>}
        <div className="grid grid-cols-[repeat(auto-fit,minmax(150px,1fr))] gap-3">
          <Metric label="Returning" value={fmtInt(tot.r)} />
          <Metric label="Lost" value={fmtInt(tot.l)} tone="bad" sub="Graduated, drafted or transferred" />
          <Metric label="Incoming (transfers)" value={fmtInt(tot.i)} tone="good" sub="Recruits have no college stats yet" />
          <Metric label="Net change" value={signed(net - tot.r, 0)} tone={tot.i >= tot.l ? "good" : "bad"} sub="Incoming minus lost" />
        </div>
        <details className="text-[13px] text-muted">
          <summary className="cursor-pointer font-semibold text-soft">How production scores work</summary>
          <p className="mt-2 leading-relaxed">Position-specific weighted stats: QB pass yds + 20×pass TD + rush yds + 6×rush TD; RB rush yds + 6×TD + rec yds + 6×rec TD; WR rec yds + 6×TD + 2×rec + rush yds; TE rec yds + 6×TD + 2×rec; DL 3×sacks + 2×TFL + tackles; LB tackles + 3×sacks + 2×TFL; DB tackles + 2×PD + 5×INT; K 3×FG + XP + points. Offensive linemen have no box-score stats, so they don&apos;t count.</p>
        </details>
      </section>

      <section className="card flex flex-col gap-3 p-5">
        <div className="flex flex-wrap items-baseline justify-between gap-2">
          <H3>Net impact by unit</H3>
          <Link href={`/compare/?a=${doc.team.slug}`} className="text-[14px] font-bold">Compare with another team →</Link>
        </div>
        <div className="grid grid-cols-[repeat(auto-fit,minmax(150px,1fr))] gap-3">
          {(["Offense", "Defense", "Special Teams", "Total"] as const).map((u) => (
            <Metric key={u} label={u} value={signed(doc.units[u], 0)} tone={doc.units[u] >= 0 ? "good" : "bad"} />
          ))}
        </div>
        <p className="m-0 text-[13px] leading-relaxed text-muted">Usage-weighted impact of every player gained (transfers in, recruits at 100× rating) minus every player lost (graduated, transferred out, drafted at 300 − pick).</p>
      </section>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <section className="flex flex-col gap-3">
          <H3>Players lost</H3>
          {doc.drafted.length > 0 && (
            <div className="card overflow-x-auto"><table className="tbl"><thead><tr><th>Drafted</th><th>Pos</th><th className="text-right">Pick</th></tr></thead>
              <tbody>{doc.drafted.map((d, i) => <tr key={i}><td className="font-semibold">{d.name ?? "—"}</td><td className="text-soft">{d.pos}</td><td className="mono text-right">#{d.pick}</td></tr>)}</tbody></table></div>
          )}
          <div className="card max-h-[520px] overflow-auto"><table className="tbl"><thead className="sticky top-0 bg-surface"><tr><th>Transferred out</th><th>Pos</th><th>New team</th></tr></thead>
            <tbody>{doc.transfersOut.map((p, i) => <tr key={i}><td className="font-semibold">{p.name}</td><td className="text-soft">{p.pos}</td><td><Opp name={p.team} refs={refs} /></td></tr>)}
              {!doc.transfersOut.length && <tr><td colSpan={3} className="text-muted">None</td></tr>}</tbody></table></div>
        </section>
        <section className="flex flex-col gap-3">
          <H3>Players gained</H3>
          <div className="card max-h-[520px] overflow-auto"><table className="tbl"><thead className="sticky top-0 bg-surface"><tr><th>Transfer in</th><th>Pos</th><th>From</th><th className="text-right">Rating</th></tr></thead>
            <tbody>{doc.transfersIn.map((p, i) => <tr key={i}><td className="font-semibold">{p.name}</td><td className="text-soft">{p.pos}</td><td><Opp name={p.team} refs={refs} /></td><td className="mono text-right">{p.rating ? p.rating.toFixed(2) : "—"}{p.stars ? ` · ${p.stars}★` : ""}</td></tr>)}
              {!doc.transfersIn.length && <tr><td colSpan={4} className="text-muted">None</td></tr>}</tbody></table></div>
          <div className="card max-h-[520px] overflow-auto"><table className="tbl"><thead className="sticky top-0 bg-surface"><tr><th>Recruit</th><th>Pos</th><th>Hometown</th><th className="text-right">Rating</th></tr></thead>
            <tbody>{doc.recruits.map((p, i) => <tr key={i}><td className="font-semibold">{p.name}</td><td className="text-soft">{p.pos}</td><td className="text-soft">{p.home}</td><td className="mono text-right">{p.stars ? `${p.stars}★ ` : ""}{p.rating?.toFixed(4) ?? "—"}</td></tr>)}
              {!doc.recruits.length && <tr><td colSpan={4} className="text-muted">No recruits found</td></tr>}</tbody></table></div>
        </section>
      </div>

      <section className="card flex flex-col gap-4 p-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <H3>Position deep dive</H3>
          <div className="flex items-center gap-2"><label htmlFor="pos" className="text-[13px] text-muted">Position</label>
            <select id="pos" className="field" value={pos} onChange={(e) => setPos(e.target.value)}>{groups.map((g) => <option key={g}>{g}</option>)}</select></div>
        </div>
        {pp && (
          <div className="grid grid-cols-3 gap-3">
            <Metric label="Returning" value={fmtInt(pp.returning)} /><Metric label="Lost" value={fmtInt(pp.lost)} tone="bad" /><Metric label="Incoming" value={fmtInt(pp.incoming)} tone="good" />
          </div>
        )}
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
          <div><div className="mb-2 font-bold">On the roster ({doc.roster.filter((r) => r.grp === pos).length})</div>
            <ul className="m-0 flex list-none flex-col gap-1 p-0 text-[14px]">{doc.roster.filter((r) => r.grp === pos).map((r, i) => <li key={i} className="flex justify-between gap-2"><span>{r.name}</span><span className="text-muted">{r.pos}{r.year ? ` · Yr ${r.year}` : ""}</span></li>)}</ul></div>
          <div><div className="mb-2 font-bold">Arriving</div>
            <ul className="m-0 flex list-none flex-col gap-1 p-0 text-[14px]">
              {doc.transfersIn.filter((p) => grpOf(p.pos) === pos).map((p, i) => <li key={`t${i}`} className="flex justify-between gap-2"><span>{p.name}</span><span className="text-muted">from {p.team}</span></li>)}
              {doc.recruits.filter((p) => grpOf(p.pos) === pos).map((p, i) => <li key={`r${i}`} className="flex justify-between gap-2"><span>{p.name}</span><span className="text-muted">{p.stars ? `${p.stars}★ recruit` : "recruit"}</span></li>)}
            </ul></div>
          <div><div className="mb-2 font-bold">Left</div>
            <ul className="m-0 flex list-none flex-col gap-1 p-0 text-[14px]">
              {doc.transfersOut.filter((p) => grpOf(p.pos) === pos).map((p, i) => <li key={i} className="flex justify-between gap-2"><span>{p.name}</span><span className="text-muted">to {p.team}</span></li>)}
            </ul></div>
        </div>
      </section>
    </div>
  );
}

function Transfers({ doc, refs }: { doc: TeamDoc; refs: Refs }) {
  const p = doc.portal;
  const Flow = ({ rows, title }: { rows: { team: string; n: number }[]; title: string }) => {
    const max = Math.max(1, ...rows.map((r) => r.n));
    return (
      <section className="card flex flex-col gap-2 p-5">
        <H3>{title}</H3>
        {rows.length ? rows.map((r) => (
          <div key={r.team} className="grid grid-cols-[minmax(0,1fr)_120px_28px] items-center gap-3 text-[14px]">
            <Opp name={r.team} refs={refs} />
            <div className="h-2 overflow-hidden rounded bg-chip"><div className="h-full rounded bg-accent" style={{ width: `${(r.n / max) * 100}%` }} /></div>
            <span className="mono text-right font-semibold">{r.n}</span>
          </div>
        )) : <p className="m-0 text-muted">None</p>}
      </section>
    );
  };
  const groups = (list: typeof doc.transfersIn) => {
    const m = new Map<string, typeof list>();
    for (const x of list) if (x.stats && Object.keys(x.stats).length) m.set(x.pos, [...(m.get(x.pos) ?? []), x]);
    return [...m.entries()];
  };
  const StatTables = ({ list, other }: { list: typeof doc.transfersIn; other: string }) => (
    <div className="flex flex-col gap-4">
      {groups(list).map(([pos, ps]) => {
        const keys = Object.keys(ps[0].stats!);
        return (
          <div key={pos} className="card overflow-x-auto">
            <table className="tbl min-w-[640px]"><thead><tr><th>{pos}</th><th>{other}</th>{keys.map((k) => <th key={k} className="text-right">{STAT_NAMES[k] ?? k}</th>)}</tr></thead>
              <tbody>{ps.map((x, i) => <tr key={i}><td className="font-semibold">{x.name}</td><td className="text-soft">{x.team}</td>{keys.map((k) => <td key={k} className="mono text-right">{fmtInt(x.stats![k])}</td>)}</tr>)}</tbody></table>
          </div>
        );
      })}
    </div>
  );
  return (
    <div className="flex flex-col gap-8">
      <div className="grid grid-cols-[repeat(auto-fit,minmax(170px,1fr))] gap-3">
        <Metric label="Incoming players" value={p.in.n} sub={`Total rating ${p.in.total.toFixed(2)} · avg ${fmt(p.in.avg, 2)}`} />
        <Metric label="Outgoing players" value={p.out.n} sub={`Total rating ${p.out.total.toFixed(2)} · avg ${fmt(p.out.avg, 2)}`} />
        <Metric label="Net rating" value={signed(p.in.total - p.out.total, 2)} tone={p.in.total >= p.out.total ? "good" : "bad"} />
      </div>
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Flow rows={p.flowsIn} title="Came from" />
        <Flow rows={p.flowsOut} title="Went to" />
      </div>
      {p.differential.length > 0 && (
        <section className="card flex flex-col gap-3 p-5">
          <H3>Production through the portal</H3>
          <p className="m-0 text-[13px] text-muted">Last season&apos;s stats for players who arrived minus players who left.</p>
          <div className="overflow-x-auto"><table className="tbl min-w-[480px]"><thead><tr><th>Stat</th><th className="text-right">Arrived</th><th className="text-right">Left</th><th className="text-right">Net</th></tr></thead>
            <tbody>{p.differential.map((d) => { const n = d.in - d.out; return (
              <tr key={d.stat}><td><span className="text-muted">{d.cat} · </span>{STAT_NAMES[d.stat] ?? d.stat}</td><td className="mono text-right">{fmtInt(d.in)}</td><td className="mono text-right">{fmtInt(d.out)}</td>
                <td className={`mono text-right font-bold ${n > 0 ? "text-accent" : n < 0 ? "text-loss" : "text-muted"}`}>{signed(n, 0)}</td></tr>); })}</tbody></table></div>
        </section>
      )}
      <section className="flex flex-col gap-3"><H3>Incoming player stats</H3><StatTables list={doc.transfersIn} other="From" /></section>
      <section className="flex flex-col gap-3"><H3>Outgoing player stats</H3><StatTables list={doc.transfersOut} other="To" /></section>
    </div>
  );
}

function Betting({ doc, refs }: { doc: TeamDoc; refs: Refs }) {
  const seasons = Object.keys(doc.betting).sort().reverse();
  const [season, setSeason] = useState(seasons[0]);
  const [wager, setWager] = useState(10);
  const b = doc.betting[season];
  if (!b) return <p className="text-muted">No betting lines for {doc.school}.</p>;
  const ats = (s: typeof b.summary) => recordText(s.cover, s.noCover, s.push);
  return (
    <div className="flex flex-col gap-6">
      <Segmented label="Season" options={seasons.map((s) => ({ value: s, label: s }))} value={season} onChange={setSeason} />
      <div className="grid grid-cols-[repeat(auto-fit,minmax(160px,1fr))] gap-3">
        <Metric label="Record" value={recordText(b.summary.w, b.summary.l)} />
        <Metric label="Against the spread" value={ats(b.summary)} sub={`${b.summary.pct}% covers`} tone={b.summary.pct >= 50 ? "good" : "bad"} />
        <Metric label="As favorite (ATS)" value={ats(b.fav)} sub={`${b.fav.games} games`} />
        <Metric label="As underdog (ATS)" value={ats(b.dog)} sub={`${b.dog.games} games`} />
      </div>
      <section className="card flex flex-col gap-2 p-5">
        <H3>Cover margin by game</H3>
        <p className="m-0 text-[13px] text-muted">Points better (green) or worse (red) than the spread.</p>
        <SimpleBars signed valueLabel="Pts vs spread" data={b.log.map((g) => ({ label: `Wk${g.week} ${g.home ? "vs" : "@"} ${g.opp}`, value: Math.round(g.atsMargin * 10) / 10 }))} height={300} />
      </section>
      <div className="card overflow-x-auto">
        <table className="tbl min-w-[640px]">
          <thead><tr><th>Wk</th><th>Opponent</th><th>Role</th><th>Line</th><th>Score</th><th>ATS</th><th className="text-right">Margin</th></tr></thead>
          <tbody>{b.log.map((g, i) => (
            <tr key={i}>
              <td className="mono text-muted">{g.week}</td>
              <td><span className="flex items-center gap-2"><span className="w-5 text-[12px] text-muted">{g.home ? "vs" : "@"}</span><Opp name={g.opp} refs={refs} /></span></td>
              <td className="text-soft">{g.role}</td>
              <td className="mono">{g.role === "Pick'em" ? "PK" : `${g.role === "Favorite" ? "−" : "+"}${fmt(g.line)}`}</td>
              <td className="mono"><b className={g.result === "W" ? "text-accent" : g.result === "L" ? "text-loss" : ""}>{g.result}</b> {g.score}</td>
              <td className={g.ats === "Covered" ? "font-semibold text-accent" : g.ats === "No Cover" ? "text-loss" : "text-muted"}>{g.ats}</td>
              <td className="mono text-right">{signed(g.atsMargin)}</td>
            </tr>))}</tbody>
        </table>
      </div>
      <section className="card flex flex-col gap-4 p-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <H3>If you bet on every game</H3>
          <label className="flex items-center gap-2 text-[14px] text-soft">Wager per game $
            <input type="number" min={1} max={1000} value={wager} onChange={(e) => setWager(Math.max(1, Number(e.target.value) || 1))} className="field w-24" /></label>
        </div>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <Metric label={`${doc.school} to win (moneyline)`} value={money(b.mlProfit * wager)} tone={b.mlProfit >= 0 ? "good" : "bad"} />
          <Metric label={`${doc.school} against the spread (−110)`} value={money(b.atsProfit * wager)} tone={b.atsProfit >= 0 ? "good" : "bad"} />
        </div>
      </section>
    </div>
  );
}

function Roster({ doc }: { doc: TeamDoc }) {
  const [grp, setGrp] = useState("all");
  const groups = POS_ORDER.filter((p) => doc.roster.some((r) => r.grp === p));
  const rows = grp === "all" ? doc.roster : doc.roster.filter((r) => r.grp === grp);
  return (
    <div className="flex flex-col gap-4">
      <Segmented label="Position group" options={[{ value: "all", label: `All ${doc.roster.length}` }, ...groups.map((g) => ({ value: g, label: g }))]} value={grp} onChange={setGrp} />
      <div className="card overflow-x-auto">
        <table className="tbl min-w-[560px]">
          <thead><tr><th>#</th><th>Player</th><th>Pos</th><th>Year</th><th>Height</th><th className="text-right">Weight</th></tr></thead>
          <tbody>{rows.map((r, i) => (
            <tr key={i}><td className="mono text-muted">{r.jersey ?? ""}</td><td className="font-semibold">{r.name}</td><td className="text-soft">{r.pos}</td><td className="text-soft">{r.year ?? "—"}</td><td className="mono">{heightText(r.height)}</td><td className="mono text-right">{r.weight ?? "—"}</td></tr>
          ))}</tbody>
        </table>
      </div>
    </div>
  );
}
