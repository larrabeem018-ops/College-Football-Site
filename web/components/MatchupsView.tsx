import { getWeek } from "@/lib/data";
import MatchupsGrid from "./MatchupsGrid";
import { WeekSwitcher } from "./PicksView";
import { PageHeader } from "./ui";

export default function MatchupsView({ week }: { week: number }) {
  const wk = getWeek(week);
  return (
    <>
      <PageHeader eyebrow="Game week" title={`Week ${week} matchups`} crumbs={[{ href: "/", label: "This Week" }, { href: "/matchups/", label: "Matchups" }]}
        right={<WeekSwitcher week={week} base="/matchups/" />}>
        Every game with the spread and the model&apos;s lean. Open any game for a stat-for-stat comparison, returning production and the model&apos;s reasoning.
      </PageHeader>
      <MatchupsGrid games={wk.games} />
    </>
  );
}
