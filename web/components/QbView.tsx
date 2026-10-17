"use client";
import { useEffect, useMemo, useState } from "react";
import type { QbFile, QbRow } from "@/lib/types";
import { fmt, fmtInt } from "@/lib/format";
import { Segmented } from "./Tabs";
import { HBars, QbRadar, QbrLine } from "./charts";
import Headshot from "./Headshot";
import PassHeatmap, { HEAT_METRICS, HeatLegend, type HeatMetric } from "./PassHeatmap";

const METRICS: Record<string, { key: keyof QbRow; fmt: (v: number) => string; blurb: string }> = {
  "Passer rating": { key: "rating", fmt: (v) => v.toFixed(1), blurb: "NCAA passer efficiency: (8.4×Yds + 330×TD + 100×Comp − 200×INT) ÷ Att." },
  "Passing yards": { key: "yds", fmt: (v) => Math.round(v).toLocaleString(), blurb: "Total passing yards." },
  "Passing TDs": { key: "td", fmt: (v) => v.toFixed(0), blurb: "Total passing touchdowns." },
  "Yards per attempt": { key: "ypa", fmt: (v) => v.toFixed(2), blurb: "Passing yards per attempt." },
  "Completion %": { key: "compPct", fmt: (v) => `${v.toFixed(1)}%`, blurb: "Completions ÷ attempts." },
  "ESPN QBR": { key: "qbr", fmt: (v) => v.toFixed(1), blurb: "ESPN's Total QBR. ESPN doesn't publish one for every QB, so only QBs with a QBR are ranked." },
};

export default function QbView({ seasons }: { seasons: number[] }) {
  const [season, setSeason] = useState(seasons[0]);
  const [data, setData] = useState<QbFile | null>(null);
  useEffect(() => { setData(null); fetch(`/data/qbs/${season}.json`).then((r) => r.json()).then(setData); }, [season]);
  return (
    <div className="flex flex-col gap-8">
      <Segmented label="Season" options={seasons.map((s) => ({ value: s, label: `${s}${s === seasons[0] ? " (in progress)" : ""}` }))} value={season} onChange={setSeason} />
      {data ? <Inner key={season} data={data} /> : <p className="text-muted">Loading quarterbacks…</p>}
    </div>
  );
}

