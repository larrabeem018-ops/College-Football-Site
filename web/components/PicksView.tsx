import Link from "next/link";
import { getMeta, getTrackRecord, getWeek } from "@/lib/data";
import GamesTable from "./GamesTable";
import PickCard from "./PickCard";
import { Callout, PageHeader, SectionTitle } from "./ui";

const wl = (v?: [number, number]) => (v ? `${v[0]}–${v[1]} (${Math.round((100 * v[0]) / Math.max(v[0] + v[1], 1))}%)` : "—");

export function WeekSwitcher({ week, base }: { week: number; base: string }) {
  const weeks = getMeta().weeks.map((w) => w.week);
  const i = weeks.indexOf(week);
  const prev = weeks[i - 1], next = weeks[i + 1];
  const btn = "flex h-11 w-11 items-center justify-center rounded-lg text-soft hover:bg-raised hover:text-ink";
  return (
    <nav aria-label="Week" className="flex items-center gap-1 rounded-xl border border-line-strong bg-surface p-1">
      {prev != null ? <Link className={btn} href={`${base}${prev}/`} aria-label={`Week ${prev}`}>‹</Link> : <span className={`${btn} opacity-30`} aria-hidden="true">‹</span>}
      <span className="px-2 font-bold">Week {week}</span>
      {next != null ? <Link className={btn} href={`${base}${next}/`} aria-label={`Week ${next}`}>›</Link> : <span className={`${btn} opacity-30`} aria-hidden="true">›</span>}
    </nav>
  );
}

export default function PicksView({ week }: { week: number }) {
  const wk = getWeek(week);
  const tr = getTrackRecord();
  const tier = (t: string) => tr.tiers.find((x) => x.tier === t);
  const byGap = (a: { edge: number | null }, b: { edge: number | null }) => Math.abs(b.edge ?? 0) - Math.abs(a.edge ?? 0);
  const watch = wk.games.filter((g) => g.tier === "fav_value").sort(byGap);
  const big = wk.games.filter((g) => g.tier === "big_gap").sort(byGap);
  const bg = tier("big_gap"), ln = tier("lean"), ps = tier("pass");
  return (
    <>
      <PageHeader eyebrow="Model vs. the line" title={`Week ${week} picks`} crumbs={[{ href: "/", label: "This Week" }, { href: "/picks/", label: "Picks" }]}
        right={<WeekSwitcher week={week} base="/picks/" />}>
        Each week our score model sets its own point spread for every game. When it disagrees with Vegas in the one way that has held up in testing, the game makes the watchlist. Every pick is saved before kickoff and graded afterward.
      </PageHeader>

      <Callout title="Read this first">
        Across all games, Vegas is more accurate than this model. The watchlist is the one kind of disagreement that has beaten the {tr.breakEven}% break-even rate in testing, and only by a few points. Treat these picks as leads to research (injuries, weather, QB news), not locks.
        {tr.qbCheck && (
          <><br /><br /><b className="text-amber">Check the quarterbacks.</b> The model rates teams on games their usual QB played, so when he sits it overrates them. In testing, big disagreements went <b>{wl(tr.qbCheck.changed.big_gap)}</b> when either team&apos;s previous starter sat, against <b>{wl(tr.qbCheck.same.big_gap)}</b> when both started again.</>
        )}
      </Callout>

      <section aria-labelledby="wl-h" className="flex flex-col gap-4">
        <SectionTitle id="wl-h" right="A 3.5–14 point favorite the model thinks should be favored by 3+ more">Week {week} watchlist</SectionTitle>
        {watch.length ? (
          <div className="grid grid-cols-[repeat(auto-fit,minmax(min(100%,460px),1fr))] gap-4">{watch.map((g) => <PickCard key={g.id} g={g} tr={tr} />)}</div>
        ) : (
          <Callout tone="plain">No watchlist games this week. The model and Vegas mostly agree on the favorites.</Callout>
        )}
      </section>

      {big.length > 0 && (
        <section aria-labelledby="bg-h" className="flex flex-col gap-4">
          <SectionTitle id="bg-h">Big disagreements: check the news</SectionTitle>
          <p className="m-0 max-w-[820px] text-[14px] leading-relaxed text-soft">
            The model&apos;s line is 10+ points from Vegas.{bg && ` These have gone ${bg.wins}–${bg.losses} (${bg.win_pct}%) in testing, but`} a gap this big usually means Vegas knows something the box scores don&apos;t, so they&apos;re not recommended as picks.
          </p>
          <div className="grid grid-cols-[repeat(auto-fit,minmax(min(100%,460px),1fr))] gap-4">{big.map((g) => <PickCard key={g.id} g={g} tr={tr} muted />)}</div>
        </section>
      )}

      <section aria-labelledby="all-h" className="flex flex-col gap-4">
        <SectionTitle id="all-h">All games this week</SectionTitle>
        {ln && ps && (
          <p className="m-0 max-w-[820px] text-[14px] leading-relaxed text-soft">
            Smaller disagreements (3–10 points) have gone {ln.wins}–{ln.losses} ({ln.win_pct}%) in testing, and games where the model roughly agrees with Vegas {ps.wins}–{ps.losses} ({ps.win_pct}%). Both are below break-even, so they&apos;re shown for reference. Click any game for the model&apos;s reasoning.
          </p>
        )}
        <GamesTable games={wk.games} />
      </section>
    </>
  );
}
