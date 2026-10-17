import MatchupsView from "@/components/MatchupsView";
import { getMeta } from "@/lib/data";

export const dynamicParams = false;
export function generateStaticParams() {
  return getMeta().weeks.map((w) => ({ week: String(w.week) }));
}
export async function generateMetadata({ params }: { params: Promise<{ week: string }> }) {
  return { title: `Week ${(await params).week} matchups` };
}
export default async function Page({ params }: { params: Promise<{ week: string }> }) {
  return <MatchupsView week={Number((await params).week)} />;
}
