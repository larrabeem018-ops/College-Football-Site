import PickLog, { UnitsChart } from "@/components/PickLog";
import { Callout, PageHeader, SectionTitle, StatCard } from "@/components/ui";
import { getTrackRecord } from "@/lib/data";
import { recordText, TIER_LONG } from "@/lib/format";
import type { Rec } from "@/lib/types";

export const metadata = { title: "Model Record" };
const wl = (v?: [number, number]) => (v ? `${v[0]}–${v[1]} (${Math.round((100 * v[0]) / Math.max(v[0] + v[1], 1))}%)` : "—");

export default function Page() {
  const tr = getTrackRecord();
  const be = tr.breakEven;
  const rc = (r: Rec, label: string) => (
    <StatCard label={label} value={r.w + r.l ? recordText(r.w, r.l, r.p) : "None yet"}
      sub={r.pct != null ? `${r.pct.toFixed(1)}% · ${r.units >= 0 ? "+" : ""}${r.units.toFixed(1)} units` : "Graded after this week's games"}
      tone={r.pct == null ? "muted" : r.pct >= be ? "good" : "bad"} />
  );
  return (
    <>
      <PageHeader eyebrow="Self-grading" title="Model record">Every pick is saved before kickoff and graded against the line it was made at. Break-even at standard −110 odds is {be}%.</PageHeader>

      <section className="flex flex-col gap-4">
        <SectionTitle>{tr.season} season</SectionTitle>
        <div className="grid grid-cols-[repeat(auto-fit,minmax(220px,1fr))] gap-3">
          {rc(tr.season_records.watchlist, "Watchlist")}
          {rc(tr.season_records.big_gap, "Big disagreements")}
          {rc(tr.season_records.lean, "Leans (3–10 pt gap)")}
          {rc(tr.season_records.watchlist_live, "Watchlist, live picks only")}
        </div>
        <div className="card p-4">
          <div className="px-2 pb-2 text-[14px] font-bold">Running profit in units (1 unit per pick at −110)</div>
          <UnitsChart series={tr.series} />
        </div>
      </section>

      <section className="flex flex-col gap-4">
        <SectionTitle>Pick log</SectionTitle>
        <PickLog log={tr.log} />
      </section>

      <section className="flex flex-col gap-4">
        <SectionTitle>How each category has done in testing</SectionTitle>
        <p className="m-0 text-[14px] text-soft">Each season&apos;s picks come from a model fit on the <em>other</em> season, then graded against the closing line.</p>
        <div className="card overflow-x-auto">
          <table className="tbl min-w-[860px]">
            <thead><tr><th>Category</th><th>What it means</th><th className="text-right">Record</th><th className="text-right">Win %</th><th className="text-right">Units</th><th className="text-right">2025</th><th className="text-right">2026</th><th>Shown as a pick?</th></tr></thead>
            <tbody>{tr.tiers.map((t) => (
              <tr key={t.tier}><td className="font-semibold">{t.label}</td><td className="max-w-[320px] text-[13px] text-soft">{t.description}</td><td className="mono text-right">{t.wins}–{t.losses}</td>
                <td className={`mono text-right font-semibold ${t.win_pct >= be ? "text-accent" : "text-loss"}`}>{t.win_pct}%</td><td className="mono text-right">{t.units > 0 ? "+" : ""}{t.units}</td>
                <td className="mono text-right">{t.by_season["2025"] ? `${t.by_season["2025"][0]}–${t.by_season["2025"][1]}` : "—"}</td><td className="mono text-right">{t.by_season["2026"] ? `${t.by_season["2026"][0]}–${t.by_season["2026"][1]}` : "—"}</td>
                <td className="text-[13px] text-soft">{t.tier === "fav_value" ? "Yes (watchlist)" : t.tier === "big_gap" ? "Flagged, not picked" : "No"}</td></tr>
            ))}</tbody>
          </table>
        </div>
        {tr.accuracy && <p className="m-0 text-[13px] text-muted">Across {tr.accuracy.Model.games.toLocaleString()} games the model misses the final margin by {tr.accuracy.Model.margin_MAE} points on average (Vegas: {tr.accuracy.Vegas.margin_MAE}) and picks the winner {tr.accuracy.Model.winner_pct}% of the time (Vegas: {tr.accuracy.Vegas.winner_pct}%).</p>}
      </section>

      {tr.qbCheck && (
        <section className="flex flex-col gap-4">
          <SectionTitle>Check the quarterbacks</SectionTitle>
          <p className="m-0 max-w-[820px] text-[14px] leading-relaxed text-soft">The model rates each team on the games it has played, almost all with its usual starting QB. When that QB sits, the model doesn&apos;t know and overrates the team. Here&apos;s how its picks did in testing when either team&apos;s previous starter didn&apos;t throw a pass, compared with games where both played.</p>
          <div className="card overflow-x-auto"><table className="tbl min-w-[520px]"><thead><tr><th>Category</th><th className="text-right">Same QBs</th><th className="text-right">A previous starter sat</th></tr></thead>
            <tbody>{["fav_value", "big_gap", "lean", "pass", "all_3plus"].map((t) => (
              <tr key={t}><td className="font-semibold">{TIER_LONG[t] ?? "All picks (3+ pt gap)"}</td><td className="mono text-right">{wl(tr.qbCheck!.same[t])}</td><td className="mono text-right">{wl(tr.qbCheck!.changed[t])}</td></tr>
            ))}</tbody></table></div>
          <p className="m-0 text-[12px] text-muted">{tr.qbCheck.same.games?.toLocaleString()} games with the same starters, {tr.qbCheck.changed.games?.toLocaleString()} with a change. Small samples (under ~100 picks) can swing a lot by chance.</p>
        </section>
      )}

      <section className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <div className="card flex flex-col gap-3 p-6">
          <h2 className="display m-0 text-[26px]">How the model sets its line</h2>
          <ol className="m-0 flex flex-col gap-3 pl-5 text-[14px] leading-relaxed text-body">
            <li><b className="text-ink">Rate every team, adjusted for schedule.</b> Every game so far goes into one regression that estimates how many points each offense scores and each defense allows compared with average, after accounting for who they played. Last season counts too, at a weight that fades as the season goes on.</li>
            <li><b className="text-ink">Weight recent form.</b> A second version counts the last 3 weeks three times as heavily, which catches teams that are improving or slipping.</li>
            <li><b className="text-ink">Rate play-by-play efficiency.</b> Every offense and defense is also rated on success rate and EPA per play, with garbage time removed and adjusted for schedule.</li>
            <li><b className="text-ink">Predict each team&apos;s score.</b> A regression turns those ratings, plus yards and home field, into a predicted score. Home field is worth much less in conference games (about 1 pt) than non-conference games.</li>
            <li><b className="text-ink">Compare with Vegas.</b> The gap between the model&apos;s spread and the Vegas spread puts each game in a category.</li>
          </ol>
        </div>
        <div className="card flex flex-col gap-3 p-6">
          <h2 className="display m-0 text-[26px]">What we tested that didn&apos;t help</h2>
          <ul className="m-0 flex list-disc flex-col gap-2 pl-5 text-[14px] leading-relaxed text-body">
            <li>Turnover margin, 3rd-down %, travel, time zones, rest days, bye weeks, altitude.</li>
            <li>A neural network: no better at picking winners, worse at win probabilities.</li>
            <li>Betting against a team with a new starting QB: looked like a 60% edge, but was a data leak. Measured cleanly it&apos;s a coin flip.</li>
            <li>About 40 more box-score stats (havoc, field position, explosive plays, line yards and more).</li>
            <li>Returning production and roster talent: better early-season scores, worse picks. Vegas already prices it in.</li>
            <li>Pace, for over/unders. The model&apos;s totals haven&apos;t beaten the posted total, so they&apos;re for reference only.</li>
          </ul>
        </div>
      </section>
      <Callout tone="plain" title="What the model can't see">Injuries (beyond what already shows up in results), weather, suspensions, motivation, coaching changes, and anything else that isn&apos;t in a box score. When the model disagrees with Vegas by 10+ points, one of these is often the reason.</Callout>
    </>
  );
}
