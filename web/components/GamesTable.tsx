"use client";
import Link from "next/link";
import { useMemo, useState } from "react";
import type { Game } from "@/lib/types";
import { favLine, kickShort } from "@/lib/format";
import { BadgePair } from "./TeamBadge";
import { GapBar, ResultTag, TierTag } from "./ui";
import { Chips } from "./Tabs";

type Filter = "edges" | "fav_value" | "big_gap" | "lean" | "all";
type Sort = "edge" | "kick";

/** Every game in a week with the model's line, Vegas and the gap. `compact` = home page "top edges" list. */
export default function GamesTable({ games, compact = false }: { games: Game[]; compact?: boolean }) {
  const [filter, setFilter] = useState<Filter>("edges");
  const [sort, setSort] = useState<Sort>("edge");
  const [q, setQ] = useState("");
  const [conf, setConf] = useState("all");
  const confs = useMemo(() => [...new Set(games.flatMap((g) => [g.homeConf, g.awayConf]).filter(Boolean) as string[])].sort(), [games]);
  const count = (f: Filter) => games.filter((g) => match(g, f)).length;

  let rows = games.filter((g) => match(g, filter));
  if (conf !== "all") rows = rows.filter((g) => g.homeConf === conf || g.awayConf === conf);
  if (q.trim()) {
    const s = q.trim().toLowerCase();
    rows = rows.filter((g) => g.home.school.toLowerCase().includes(s) || g.away.school.toLowerCase().includes(s));
  }
  rows = [...rows].sort((a, b) => (sort === "edge" ? Math.abs(b.edge ?? 0) - Math.abs(a.edge ?? 0) : a.kick.localeCompare(b.kick)));
  if (compact) rows = rows.slice(0, 8);
  const showResult = rows.some((g) => g.result);

  const opts: { value: Filter; label: string; count: number }[] = [
    { value: "edges", label: "All edges", count: count("edges") },
    { value: "fav_value", label: "Watchlist", count: count("fav_value") },
    ...(count("big_gap") ? [{ value: "big_gap" as Filter, label: "Big disagreement", count: count("big_gap") }] : []),
    { value: "lean", label: "Lean", count: count("lean") },
    ...(!compact ? [{ value: "all" as Filter, label: "Every game", count: games.length }] : []),
  ];

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <Chips label="Filter by category" options={opts} value={filter} onChange={setFilter} />
        {!compact && (
          <div className="flex flex-wrap gap-2">
            <label className="sr-only" htmlFor="gt-q">Search teams</label>
            <input id="gt-q" className="field w-48" type="search" placeholder="Search teams" value={q} onChange={(e) => setQ(e.target.value)} />
            <label className="sr-only" htmlFor="gt-conf">Conference</label>
            <select id="gt-conf" className="field" value={conf} onChange={(e) => setConf(e.target.value)}>
              <option value="all">All conferences</option>
              {confs.map((c) => <option key={c} value={c}>{c}</option>)}
            </select>
            <label className="sr-only" htmlFor="gt-sort">Sort</label>
            <select id="gt-sort" className="field" value={sort} onChange={(e) => setSort(e.target.value as Sort)}>
              <option value="edge">Biggest gap first</option>
              <option value="kick">By kickoff</option>
            </select>
          </div>
        )}
      </div>
      <ul className="card m-0 flex list-none flex-col p-0 sm:hidden">
        {rows.map((g) => (
          <li key={g.id} className="border-t border-line first:border-t-0">
            <Link href={`/games/${g.id}/`} className="flex flex-col gap-2 p-4 text-ink hover:text-ink">
              <div className="flex items-center gap-3">
                <BadgePair away={g.away} home={g.home} size={30} />
                <span className="min-w-0 flex-1 font-bold leading-tight">{g.away.school} <span className="font-medium text-muted">{g.neutral ? "vs" : "@"}</span> {g.home.school}</span>
                <ResultTag result={g.result} />
              </div>
              <div className="flex items-center justify-between gap-2 text-[13px]">
                <span className="text-muted">{kickShort(g.kick)}</span>
                <span className="mono text-soft">Vegas {favLine(g.home, g.away, g.spread)} · Model {favLine(g.home, g.away, g.modelSpread != null ? Math.round(g.modelSpread * 10) / 10 : null)}</span>
              </div>
              <div className="flex items-center justify-between gap-2">
                <span className="flex items-center gap-2 text-[14px]">{g.tier && g.tier !== "pass" ? <b>{g.pick}</b> : <span className="text-muted">No lean</span>}<TierTag tier={g.tier} /></span>
                <span className="mono text-[13px] font-semibold">{Math.abs(g.edge ?? 0).toFixed(1)} gap</span>
              </div>
            </Link>
          </li>
        ))}
        {!rows.length && <li className="p-8 text-center text-muted">No games match these filters.</li>}
      </ul>
      <div className="card hidden overflow-x-auto sm:block">
        <table className="tbl min-w-[820px]">
          <thead>
            <tr>
              <th className="pl-5">Matchup</th><th>Kickoff</th><th>Vegas</th><th>Model</th><th className="w-[180px]">Gap</th><th>Model lean</th>
              {showResult && <th>Result</th>}
            </tr>
          </thead>
          <tbody>
            {rows.map((g) => (
              <tr key={g.id}>
                <td className="pl-5">
                  <Link href={`/games/${g.id}/`} className="flex items-center gap-3 font-bold text-ink hover:text-accent">
                    <BadgePair away={g.away} home={g.home} size={30} />
                    <span>{g.away.school} <span className="font-medium text-muted">{g.neutral ? "vs" : "@"}</span> {g.home.school}</span>
                  </Link>
                </td>
                <td className="whitespace-nowrap text-soft">{kickShort(g.kick)}</td>
                <td className="mono whitespace-nowrap">{favLine(g.home, g.away, g.spread)}</td>
                <td className="mono whitespace-nowrap">{favLine(g.home, g.away, g.modelSpread != null ? Math.round(g.modelSpread * 10) / 10 : null)}</td>
                <td><GapBar edge={g.edge} tier={g.tier} /></td>
                <td className="whitespace-nowrap">
                  {g.tier && g.tier !== "pass" ? <span className="mr-2 font-bold">{g.pick}</span> : <span className="mr-2 text-muted">—</span>}
                  <TierTag tier={g.tier} />
                </td>
                {showResult && <td><ResultTag result={g.result} /></td>}
              </tr>
            ))}
            {!rows.length && (
              <tr><td colSpan={7} className="py-10 text-center text-muted">No games match these filters.</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function match(g: Game, f: Filter) {
  if (f === "all") return true;
  if (f === "edges") return g.tier === "fav_value" || g.tier === "big_gap" || g.tier === "lean";
  return g.tier === f;
}
