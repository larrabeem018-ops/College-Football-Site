import Link from "next/link";
import { getDirectory, getTeam, getTeams } from "@/lib/data";
import type { TeamRef } from "@/lib/types";
import TeamBadge from "@/components/TeamBadge";
import TeamView from "@/components/TeamView";

export const dynamicParams = false;
export function generateStaticParams() {
  return getDirectory().map((t) => ({ slug: t.slug! }));
}
export async function generateMetadata({ params }: { params: Promise<{ slug: string }> }) {
  const d = getTeam((await params).slug);
  return { title: `${d.school} ${d.mascot ?? ""}`.trim(), description: `${d.school}: schedule, roster turnover, transfers and ATS record.` };
}

export default async function TeamPage({ params }: { params: Promise<{ slug: string }> }) {
  const doc = getTeam((await params).slug);
  const all = getTeams();
  // only the schools this page mentions, so the page stays small
  const names = new Set<string>([
    ...doc.schedule.map((s) => s.opp), ...doc.transfersIn.map((p) => p.team), ...doc.transfersOut.map((p) => p.team),
    ...doc.portal.flowsIn.map((f) => f.team), ...doc.portal.flowsOut.map((f) => f.team),
    ...Object.values(doc.betting).flatMap((b) => b.log.map((g) => g.opp)),
  ]);
  const refs: Record<string, TeamRef> = {};
  for (const n of names) if (all[n]) refs[n] = { school: n, ...all[n], slug: ["fbs", "fcs"].includes(all[n].level ?? "") ? all[n].slug : null };
  const t = doc.team;
  return (
    <>
      <nav aria-label="Breadcrumb" className="-mb-6 text-[13px] text-muted"><Link href="/teams/" className="text-muted hover:text-ink">Teams</Link> / {doc.school}</nav>
      <section className="card overflow-hidden rounded-[20px]">
        <div aria-hidden="true" className="h-1.5" style={{ background: `linear-gradient(90deg, ${t.color} 0 70%, ${t.alt} 70% 100%)` }} />
        <div className="flex flex-wrap items-center gap-5 p-6">
          <TeamBadge team={t} size={88} />
          <div className="flex min-w-0 flex-1 flex-col gap-1">
            <h1 className="display m-0 text-[44px] leading-none sm:text-[56px]">{doc.school}</h1>
            <div className="text-[15px] text-soft">{[doc.mascot, doc.conference, doc.level?.toUpperCase()].filter(Boolean).join(" · ")}</div>
          </div>
          <Link href={`/compare/?a=${t.slug}`} className="inline-flex h-11 items-center rounded-xl border border-line-strong px-4 font-bold text-ink hover:border-accent hover:text-ink">Compare</Link>
        </div>
      </section>
      <TeamView doc={doc} refs={refs} />
    </>
  );
}
