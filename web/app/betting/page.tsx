import BettingView from "@/components/BettingView";
import { PageHeader } from "@/components/ui";
import { getDirectory, getMeta } from "@/lib/data";

export const metadata = { title: "ATS Results" };
export default function Page() {
  return (
    <>
      <PageHeader eyebrow="Against the spread" title="ATS Results">How every team has done against the Vegas line: cover rates as favorite and underdog, the biggest upsets, and what betting every game would have paid.</PageHeader>
      <BettingView seasons={getMeta().bettingSeasons} teams={getDirectory()} />
    </>
  );
}
