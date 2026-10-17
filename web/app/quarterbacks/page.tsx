import QbView from "@/components/QbView";
import { PageHeader } from "@/components/ui";
import { getMeta } from "@/lib/data";

export const metadata = { title: "Quarterbacks" };
export default function Page() {
  return (
    <>
      <PageHeader eyebrow="Under center" title="Quarterbacks">Who&apos;s playing the best football at quarterback. Rank the field by any stat, then compare any two QBs head to head.</PageHeader>
      <QbView seasons={getMeta().qbSeasons} />
    </>
  );
}
