import { Suspense } from "react";
import CompareView from "@/components/CompareView";
import { PageHeader } from "@/components/ui";
import { getDirectory } from "@/lib/data";

export const metadata = { title: "Compare teams" };
export default function Page() {
  return (
    <>
      <PageHeader eyebrow="Head to head" title="Compare teams" crumbs={[{ href: "/teams/", label: "Teams" }, { href: "/compare/", label: "Compare" }]}>
        How each roster changed this offseason, plus this season&apos;s numbers side by side. The better value in each row is highlighted.
      </PageHeader>
      <Suspense fallback={<p className="text-muted">Loading…</p>}><CompareView teams={getDirectory()} /></Suspense>
    </>
  );
}
