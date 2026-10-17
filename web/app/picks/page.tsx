import PicksView from "@/components/PicksView";
import { Empty } from "@/components/ui";
import { getMeta } from "@/lib/data";

export const metadata = { title: "Picks" };

export default function Page() {
  const w = getMeta().currentWeek;
  return w != null ? <PicksView week={w} /> : <Empty title="No model picks yet">Run score_model.py and export_web_data.py.</Empty>;
}
