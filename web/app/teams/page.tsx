import Link from "next/link";
import TeamDirectory from "@/components/TeamDirectory";
import { PageHeader } from "@/components/ui";
import { getDirectory } from "@/lib/data";

export const metadata = { title: "Teams" };
export default function Page() {
  return (
    <>
      <PageHeader eyebrow="Every program" title="Teams" right={<Link href="/compare/" className="inline-flex h-11 items-center rounded-xl border border-line-strong px-4 font-bold text-ink hover:border-accent hover:text-ink">Compare two teams</Link>}>
        Each team page brings together the schedule, season stats, roster turnover, transfers and betting record.
      </PageHeader>
      <TeamDirectory teams={getDirectory()} />
    </>
  );
}
