"use client";
import Link from "next/link";
import { useState } from "react";
import type { DirectoryTeam } from "@/lib/types";
import TeamBadge from "./TeamBadge";
import { Segmented } from "./Tabs";

export default function TeamDirectory({ teams }: { teams: DirectoryTeam[] }) {
  const [q, setQ] = useState("");
  const [level, setLevel] = useState<"fbs" | "fcs">("fbs");
  const s = q.trim().toLowerCase();
  const rows = teams.filter((t) => (s ? t.school.toLowerCase().includes(s) : t.level === level));
  const byConf = new Map<string, DirectoryTeam[]>();
  for (const t of rows) byConf.set(t.conference ?? "Other", [...(byConf.get(t.conference ?? "Other") ?? []), t]);
  const confs = [...byConf.keys()].sort((a, b) => (a === "FBS Independents" ? 1 : b === "FBS Independents" ? -1 : a.localeCompare(b)));
  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-center gap-3">
        <label className="sr-only" htmlFor="td-q">Search teams</label>
        <input id="td-q" type="search" className="field w-72" placeholder="Search all teams" value={q} onChange={(e) => setQ(e.target.value)} autoFocus />
        {!s && <Segmented label="Division" options={[{ value: "fbs", label: "FBS" }, { value: "fcs", label: "FCS" }]} value={level} onChange={setLevel} />}
      </div>
      {confs.map((c) => (
        <section key={c} className="flex flex-col gap-3">
          <h2 className="eyebrow m-0 text-muted">{c}</h2>
          <div className="grid grid-cols-[repeat(auto-fill,minmax(210px,1fr))] gap-2.5">
            {byConf.get(c)!.sort((a, b) => a.school.localeCompare(b.school)).map((t) => (
              <Link key={t.slug} href={`/teams/${t.slug}/`} className="card flex min-h-14 items-center gap-3 px-3 py-2 text-ink hover:border-accent hover:text-ink">
                <TeamBadge team={t} size={34} ring={false} /><span className="font-semibold">{t.school}</span>
              </Link>
            ))}
          </div>
        </section>
      ))}
      {!rows.length && <p className="text-muted">No teams match “{q}”.</p>}
    </div>
  );
}
