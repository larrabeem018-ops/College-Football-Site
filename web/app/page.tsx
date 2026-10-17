import Link from "next/link";
import { currentWeek, getMeta, getTrackRecord } from "@/lib/data";
import { favLine, kickShort, recordText } from "@/lib/format";
import GamesTable from "@/components/GamesTable";
import TeamBadge from "@/components/TeamBadge";
import { Arrow, SectionTitle, StatCard, TierTag } from "@/components/ui";

const TOOLS = [
  { href: "/teams/", title: "Team pages", desc: "One home per team: schedule, roster turnover, transfers, ATS record and a side-by-side comparison.", icon: <path d="M12 3l8 4v5c0 5-3.5 8-8 9-4.5-1-8-4-8-9V7z" /> },
  { href: "/quarterbacks/", title: "Quarterbacks", desc: "Who's playing best right now, head-to-head profiles and weekly QBR.", icon: <polygon points="12,3 20,9 17,19 7,19 4,9" /> },
  { href: "/portal/", title: "Transfer Portal", desc: "Who won the cycle, where players went, and net rating by team.", icon: <><path d="M3 6h6l6 12h6" /><path d="M3 18h6l6-12h6" /></> },
  { href: "/betting/", title: "ATS Results", desc: "Cover rates, upsets, nail-biters and favorite/underdog splits for every team.", icon: <><polyline points="4,17 10,10 14,13 20,6" /><polyline points="14,6 20,6 20,12" /></> },
];

