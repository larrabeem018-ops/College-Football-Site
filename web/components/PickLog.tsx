"use client";
import Link from "next/link";
import { useState } from "react";
import type { TrackRecord } from "@/lib/types";
import { Chips } from "./Tabs";
import { ResultTag, TierTag } from "./ui";
import { UnitsLine } from "./charts";

export function UnitsChart({ series }: { series: TrackRecord["series"] }) {
  return <UnitsLine series={[
    { name: "Watchlist", color: "#2FD27A", points: series.watchlist },
    { name: "Big disagreements", color: "#F5B83D", dash: "6 4", points: series.big_gap },
    { name: "Every 3+ pt gap", color: "#8D99A8", dash: "2 4", points: series.all },
  ]} />;
}

export default function PickLog({ log }: { log: TrackRecord["log"] }) {
  const [f, setF] = useState<"fav_value" | "big_gap" | "lean" | "all">("fav_value");
  const rows = log.filter((r) => f === "all" || r.tier === f);
  return (
    <div className="flex flex-col gap-3">
      <Chips label="Category" value={f} onChange={setF} options={[
        { value: "fav_value", label: "Watchlist", count: log.filter((r) => r.tier === "fav_value").length },
        { value: "big_gap", label: "Big disagreements", count: log.filter((r) => r.tier === "big_gap").length },
        { value: "lean", label: "Leans", count: log.filter((r) => r.tier === "lean").length },
        { value: "all", label: "All picks", count: log.length }]} />
      <div className="card max-h-[640px] overflow-auto">
        <table className="tbl min-w-[720px]">
          <thead className="sticky top-0 bg-surface"><tr><th>Wk</th><th>Matchup</th><th>Pick</th><th>Category</th><th className="text-right">Gap</th><th className="text-right">Score</th><th>Result</th><th>Source</th></tr></thead>
          <tbody>{rows.map((r) => (
            <tr key={`${r.id}`}><td className="mono text-muted">{r.week}</td><td><Link href={`/games/${r.id}/`} className="text-ink hover:text-accent">{r.away} @ {r.home}</Link></td><td className="font-semibold">{r.pick}</td><td><TierTag tier={r.tier} /></td>
              <td className="mono text-right">{r.gap.toFixed(1)}</td><td className="mono text-right">{r.score ?? "—"}</td><td>{r.result === "Pending" ? <span className="text-muted">Pending</span> : <ResultTag result={r.result} />}</td><td className="text-[13px] capitalize text-muted">{r.source}</td></tr>
          ))}</tbody>
        </table>
      </div>
      <p className="m-0 text-[12px] text-muted">Game links work for weeks with a published preview. Live picks were saved before kickoff; backtest picks were rebuilt using only information available before each game.</p>
    </div>
  );
}
