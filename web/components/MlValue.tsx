import Link from "next/link";
import type { MlFile, MlRow } from "@/lib/types";
import { kickShort } from "@/lib/format";
import TeamBadge from "./TeamBadge";
import { ResultTag, SectionTitle } from "./ui";

const pct = (v: number) => `${Math.round(v * 100)}%`;
const odds = (ml: number) => (ml > 0 ? `+${ml}` : `${ml}`);
const roi = (v?: number | null) => (v == null ? "—" : `${v > 0 ? "+" : ""}${v.toFixed(1)}%`);

export function MlTable({ rows, showWeek = false }: { rows: MlRow[]; showWeek?: boolean }) {
  const anyDone = rows.some((r) => r.result !== "Pending");
  return (
    <div className="card overflow-x-auto">
      <table className="tbl min-w-[860px]">
        <thead>
          <tr>
            {showWeek && <th>Wk</th>}
            <th className="pl-5">Underdog</th><th>Kickoff</th><th className="text-right">Spread</th><th className="text-right">Moneyline</th>
            <th className="text-right">Market win %</th><th className="text-right">Model win %</th><th className="text-right">Blended win %</th><th className="text-right">Value</th>
            {anyDone && <th>Result</th>}
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={`${r.id}-${r.team.school}`}>
              {showWeek && <td className="mono text-muted">{r.week}</td>}
              <td className="pl-5">
                <Link href={`/games/${r.id}/`} className="flex items-center gap-3 font-bold text-ink hover:text-accent">
                  <TeamBadge team={r.team} size={30} />
                  <span>{r.team.school} <span className="font-medium text-muted">{r.home ? "vs" : "at"} {r.opp}</span></span>
                </Link>
              </td>
              <td className="whitespace-nowrap text-soft">{kickShort(r.kick)}</td>
              <td className="mono text-right">{r.line != null ? `+${Math.abs(r.line).toFixed(1)}` : "—"}</td>
              <td className="mono text-right font-bold">{odds(r.ml)}</td>
              <td className="mono text-right text-soft">{pct(r.pMkt)}</td>
              <td className="mono text-right text-soft">{pct(r.pModel)}</td>
              <td className="mono text-right font-semibold">{pct(r.pBlend)}</td>
              <td className="mono text-right font-semibold text-accent">+{(r.ev * 100).toFixed(1)}%</td>
              {anyDone && <td className="whitespace-nowrap">{r.result === "Pending" ? <span className="text-muted">Pending</span> : <><ResultTag result={r.result} /> <span className="mono text-[12px] text-muted">{r.score}</span></>}</td>}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/** Picks page section: this week's underdog moneylines with positive blended value. */
export default function MlValue({ ml, week }: { ml: MlFile; week: number }) {
  const rows = ml.weeks[String(week)] ?? [];
  const bt = ml.model.backtest;
  return (
    <section aria-labelledby="ml-h" className="flex flex-col gap-4">
      <SectionTitle id="ml-h" right={<Link href="/model/#moneyline" className="font-semibold">How it&apos;s done →</Link>}>Moneyline value · Week {week}</SectionTitle>
      <p className="m-0 max-w-[860px] text-[14px] leading-relaxed text-soft">
        Underdogs whose moneyline looks too long. The raw model is overconfident when it disagrees with Vegas, so the win % used here is a <b className="text-ink">blend</b>: mostly the market&apos;s price, nudged toward the model. In a two-season backtest, betting every flagged underdog returned <b className="text-ink">{roi(bt.all.roi)}</b> per bet ({bt.all.bets} bets), versus <b className="text-ink">{roi(bt.every_dog.roi)}</b> for betting every underdog. Edges are thin and prices move, so check the current line.
      </p>
      <div className="grid grid-cols-[repeat(auto-fit,minmax(190px,1fr))] gap-3">
        {Object.entries(bt.by_season).map(([y, s]) => (
          <div key={y} className="card p-4"><div className="text-[12px] font-semibold text-muted">Backtest {y}</div>
            <div className={`mono mt-1 text-[22px] font-semibold ${(s.roi ?? 0) >= 0 ? "text-accent" : "text-loss"}`}>{roi(s.roi)}</div>
            <div className="text-[12px] text-muted">{s.bets} bets · {s.units != null && (s.units > 0 ? "+" : "")}{s.units}u</div></div>
        ))}
        <div className="card p-4"><div className="text-[12px] font-semibold text-muted">Live this season</div>
          <div className={`mono mt-1 text-[22px] font-semibold ${ml.live.roi == null ? "" : ml.live.roi >= 0 ? "text-accent" : "text-loss"}`}>{ml.live.bets ? `${ml.live.won}–${ml.live.bets - ml.live.won}` : "Starts now"}</div>
          <div className="text-[12px] text-muted">{ml.live.bets ? `${roi(ml.live.roi)} · ${ml.live.units > 0 ? "+" : ""}${ml.live.units}u` : `${ml.live.pending} pending`}</div></div>
      </div>
      {rows.length ? <MlTable rows={rows} /> : <p className="text-muted">No underdogs rate as value this week.</p>}
    </section>
  );
}
