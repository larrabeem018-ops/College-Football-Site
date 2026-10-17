import MatchupsView from "@/components/MatchupsView";
import { Empty } from "@/components/ui";
import { getMeta } from "@/lib/data";

export const metadata = { title: "Matchups" };
export default function Page() {
  const w = getMeta().currentWeek;
  return w != null ? <MatchupsView week={w} /> : <Empty title="No schedule yet" />;
}
