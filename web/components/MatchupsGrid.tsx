"use client";
import Link from "next/link";
import { useMemo, useState } from "react";
import type { Game } from "@/lib/types";
import { favLine, kickLong } from "@/lib/format";
import TeamBadge from "./TeamBadge";
import { TierTag } from "./ui";

export default function MatchupsGrid({ games }: { games: Game[] }) {
  const [conf, setConf] = useState("all");
  const [q, setQ] = useState("");
  const confs = useMemo(() => [...new Set(games.flatMap((g) => [g.homeConf, g.awayConf]).filter(Boolean) as string[])].sort(), [games]);
  let rows = conf === "all" ? games : games.filter((g) => g.homeConf === conf || g.awayConf === conf);
  if (q.trim()) {
    const s = q.trim().toLowerCase();
    rows = rows.filter((g) => g.home.school.toLowerCase().includes(s) || g.away.school.toLowerCase().includes(s));
  }
  // group by calendar day (ET)
  const days = new Map<string, Game[]>();
  for (const g of rows) {
    const d = new Date(g.kick).toLocaleDateString("en-US", { weekday: "long", month: "long", day: "numeric", timeZone: "America/New_York" });
    days.set(d, [...(days.get(d) ?? []), g]);
  }
  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-center gap-2">
        <label className="sr-only" htmlFor="mg-q">Search teams</label>
        <input id="mg-q" className="field w-56" type="search" placeholder="Search teams" value={q} onChange={(e) => setQ(e.target.value)} />
        <label className="sr-only" htmlFor="mg-conf">Conference</label>
        <select id="mg-conf" className="field" value={conf} onChange={(e) => setConf(e.target.value)}>
          <option value="all">All conferences</option>
          {confs.map((c) => <option key={c} value={c}>{c}</option>)}
        </select>
        <span className="text-[13px] text-muted">{rows.length} games</span>
      </div>
      {[...days.entries()].map(([day, gs]) => (
        <section key={day} className="flex flex-col gap-3">
          <h2 className="eyebrow m-0 text-muted">{day}</h2>
          <div className="grid grid-cols-[repeat(auto-fill,minmax(min(100%,380px),1fr))] gap-3">
            {gs.map((g) => (
              <Link key={g.id} href={`/games/${g.id}/`} className="card flex flex-col gap-3 p-4 text-ink hover:border-accent hover:text-ink">
                <div className="flex items-center justify-between text-[12px] font-semibold text-muted">
                  <span>{kickLong(g.kick).split(" · ")[1]}</span>
                  {g.homeScore != null ? <span className="text-soft">Final</span> : <span>{g.overUnder != null ? `O/U ${g.overUnder}` : ""}</span>}
                </div>
                {[g.away, g.home].map((t, i) => (
                  <div key={t.school} className="flex items-center gap-3">
                    <TeamBadge team={t} size={32} />
                    <span className="flex-1 font-bold">{t.school}</span>
                    {g.homeScore != null && <span className="mono font-semibold">{i === 0 ? g.awayScore : g.homeScore}</span>}
                  </div>
                ))}
                <div className="flex flex-wrap items-center justify-between gap-2 border-t border-line pt-3 text-[13px]">
                  <span className="mono text-soft">{favLine(g.home, g.away, g.spread)}</span>
                  <span className="flex items-center gap-2">{g.tier && g.tier !== "pass" && <span className="font-semibold">{g.pick}</span>}<TierTag tier={g.tier} /></span>
                </div>
              </Link>
            ))}
          </div>
        </section>
      ))}
    </div>
  );
}
