import PicksView from "@/components/PicksView";
import { getMeta } from "@/lib/data";

export const dynamicParams = false;
export function generateStaticParams() {
  return getMeta().weeks.map((w) => ({ week: String(w.week) }));
}
export async function generateMetadata({ params }: { params: Promise<{ week: string }> }) {
  const { week } = await params;
  return { title: `Week ${week} picks` };
}
export default async function Page({ params }: { params: Promise<{ week: string }> }) {
  const { week } = await params;
  return <PicksView week={Number(week)} />;
}
