import Link from "next/link";
import { allGameIds, getGame, getTrackRecord } from "@/lib/data";
import { fmt, gameTitle, kickLong, TIER_LONG, favLine, teamHref } from "@/lib/format";
import type { GameDetail, SeasonStats, TeamRef } from "@/lib/types";
import TeamBadge from "@/components/TeamBadge";
import { Bold, Callout, ResultTag, SectionTitle, TierTag } from "@/components/ui";

export const dynamicParams = false;
export function generateStaticParams() {
  return allGameIds().map((id) => ({ id }));
}
export async function generateMetadata({ params }: { params: Promise<{ id: string }> }) {
  const g = getGame((await params).id);
  return { title: `${gameTitle(g)} · Week ${g.week}`, description: g.pick ? `Model lean: ${g.pick}` : undefined };
}

const STAT_ROWS: [string, keyof NonNullable<SeasonStats>, "higher" | "lower", (v: number) => string][] = [
  ["Offensive yards / game", "off_yards_pg", "higher", (v) => v.toFixed(0)],
  ["Points / game", "off_points_pg", "higher", (v) => v.toFixed(1)],
  ["3rd down conversion % (off.)", "off_third_down_pct", "higher", (v) => `${v.toFixed(1)}%`],
  ["Yards allowed / game", "def_yards_pg", "lower", (v) => v.toFixed(0)],
  ["Points allowed / game", "def_points_pg", "lower", (v) => v.toFixed(1)],
  ["3rd down allowed % (def.)", "def_third_down_pct", "lower", (v) => `${v.toFixed(1)}%`],
  ["Turnovers forced / game", "turnovers_forced_pg", "higher", (v) => v.toFixed(2)],
  ["Turnover margin / game", "turnover_margin_pg", "higher", (v) => `${v > 0 ? "+" : ""}${v.toFixed(2)}`],
];

function TeamName({ t, align = "left" }: { t: TeamRef; align?: "left" | "right" }) {
  const href = teamHref(t);
  const name = <span className="display text-[28px] leading-none sm:text-[36px]">{t.school}</span>;
  return (
    <div className={`flex min-w-0 items-center gap-4 ${align === "right" ? "flex-row-reverse text-right" : ""}`}>
      <TeamBadge team={t} size={72} />
      {href ? <Link href={href} className="text-ink hover:text-accent">{name}</Link> : name}
    </div>
  );
}

/** Where Vegas, the opening line and the model sit on one "home margin" axis. */
function GapLine({ g }: { g: GameDetail }) {
  if (g.spread == null || g.modelSpread == null) return null;
  const pts = [
    { label: "Model", v: -g.modelSpread, color: "var(--color-accent)", big: true },
    ...(g.spreadOpen != null && g.spreadOpen !== g.spread ? [{ label: "Open", v: -g.spreadOpen, color: "var(--color-muted)", big: false }] : []),
    { label: "Vegas", v: -g.spread, color: "var(--color-amber)", big: true },
  ];
  const lo = Math.min(0, ...pts.map((p) => p.v)) - 4, hi = Math.max(0, ...pts.map((p) => p.v)) + 4;
  const x = (v: number) => ((v - lo) / (hi - lo)) * 100;
  const a = x(-g.modelSpread), b = x(-g.spread);
  return (
    <div role="img" aria-label={`Model has ${favLine(g.home, g.away, g.modelSpread, false)}; Vegas has ${favLine(g.home, g.away, g.spread, false)}`} className="py-2">
      <div className="relative h-16">
        <div className="absolute inset-x-0 top-[38px] h-1 rounded bg-chip" />
        <div className="absolute top-[34px] h-3 rounded-md border border-accent bg-accent-tint" style={{ left: `${Math.min(a, b)}%`, width: `${Math.abs(a - b)}%` }} />
        <div className="absolute top-[30px] h-5 w-px bg-line-strong" style={{ left: `${x(0)}%` }} />
        {pts.map((p) => (
          <div key={p.label} className="absolute top-0 flex -translate-x-1/2 flex-col items-center gap-1" style={{ left: `${x(p.v)}%` }}>
            <span className="text-[12px] font-bold" style={{ color: p.color }}>{p.label}</span>
            <span className="rounded-full border-[3px] border-surface" style={{ width: p.big ? 16 : 13, height: p.big ? 16 : 13, background: p.big ? p.color : "var(--color-surface)", boxShadow: p.big ? undefined : `inset 0 0 0 2px ${p.color}` }} />
          </div>
        ))}
      </div>
      <div className="mono mt-1 flex justify-between text-[12px] text-muted">
        <span>← {g.away.abbr} wins by more</span><span>even</span><span>{g.home.abbr} wins by more →</span>
      </div>
    </div>
  );
}