function Inner({ data }: { data: QbFile }) {
  const qbs = data.qbs;
  const maxAtt = Math.max(...qbs.map((q) => q.att));
  const sorted = [...qbs.map((q) => q.att)].sort((a, b) => a - b);
  const q90 = sorted[Math.floor(sorted.length * 0.9)] ?? 0;
  const [metric, setMetric] = useState("Passer rating");
  const [level, setLevel] = useState<"fbs" | "all">("fbs");
  const [minAtt, setMinAtt] = useState(Math.min(15 * data.gamesPlayed, q90, maxAtt));
  const [topN, setTopN] = useState(15);
  const m = METRICS[metric];
  const ranked = useMemo(() => qbs.filter((q) => q.att >= minAtt && (level === "all" || q.fbs) && q[m.key] != null)
    .sort((a, b) => (b[m.key] as number) - (a[m.key] as number)), [qbs, minAtt, level, m.key]);
  const top = ranked.slice(0, topN);
  const [aId, setA] = useState<number | null>(null);
  const [bId, setB] = useState<number | null>(null);
  const [heat, setHeat] = useState<HeatMetric>("pct");
  const a = qbs.find((q) => q.id === (aId ?? ranked[0]?.id)), b = qbs.find((q) => q.id === (bId ?? ranked[1]?.id));
  const byName = useMemo(() => [...qbs].sort((x, y) => x.name.localeCompare(y.name)), [qbs]);
  const pick = (id: string) => { setA(Number(id)); document.getElementById("h2h")?.scrollIntoView({ behavior: "smooth" }); };

  return (
    <>
      <section className="flex flex-col gap-4">
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <label className="flex flex-col gap-1.5 text-[13px] font-semibold text-muted">Rank by
            <select className="field" value={metric} onChange={(e) => setMetric(e.target.value)}>{Object.keys(METRICS).map((k) => <option key={k}>{k}</option>)}</select></label>
          <div className="flex flex-col gap-1.5 text-[13px] font-semibold text-muted">Level
            <Segmented label="Level" options={[{ value: "fbs", label: "FBS" }, { value: "all", label: "All levels" }]} value={level} onChange={setLevel} /></div>
          <label className="flex flex-col gap-1.5 text-[13px] font-semibold text-muted">Minimum attempts: <span className="mono text-ink">{minAtt}</span>
            <input type="range" min={0} max={maxAtt} step={5} value={minAtt} onChange={(e) => setMinAtt(Number(e.target.value))} /></label>
          <label className="flex flex-col gap-1.5 text-[13px] font-semibold text-muted">QBs shown: <span className="mono text-ink">{topN}</span>
            <input type="range" min={5} max={25} value={topN} onChange={(e) => setTopN(Number(e.target.value))} /></label>
        </div>
        <p className="m-0 text-[13px] text-muted">{m.blurb} Top {top.length} of {ranked.length} qualifying QBs. <b className="text-soft">Click a bar</b> to put that QB in the head-to-head.</p>
        {top.length ? (
          <div className="card p-4">
            <HBars data={top.map((q) => ({ key: String(q.id), label: `${q.name} · ${q.team}`, value: q[m.key] as number }))} format={m.fmt} onPick={pick} selected={[String(a?.id), String(b?.id)]} />
          </div>
        ) : <p className="text-muted">No quarterbacks match. Try lowering the minimum attempts.</p>}
        <div className="card overflow-x-auto">
          <table className="tbl min-w-[860px]">
            <thead><tr><th>#</th><th>Quarterback</th><th>Team</th><th>Conf</th>{["Att", "Comp %", "Yds", "TD", "INT", "Y/A", "Rating", "QBR"].map((h) => <th key={h} className="text-right">{h}</th>)}</tr></thead>
            <tbody>{top.map((q, i) => (
              <tr key={q.id}><td className="mono text-muted">{i + 1}</td><td><button type="button" onClick={() => pick(String(q.id))} className="flex cursor-pointer items-center gap-2.5 font-bold text-ink hover:text-accent"><Headshot id={q.id} name={q.name} size={32} />{q.name}</button></td>
                <td className="text-soft">{q.team}</td><td className="text-muted">{q.conf}</td>
                <td className="mono text-right">{q.att}</td><td className="mono text-right">{fmt(q.compPct)}</td><td className="mono text-right">{fmtInt(q.yds)}</td><td className="mono text-right">{q.td}</td><td className="mono text-right">{q.int}</td>
                <td className="mono text-right">{fmt(q.ypa, 2)}</td><td className="mono text-right">{fmt(q.rating)}</td><td className="mono text-right">{fmt(q.qbr)}</td></tr>
            ))}</tbody>
          </table>
        </div>
      </section>

      <section id="h2h" className="flex scroll-mt-24 flex-col gap-4">
        <h2 className="display m-0 text-[30px]">Head to head</h2>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          {([["Quarterback 1", a, setA], ["Quarterback 2", b, setB]] as const).map(([label, q, set]) => (
            <label key={label} className="flex flex-col gap-1.5 text-[13px] font-semibold text-muted">{label}
              <select className="field" value={q?.id ?? ""} onChange={(e) => set(Number(e.target.value))}>
                {byName.map((x) => <option key={x.id} value={x.id}>{x.name} — {x.team}</option>)}
              </select></label>
          ))}
        </div>
        {a && b && a.id !== b.id ? (
          <>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              {[{ q: a, c: "text-accent" }, { q: b, c: "text-blue-text" }].map(({ q, c }) => (
                <div key={q.id} className="card flex items-center gap-4 p-4">
                  <Headshot id={q.id} name={q.name} size={88} />
                  <div className="min-w-0">
                    <div className={`display text-[28px] leading-none ${c}`}>{q.name}</div>
                    <div className="mt-1 text-[14px] text-soft">{q.team} · {q.conf}</div>
                    <div className="mono mt-2 text-[13px] text-muted">{q.comp}/{q.att} · {fmtInt(q.yds)} yds · {q.td} TD · {q.int} INT</div>
                  </div>
                </div>
              ))}
            </div>

            <section className="card flex flex-col gap-4 p-5" aria-labelledby="heat-h">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <h3 id="heat-h" className="display m-0 text-[24px]">Where they throw</h3>
                  <p className="m-0 mt-1 text-[13px] text-muted">Every charted pass by depth and direction, seen from behind the quarterback. Short and deep follow the play-by-play charting.</p>
                </div>
                <Segmented label="Heatmap metric" options={HEAT_METRICS} value={heat} onChange={setHeat} />
              </div>
              <HeatLegend metric={heat} />
              <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
                {[{ q: a, c: "text-accent" }, { q: b, c: "text-blue-text" }].map(({ q, c }) => (
                  <div key={q.id} className="flex flex-col gap-2">
                    <div className={`font-bold ${c}`}>{q.name}</div>
                    <PassHeatmap name={q.name} loc={q.locations} avg={data.zoneAvg} metric={heat} />
                  </div>
                ))}
              </div>
            </section>

            <div className="grid grid-cols-1 gap-4 lg:grid-cols-[3fr_2fr]">
              <div className="card p-4">
                <QbRadar a={{ name: a.name, values: a.radar }} b={{ name: b.name, values: b.radar }} />
                <p className="m-0 px-2 text-[12px] text-muted">Each stat is scaled 0–100 against every QB this season (100 = best). Interceptions are flipped so fewer is better.</p>
              </div>
              <div className="card overflow-x-auto p-1">
                <table className="tbl">
                  <thead><tr><th>Stat</th><th className="text-right text-accent">{a.name}</th><th className="text-right text-blue-text">{b.name}</th></tr></thead>
                  <tbody>{([["Team", (q: QbRow) => q.team], ["Attempts", (q: QbRow) => q.att], ["Completion %", (q: QbRow) => fmt(q.compPct)], ["Pass yards", (q: QbRow) => fmtInt(q.yds)], ["TD", (q: QbRow) => q.td], ["INT", (q: QbRow) => q.int], ["Yards / attempt", (q: QbRow) => fmt(q.ypa, 2)], ["Passer rating", (q: QbRow) => fmt(q.rating)], ["QBR", (q: QbRow) => fmt(q.qbr)]] as [string, (q: QbRow) => React.ReactNode][]).map(([l, f]) => (
                    <tr key={l}><td className="text-soft">{l}</td><td className="mono text-right">{f(a)}</td><td className="mono text-right">{f(b)}</td></tr>
                  ))}</tbody>
                </table>
              </div>
            </div>
            <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
              {[{ q: a, c: "#2FD27A" }, { q: b, c: "#5AA9F0" }].map(({ q, c }) => (
                <div key={q.id} className="card flex flex-col gap-3 p-4">
                  <div className="font-bold">{q.name} · QBR by week</div>
                  <QbrLine color={c} data={q.games.map((g) => ({ label: `Wk${g.week}`, qbr: g.qbr }))} />
                  <div className="overflow-x-auto">
                    <table className="tbl min-w-[480px]">
                      <thead><tr><th>Wk</th><th>Opponent</th><th className="text-right">C/A</th><th className="text-right">Yds</th><th className="text-right">TD</th><th className="text-right">INT</th><th className="text-right">QBR</th></tr></thead>
                      <tbody>{q.games.map((g, i) => (
                        <tr key={i}><td className="mono text-muted">{g.week}</td><td>{g.opp}</td><td className="mono text-right">{g.comp}/{g.att}</td><td className="mono text-right">{g.yds}</td><td className="mono text-right">{g.td}</td><td className="mono text-right">{g.int}</td><td className="mono text-right">{fmt(g.qbr)}</td></tr>
                      ))}</tbody>
                    </table>
                  </div>
                </div>
              ))}
            </div>
            <p className="m-0 text-[12px] text-muted">ESPN doesn&apos;t publish QBR for every game (often missing for early buy games), so some weeks show a gap. Every other column is the real box score.</p>
          </>
        ) : <p className="text-amber">Pick two different quarterbacks.</p>}
      </section>
    </>
  );
}