export default function Home() {
  const meta = getMeta();
  const wk = currentWeek();
  const tr = getTrackRecord();
  const games = wk?.games ?? [];
  const watch = games.filter((g) => g.tier === "fav_value");
  const edges = games.filter((g) => g.tier && g.tier !== "pass");
  const byGap = (a: { edge: number | null }, b: { edge: number | null }) => Math.abs(b.edge ?? 0) - Math.abs(a.edge ?? 0);
  const featured = [...watch].sort(byGap)[0] ?? [...edges].sort(byGap)[0];
  const fav = tr.tiers.find((t) => t.tier === "fav_value");
  const sw = tr.season_records.watchlist;
  const all = tr.season_records.all;

  return (
    <>
      <section className="flex flex-wrap items-stretch gap-8">
        <div className="flex min-w-0 flex-[1_1_520px] flex-col justify-center gap-5">
          <div className="eyebrow inline-flex items-center gap-2 self-start rounded-full bg-accent-tint px-3.5 py-1.5 text-accent">
            <span className="h-2 w-2 rounded-full bg-accent" />Week {wk?.week ?? "—"} · {meta.season} season
          </div>
          <h1 className="display m-0 text-[48px] leading-[0.95] sm:text-[68px]">
            {games.length} games.{" "}
            <span className="text-accent">{watch.length ? `${watch.length} on the watchlist.` : `${edges.length} model edges.`}</span>
          </h1>
          <p className="m-0 max-w-[580px] text-[18px] leading-relaxed text-soft">
            Our score model sets its own line for every game. Start with the spots where it disagrees with Vegas, then dig into any matchup, team, quarterback or transfer.
          </p>
          <div className="flex flex-wrap gap-3">
            <Link href={wk ? `/picks/${wk.week}/` : "/picks/"} className="inline-flex h-12 items-center gap-2 rounded-xl bg-accent px-5 font-bold text-[#06120B] hover:bg-accent-hover hover:text-[#06120B]">
              See Week {wk?.week} picks <Arrow />
            </Link>
            <Link href="/matchups/" className="inline-flex h-12 items-center rounded-xl border border-line-strong px-5 font-bold text-ink hover:border-accent hover:text-ink">All matchups</Link>
          </div>
        </div>

        {featured && (
          <Link href={`/games/${featured.id}/`} className="card flex min-w-0 flex-[1_1_420px] flex-col gap-5 rounded-[20px] p-6 text-ink hover:border-accent hover:text-ink">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <span className="eyebrow text-amber">{featured.tier === "fav_value" ? "Top watchlist game" : "Biggest gap this week"}</span>
              <span className="text-[13px] text-muted">{kickShort(featured.kick)} ET</span>
            </div>
            <div className="grid grid-cols-[1fr_auto_1fr] items-center gap-3">
              <div className="flex flex-col gap-2">
                <TeamBadge team={featured.away} size={56} />
                <div className="text-[18px] font-bold leading-tight">{featured.away.school}</div>
                <div className="text-[13px] text-muted">Away · {featured.awayConf}</div>
              </div>
              <div className="display text-[22px] text-muted">{featured.neutral ? "vs" : "@"}</div>
              <div className="flex flex-col items-end gap-2 text-right">
                <TeamBadge team={featured.home} size={56} />
                <div className="text-[18px] font-bold leading-tight">{featured.home.school}</div>
                <div className="text-[13px] text-muted">Home · {featured.homeConf}</div>
              </div>
            </div>
            <div className="grid grid-cols-3 gap-2.5">
              <div className="rounded-xl bg-surface-2 p-2.5 sm:p-3.5"><div className="text-[12px] font-semibold text-muted">Vegas</div><div className="mono mt-1 text-[15px] font-semibold sm:text-[18px]">{favLine(featured.home, featured.away, featured.spread)}</div></div>
              <div className="rounded-xl bg-surface-2 p-2.5 sm:p-3.5"><div className="text-[12px] font-semibold text-muted">Our model</div><div className="mono mt-1 text-[15px] font-semibold sm:text-[18px]">{favLine(featured.home, featured.away, featured.modelSpread)}</div></div>
              <div className="rounded-xl bg-accent-tint p-2.5 sm:p-3.5"><div className="text-[12px] font-semibold text-accent">Gap</div><div className="mono mt-1 text-[15px] font-semibold sm:text-[18px] text-accent">{Math.abs(featured.edge ?? 0).toFixed(1)} pts</div></div>
            </div>
            <div className="flex flex-wrap items-center justify-between gap-3 border-t border-line-strong pt-4">
              <div className="flex items-center gap-2"><span className="text-[13px] text-muted">Model pick</span><b>{featured.pick}</b><TierTag tier={featured.tier} /></div>
              <span className="text-[14px] font-bold text-accent">Why →</span>
            </div>
          </Link>
        )}
      </section>

      <section aria-labelledby="rec-h" className="flex flex-col gap-4">
        <SectionTitle id="rec-h" right={<Link href="/model/" className="font-semibold">Full track record →</Link>}>Track record</SectionTitle>
        <div className="grid grid-cols-[repeat(auto-fit,minmax(220px,1fr))] gap-3">
          {fav && <StatCard label="Watchlist · past-season testing" value={recordText(fav.wins, fav.losses)} sub={`${fav.win_pct}% · ${fav.units > 0 ? "+" : ""}${fav.units} units`} tone={fav.win_pct >= tr.breakEven ? "good" : "bad"} />}
          <StatCard label={`Watchlist · ${tr.season}`} value={sw.w + sw.l ? recordText(sw.w, sw.l, sw.p) : "—"} sub={sw.pct != null ? `${sw.pct.toFixed(1)}% · need ${tr.breakEven}% to profit` : `need ${tr.breakEven}% to profit`} tone={(sw.pct ?? 0) >= tr.breakEven ? "good" : "bad"} />
          <StatCard label={`Every 3+ pt gap · ${tr.season}`} value={recordText(all.w, all.l, all.p)} sub={`${all.pct?.toFixed(1)}% · ${all.units >= 0 ? "+" : ""}${all.units.toFixed(1)} units`} tone={(all.pct ?? 0) >= tr.breakEven ? "good" : "bad"} />
          {tr.accuracy && <StatCard label="Average miss on final margin" value={`${tr.accuracy.Model.margin_MAE.toFixed(1)} pts`} sub={`Vegas: ${tr.accuracy.Vegas.margin_MAE.toFixed(1)} pts`} />}
        </div>
      </section>

      {wk && (
        <section aria-labelledby="edges-h" className="flex flex-col gap-4">
          <SectionTitle id="edges-h">Top gaps · Week {wk.week}</SectionTitle>
          <GamesTable games={wk.games} compact />
          <Link href={`/picks/${wk.week}/`} className="self-start text-[14px] font-bold">All {edges.length} model edges, with the reasoning for each →</Link>
        </section>
      )}

      <section aria-labelledby="ex-h" className="flex flex-col gap-4">
        <SectionTitle id="ex-h">Explore</SectionTitle>
        <div className="grid grid-cols-[repeat(auto-fit,minmax(250px,1fr))] gap-3.5">
          {TOOLS.map((t) => (
            <Link key={t.href} href={t.href} className="card flex flex-col gap-2.5 p-5 text-ink hover:border-accent hover:text-ink">
              <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="#2FD27A" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{t.icon}</svg>
              <div className="text-[18px] font-bold">{t.title}</div>
              <div className="text-[14px] leading-normal text-soft">{t.desc}</div>
            </Link>
          ))}
        </div>
      </section>
    </>
  );
}