export default async function GamePage({ params }: { params: Promise<{ id: string }> }) {
  const g = getGame((await params).id);
  const tr = getTrackRecord();
  const th = tr.tiers.find((t) => t.tier === g.tier);
  const final = g.homeScore != null;
  const hasEdge = g.tier && g.tier !== "pass";
  const qb = (q: GameDetail["homeQb"]) => (q ? `${q.name}${q.starts != null ? ` (${q.starts} start${q.starts === 1 ? "" : "s"})` : ""}` : "Unknown");

  return (
    <>
      <nav aria-label="Breadcrumb" className="-mb-6 text-[13px] text-muted">
        <Link href="/" className="text-muted hover:text-ink">This Week</Link> / <Link href={`/matchups/${g.week}/`} className="text-muted hover:text-ink">Week {g.week}</Link> / {g.away.school} {g.neutral ? "vs" : "@"} {g.home.school}
      </nav>

      <section aria-label="Game" className="card overflow-hidden rounded-[20px]">
        <div aria-hidden="true" className="flex h-1.5"><div className="flex-1" style={{ background: g.away.color }} /><div className="flex-1" style={{ background: g.home.color }} /></div>
        <div className="flex flex-col gap-6 p-6 sm:p-7">
          <div className="flex flex-wrap justify-between gap-2 text-[13px] font-semibold text-muted">
            <span>{kickLong(g.kick)}{g.venue ? ` · ${g.venue}` : ""}{g.confGame ? " · Conference game" : ""}{g.neutral ? " · Neutral site" : ""}</span>
            {hasEdge && <span className="text-accent">Model lean: {g.pick}</span>}
          </div>
          <div className="grid grid-cols-1 items-center gap-6 md:grid-cols-[1fr_auto_1fr]">
            <TeamName t={g.away} />
            <div className="flex flex-col items-center gap-1.5">
              <div className="eyebrow text-muted">{final ? "Final" : "Model projection"}</div>
              <div className="mono whitespace-nowrap text-[40px] font-semibold">
                {final ? `${g.awayScore} – ${g.homeScore}` : `${fmt(g.predAway)} – ${fmt(g.predHome)}`}
              </div>
              <div className="text-[13px] text-muted">
                Vegas {favLine(g.home, g.away, g.spread)}{g.overUnder != null ? ` · O/U ${g.overUnder}` : ""}
              </div>
              {final && g.result && <div className="flex items-center gap-2 text-[13px] text-muted">Model pick: <ResultTag result={g.result} /></div>}
            </div>
            <TeamName t={g.home} align="right" />
          </div>
        </div>
      </section>

      <div className="flex flex-wrap items-start gap-6">
        <div className="flex min-w-0 flex-[999_1_600px] flex-col gap-6">
          <section aria-labelledby="gap-h" className="card flex flex-col gap-5 p-6">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <h2 id="gap-h" className="display m-0 text-[26px]">Model vs. Vegas</h2>
              <TierTag tier={g.tier} />
            </div>
            <GapLine g={g} />
            <dl className="grid grid-cols-[repeat(auto-fit,minmax(150px,1fr))] gap-2.5">
              <div className="rounded-xl bg-surface-2 p-3.5"><dt className="text-[12px] font-semibold text-muted">Model spread</dt><dd className="mono mt-1 text-[19px] font-semibold">{favLine(g.home, g.away, g.modelSpread)}</dd></div>
              <div className="rounded-xl bg-surface-2 p-3.5"><dt className="text-[12px] font-semibold text-muted">Vegas{g.spreadOpen != null && g.spreadOpen !== g.spread ? ` (opened ${favLine(g.home, g.away, g.spreadOpen)})` : ""}</dt><dd className="mono mt-1 text-[19px] font-semibold">{favLine(g.home, g.away, g.spread)}</dd></div>
              <div className="rounded-xl bg-accent-tint p-3.5"><dt className="text-[12px] font-semibold text-accent">Gap</dt><dd className="mono mt-1 text-[19px] font-semibold text-accent">{fmt(Math.abs(g.edge ?? 0))} pts</dd></div>
              <div className="rounded-xl bg-surface-2 p-3.5"><dt className="text-[12px] font-semibold text-muted">Total · model / Vegas</dt><dd className="mono mt-1 text-[19px] font-semibold">{fmt(g.modelTotal)} / {fmt(g.overUnder)}</dd></div>
            </dl>
            {th && g.tier && (
              <p className="m-0 text-[14px] leading-relaxed text-soft">
                <b className="text-ink">{TIER_LONG[g.tier]}:</b> {th.description} This kind of pick has gone {th.wins}–{th.losses} ({th.win_pct}%) in testing{g.tier === "fav_value" ? ", the one category above break-even." : g.tier === "big_gap" ? ". A gap this big usually means Vegas knows something the box score doesn't." : ", below the 52.4% break-even, so treat it as reference only."}
              </p>
            )}
          </section>

          {g.why.length > 0 && (
            <section aria-labelledby="why-h" className="card flex flex-col gap-3.5 p-6">
              <h2 id="why-h" className="display m-0 text-[26px]">{hasEdge ? `Why the model likes ${g.pickSide === "home" ? g.home.school : g.away.school}` : "What the model sees"}</h2>
              <ul className="flex list-none flex-col gap-3 p-0">
                {g.why.map((w, i) => (
                  <li key={i} className="flex gap-3 leading-relaxed text-body">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#2FD27A" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" className="mt-1 shrink-0"><polyline points="5,12 10,17 19,7" /></svg>
                    <span><Bold text={w} /></span>
                  </li>
                ))}
              </ul>
            </section>
          )}
          {g.watch.length > 0 && (
            <section aria-labelledby="risk-h" className="flex flex-col gap-3.5 rounded-2xl border border-amber-line bg-amber-tint p-6">
              <h2 id="risk-h" className="display m-0 text-[26px] text-amber">What could go wrong</h2>
              <ul className="flex list-none flex-col gap-3 p-0">
                {g.watch.map((w, i) => (
                  <li key={i} className="flex gap-3 leading-relaxed text-amber-text">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#F5B83D" strokeWidth="2.2" strokeLinecap="round" aria-hidden="true" className="mt-1 shrink-0"><path d="M12 4l9 16H3z" /><line x1="12" y1="10" x2="12" y2="14" /><line x1="12" y1="17" x2="12" y2="17.5" /></svg>
                    <span><Bold text={w} /></span>
                  </li>
                ))}
              </ul>
            </section>
          )}

          <section aria-labelledby="stats-h" className="card flex flex-col gap-3 p-6">
            <SectionTitle id="stats-h">Stat for stat</SectionTitle>
            {g.homeStats || g.awayStats ? (
              <>
                <div className="text-[12px] text-muted">
                  {[g.awayStats && `${g.away.school}: ${g.awayStats.season} season, ${g.awayStats.games} games`, g.homeStats && `${g.home.school}: ${g.homeStats.season} season, ${g.homeStats.games} games`].filter(Boolean).join(" · ")}
                </div>
                <div className="overflow-x-auto">
                  <table className="tbl">
                    <thead><tr><th className="w-[30%] text-center">{g.away.abbr}</th><th className="text-center"> </th><th className="w-[30%] text-center">{g.home.abbr}</th></tr></thead>
                    <tbody>
                      {STAT_ROWS.map(([label, key, better, f]) => {
                        const av = g.awayStats?.[key] as number | undefined, hv = g.homeStats?.[key] as number | undefined;
                        const aBetter = av != null && hv != null && av !== hv && (better === "higher" ? av > hv : av < hv);
                        const hBetter = av != null && hv != null && av !== hv && !aBetter;
                        return (
                          <tr key={key}>
                            <td className={`mono text-center ${aBetter ? "font-bold text-accent" : ""}`}>{av != null ? f(av) : "—"}</td>
                            <td className="text-center text-[13px] text-muted">{label}</td>
                            <td className={`mono text-center ${hBetter ? "font-bold text-accent" : ""}`}>{hv != null ? f(hv) : "—"}</td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </>
            ) : <p className="text-muted">No season stats for either team yet.</p>}
          </section>
        </div>

        <aside aria-label="More on this game" className="flex min-w-0 flex-[1_1_300px] flex-col gap-4">
          {g.mlValue && (
            <div className="flex flex-col gap-2 rounded-2xl border border-[#1E4A30] bg-accent-tint p-5">
              <div className="eyebrow text-accent">Moneyline value</div>
              <div className="display text-[26px] leading-none">{g.mlValue.team.school} {g.mlValue.ml > 0 ? `+${g.mlValue.ml}` : g.mlValue.ml}</div>
              <p className="m-0 text-[14px] leading-relaxed text-body">
                The market prices {g.mlValue.team.school} to win <b>{Math.round(g.mlValue.pMkt * 100)}%</b> of the time; the market-anchored blend says <b>{Math.round(g.mlValue.pBlend * 100)}%</b> (raw model {Math.round(g.mlValue.pModel * 100)}%). At {g.mlValue.ml > 0 ? `+${g.mlValue.ml}` : g.mlValue.ml} that&apos;s about <b>+{(g.mlValue.ev * 100).toFixed(1)}%</b> expected value per bet.
              </p>
              <Link href={`/picks/${g.week}/#ml-h`} className="text-[13px] font-bold">All Week {g.week} moneyline value →</Link>
            </div>
          )}
          <div className="card flex flex-col gap-3 p-5">
            <div className="eyebrow text-muted">Returning production</div>
            {[{ t: g.away, r: g.awayReturning }, { t: g.home, r: g.homeReturning }].map(({ t, r }) => (
              <div key={t.school} className="flex flex-col gap-1.5">
                <div className="flex items-center justify-between gap-2"><span className="flex items-center gap-2 font-bold"><TeamBadge team={t} size={24} ring={false} />{t.school}</span><span className="mono font-semibold">{r?.pct != null ? `${Math.round(r.pct)}%` : "—"}</span></div>
                <div className="h-2 overflow-hidden rounded bg-chip"><div className="h-full rounded bg-accent" style={{ width: `${r?.pct ?? 0}%` }} /></div>
                {r && <div className="text-[12px] text-muted">{r.returning_players} of {r.total_players} players from last season&apos;s roster are back</div>}
              </div>
            ))}
          </div>
          <div className="card flex flex-col gap-2 p-5 text-[14px]">
            <div className="eyebrow text-muted">Started last game</div>
            <div className="flex justify-between gap-3"><span className="text-muted">{g.away.abbr}</span><span className="text-right font-semibold">{qb(g.awayQb)}</span></div>
            <div className="flex justify-between gap-3"><span className="text-muted">{g.home.abbr}</span><span className="text-right font-semibold">{qb(g.homeQb)}</span></div>
            <p className="m-0 mt-1 text-[12px] leading-normal text-muted">If either one is out, the model&apos;s line is less reliable. Check the injury news.</p>
          </div>
          <div className="card flex flex-col p-5">
            <div className="eyebrow mb-1 text-muted">Go deeper</div>
            {[g.away, g.home].filter((t) => t.slug).map((t) => (
              <Link key={t.school} href={`/teams/${t.slug}/`} className="flex min-h-11 items-center justify-between border-b border-line font-semibold text-ink hover:text-accent">{t.school} team page <span className="text-accent">→</span></Link>
            ))}
            {g.away.slug && g.home.slug && (
              <Link href={`/compare/?a=${g.away.slug}&b=${g.home.slug}`} className="flex min-h-11 items-center justify-between border-b border-line font-semibold text-ink hover:text-accent">Compare rosters <span className="text-accent">→</span></Link>
            )}
            <Link href={`/picks/${g.week}/`} className="flex min-h-11 items-center justify-between font-semibold text-ink hover:text-accent">All Week {g.week} picks <span className="text-accent">→</span></Link>
          </div>
          <Callout tone="plain" title="What the model doesn't know">Injuries, weather, suspensions, motivation, coaching changes — anything that isn&apos;t in a box score.</Callout>
        </aside>
      </div>
    </>
  );
}
