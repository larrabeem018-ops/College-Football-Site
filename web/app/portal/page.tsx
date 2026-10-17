import PortalView from "@/components/PortalView";
import { PageHeader } from "@/components/ui";
import { getMeta, getPortal, getTeams } from "@/lib/data";
import type { TeamRef } from "@/lib/types";

export const metadata = { title: "Transfer Portal" };
export default function Page() {
  const rows = getPortal();
  const all = getTeams();
  const refs: Record<string, TeamRef & { level?: string | null }> = {};
  for (const r of rows) {
    const t = all[r.team];
    if (t) refs[r.team] = { school: r.team, ...t, slug: ["fbs", "fcs"].includes(t.level ?? "") ? t.slug : null, level: t.level };
  }
  return (
    <>
      <PageHeader eyebrow={`${getMeta().season} cycle`} title="Transfer Portal">Who won the portal: total transfer rating gained minus rating lost for every school.</PageHeader>
      <PortalView rows={rows} refs={refs} />
    </>
  );
}
