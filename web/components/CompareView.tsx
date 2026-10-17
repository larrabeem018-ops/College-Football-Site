"use client";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";
import type { CompareFile, DirectoryTeam } from "@/lib/types";
import { fmt, signed } from "@/lib/format";
import TeamBadge from "./TeamBadge";
import TeamPicker from "./TeamPicker";

const STATS: [string, string, "higher" | "lower", number][] = [
  ["Points / game", "off_points_pg", "higher", 1], ["Yards / game", "off_yards_pg", "higher", 0], ["3rd down %", "off_third_down_pct", "higher", 1],
  ["Points allowed / game", "def_points_pg", "lower", 1], ["Yards allowed / game", "def_yards_pg", "lower", 0], ["3rd down % allowed", "def_third_down_pct", "lower", 1],
  ["Turnovers forced / game", "turnovers_forced_pg", "higher", 2], ["Turnover margin / game", "turnover_margin_pg", "higher", 2],
];

export default function CompareView({ teams }: { teams: DirectoryTeam[] }) {
  const sp = useSearchParams();
  const router = useRouter();
  const fbs = teams.filter((t) => t.level === "fbs");
  const [a, setA] = useState<string | null>(sp.get("a") ?? fbs[0]?.slug ?? null);
  const [b, setB] = useState<string | null>(sp.get("b") ?? fbs[1]?.slug ?? null);
  const [data, setData] = useState<CompareFile | null>(null);
  useEffect(() => { fetch("/data/compare.json").then((r) => r.json()).then(setData); }, []);
  useEffect(() => { router.replace(`/compare/?a=${a ?? ""}&b=${b ?? ""}`, { scroll: false }); }, [a, b, router]);

  const ta = teams.find((t) => t.slug === a), tb = teams.find((t) => t.slug === b);
  const row = (fa?: number | null, fb?: number | null, better: "higher" | "lower" = "higher") => {
    if (fa == null || fb == null || fa === fb) return [false, false];
    const aw = better === "higher" ? fa > fb : fa < fb;
    return [aw, !aw];
  };
  return (
    <div className="flex flex-col gap-6">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <TeamPicker id="ta" label="Team 1" teams={teams} value={a} onChange={setA} />
        <TeamPicker id="tb" label="Team 2" teams={teams} value={b} onChange={setB} />
      </div>
      {a === b && <p className="text-amber">Pick two different teams.</p>}
      {ta && tb && a !== b && (
        !data ? <p className="text-muted">Loading…</p> : (
          <>
            <div className="card grid grid-cols-[1fr_auto_1fr] items-center gap-4 p-5">
              {[ta, tb].map((t, i) => (
                <Link key={t.slug} href={`/teams/${t.slug}/`} className={`flex items-center gap-3 text-ink hover:text-accent ${i ? "order-3 flex-row-reverse text-right" : ""}`}>
                  <TeamBadge team={t} size={56} /><span className="display text-[28px] leading-none">{t.school}</span>
                </Link>
              ))}
              <span className="display order-2 text-[22px] text-muted">vs</span>
            </div>

            <section className="card overflow-x-auto p-1">
              <table className="tbl">
                <caption className="px-3.5 pt-3 text-left"><span className="display text-[22px]">Offseason net impact by unit</span><div className="text-[12px] text-muted">Players gained minus players lost, usage-weighted. Higher is better.</div></caption>
                <thead><tr><th className="w-[30%] text-center">{ta.abbr}</th><th className="text-center"> </th><th className="w-[30%] text-center">{tb.abbr}</th></tr></thead>
                <tbody>{(["Offense", "Defense", "Special Teams", "Total"] as const).map((u) => {
                  const va = data.units[ta.school]?.[u], vb = data.units[tb.school]?.[u];
                  const [aw, bw] = row(va, vb);
                  return <tr key={u}><td className={`mono text-center ${aw ? "font-bold text-accent" : ""}`}>{va != null ? signed(va, 0) : "—"}</td><td className="text-center text-[13px] text-muted">{u}</td><td className={`mono text-center ${bw ? "font-bold text-accent" : ""}`}>{vb != null ? signed(vb, 0) : "—"}</td></tr>;
                })}
                  <tr><td className="mono text-center">{fmt(data.returning[ta.school]?.pct, 0)}%</td><td className="text-center text-[13px] text-muted">Returning production</td><td className="mono text-center">{fmt(data.returning[tb.school]?.pct, 0)}%</td></tr>
                </tbody>
              </table>
            </section>

            <section className="card overflow-x-auto p-1">
              <table className="tbl">
                <caption className="px-3.5 pt-3 text-left"><span className="display text-[22px]">Season stats</span>
                  <div className="text-[12px] text-muted">{[ta, tb].map((t) => { const s = data.stats[t.school]; return s ? `${t.school}: ${s.season}, ${s.games} games` : `${t.school}: none`; }).join(" · ")}</div></caption>
                <tbody>{STATS.map(([label, key, better, d]) => {
                  const va = (data.stats[ta.school] as any)?.[key] as number | undefined, vb = (data.stats[tb.school] as any)?.[key] as number | undefined;
                  const [aw, bw] = row(va, vb, better);
                  return <tr key={key}><td className={`mono w-[30%] text-center ${aw ? "font-bold text-accent" : ""}`}>{fmt(va, d)}</td><td className="text-center text-[13px] text-muted">{label}</td><td className={`mono w-[30%] text-center ${bw ? "font-bold text-accent" : ""}`}>{fmt(vb, d)}</td></tr>;
                })}</tbody>
              </table>
            </section>
          </>
        )
      )}
    </div>
  );
}
