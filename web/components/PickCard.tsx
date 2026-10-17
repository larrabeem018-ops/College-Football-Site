import Link from "next/link";
import type { Game, TrackRecord } from "@/lib/types";
import { favLine, kickLong, TIER_LONG } from "@/lib/format";
import TeamBadge from "./TeamBadge";
import { Bold, ResultTag, TierTag } from "./ui";

function qbText(q: Game["homeQb"]) {
  if (!q) return "unknown";
  return q.starts != null ? `${q.name} (${q.starts} start${q.starts === 1 ? "" : "s"})` : q.name;
}
const wl = (v?: [number, number]) => (v ? `${v[0]}–${v[1]} (${Math.round((100 * v[0]) / Math.max(v[0] + v[1], 1))}%)` : "—");

/** The Sharp Bets pick card: category, pick, lines, QBs, why / what could go wrong. */
export default function PickCard({ g, tr, muted = false }: { g: Game; tr: TrackRecord; muted?: boolean }) {
  const th = tr.tiers.find((t) => t.tier === g.tier);
  return (
    <article className="card flex flex-col gap-4 p-5">
      <div className="flex flex-wrap items-center gap-2">
        <TierTag tier={g.tier} />
        <ResultTag result={g.result} />
        {th && (
          <span className="text-[12px] text-muted">
            Past record: <b className="text-soft">{th.wins}–{th.losses}</b> ({th.win_pct}%) · {Object.entries(th.by_season).map(([y, v]) => `${y}: ${v[0]}–${v[1]}`).join(" · ")}
          </span>
        )}
      </div>
      <Link href={`/games/${g.id}/`} className="flex items-center gap-3 text-ink hover:text-accent">
        <TeamBadge team={g.away} size={40} />
        <span className="text-[19px] font-bold leading-tight">{g.away.school} <span className="font-medium text-muted">{g.neutral ? "vs" : "@"}</span> {g.home.school}</span>
        <TeamBadge team={g.home} size={40} />
      </Link>
      <div className="-mt-2 text-[13px] text-muted">{kickLong(g.kick)}</div>
      <div>
        <div className="eyebrow text-muted">{muted ? "Model lean" : "The pick"}</div>
        <div className={`display mt-1 text-[30px] leading-none ${muted ? "text-amber" : "text-accent"}`}>{g.pick}</div>
      </div>
      <dl className="grid grid-cols-3 gap-2">
        <div className="rounded-xl bg-surface-2 p-3"><dt className="text-[12px] font-semibold text-muted">Vegas</dt><dd className="mono mt-1 font-semibold">{favLine(g.home, g.away, g.spread)}</dd></div>
        <div className="rounded-xl bg-surface-2 p-3"><dt className="text-[12px] font-semibold text-muted">Model</dt><dd className="mono mt-1 font-semibold">{favLine(g.home, g.away, g.modelSpread)}</dd></div>
        <div className="rounded-xl bg-surface-2 p-3"><dt className="text-[12px] font-semibold text-muted">Model score</dt><dd className="mono mt-1 font-semibold">{g.away.abbr} {Math.round(g.predAway ?? 0)} · {g.home.abbr} {Math.round(g.predHome ?? 0)}</dd></div>
      </dl>
      {(g.homeQb || g.awayQb) && (
        <div className="rounded-xl border border-line bg-surface-2 p-3 text-[13px] leading-relaxed text-soft">
          <b className="text-ink">Started last game:</b> {g.away.school}: {qbText(g.awayQb)} · {g.home.school}: {qbText(g.homeQb)}
          {tr.qbCheck && g.tier && (
            <div className="mt-1 text-[12px] text-muted">
              If either QB is out, be careful: {TIER_LONG[g.tier].toLowerCase()} picks went {wl(tr.qbCheck.changed[g.tier])} in testing when a team&apos;s previous starter sat, vs. {wl(tr.qbCheck.same[g.tier])} otherwise.
            </div>
          )}
        </div>
      )}
      {g.why.length > 0 && (
        <div>
          <div className="mb-2 text-[14px] font-bold">Why the model likes it</div>
          <ul className="flex list-disc flex-col gap-1.5 pl-5 text-[14px] leading-relaxed text-body marker:text-accent">
            {g.why.map((w, i) => <li key={i}><Bold text={w} /></li>)}
          </ul>
        </div>
      )}
      {g.watch.length > 0 && (
        <details open={muted} className="group rounded-xl border border-amber-line bg-amber-tint p-3">
          <summary className="cursor-pointer text-[14px] font-bold text-amber">What could go wrong</summary>
          <ul className="mt-2 flex list-disc flex-col gap-1.5 pl-5 text-[14px] leading-relaxed text-amber-text">
            {g.watch.map((w, i) => <li key={i}><Bold text={w} /></li>)}
          </ul>
        </details>
      )}
    </article>
  );
}
