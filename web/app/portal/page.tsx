import PortalView from "@/components/PortalView";
import Tabs from "@/components/Tabs";
import TransferProdView from "@/components/TransferProdView";
import { PageHeader } from "@/components/ui";
import { getMeta, getPortal, getTeams, getTransferProd } from "@/lib/data";
import type { TeamRef } from "@/lib/types";

export const metadata = { title: "Transfer Portal" };
export default function Page() {
  const rows = getPortal();
  const prod = getTransferProd();
  const all = getTeams();
  const refs: Record<string, TeamRef & { level?: string | null }> = {};
  const names = new Set<string>([...rows.map((r) => r.team), ...(prod?.teams.map((t) => t.team) ?? []),
    ...(prod?.players.flatMap((p) => [p.from, p.to]) ?? [])]);
  for (const n of names) {
    const t = all[n];
    if (t) refs[n] = { school: n, ...t, slug: ["fbs", "fcs"].includes(t.level ?? "") ? t.slug : null, level: t.level };
  }
  const season = getMeta().season;
  const ratings = <PortalView rows={rows} refs={refs} />;
  return (
    <>
      <PageHeader eyebrow={`${season} cycle`} title="Transfer Portal">
        How much this cycle&apos;s transfers are producing at their new schools, and who won the portal on paper (transfer rating gained minus rating lost).
      </PageHeader>
      {prod && prod.players.length ? (
        <Tabs label="Transfer portal views" tabs={[
          { id: "production", label: `${prod.season} production`, content: <TransferProdView data={prod} refs={refs} /> },
          { id: "ratings", label: "Portal ratings", content: ratings },
        ]} />
      ) : ratings}
    </>
  );
}
