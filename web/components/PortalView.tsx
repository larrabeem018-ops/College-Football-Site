"use client";
import Link from "next/link";
import { useState } from "react";
import type { PortalRow, TeamRef } from "@/lib/types";
import { signed } from "@/lib/format";
import TeamBadge from "./TeamBadge";
import { Segmented } from "./Tabs";

type Key = "net" | "in" | "out" | "nIn" | "nOut";
export default function PortalView({ rows, refs }: { rows: PortalRow[]; refs: Record<string, TeamRef> }) {
  const [q, setQ] = useState("");
  const [level, setLevel] = useState<"fbs" | "all">("fbs");
  const [sort, setSort] = useState<Key>("net");
  const [asc, setAsc] = useState(false);
  const isFbs = (t: string) => (refs[t] as any)?.level === "fbs";
  const base = rows.filter((r) => level === "all" || isFbs(r.team));
  const s = q.trim().toLowerCase();
  const list = base.filter((r) => !s || r.team.toLowerCase().includes(s)).sort((a, b) => (asc ? a[sort] - b[sort] : b[sort] - a[sort]));
  const winners = [...base].sort((a, b) => b.net - a.net).slice(0, 10), losers = [...base].sort((a, b) => a.net - b.net).slice(0, 10);
  const max = Math.max(...base.map((r) => Math.abs(r.net)), 1);
  const Name = ({ t }: { t: string }) => {
    const r = refs[t];
    const inner = <span className="flex items-center gap-2.5">{r && <TeamBadge team={r} size={28} ring={false} />}<span className="font-semibold">{t}</span></span>;
    return r?.slug ? <Link href={`/teams/${r.slug}/#transfers`} className="text-ink hover:text-accent">{inner}</Link> : inner;
  };
  const Board = ({ title, data }: { title: string; data: PortalRow[] }) => (
    <section className="card flex flex-col gap-2.5 p-5">
      <h2 className="display m-0 text-[22px]">{title}</h2>
      {data.map((r) => (
        <div key={r.team} className="grid grid-cols-[minmax(0,1fr)_110px_56px] items-center gap-3 text-[14px]">
          <Name t={r.team} />
          <div className="h-2 overflow-hidden rounded bg-chip"><div className={`h-full rounded ${r.net >= 0 ? "bg-accent" : "bg-loss"}`} style={{ width: `${(Math.abs(r.net) / max) * 100}%` }} /></div>
          <span className={`mono text-right font-semibold ${r.net >= 0 ? "text-accent" : "text-loss"}`}>{signed(r.net, 2)}</span>
        </div>
      ))}
    </section>
  );
  const th = (k: Key, label: string) => (
    <th className="text-right"><button type="button" onClick={() => (sort === k ? setAsc(!asc) : (setSort(k), setAsc(false)))} aria-sort={sort === k ? (asc ? "ascending" : "descending") : undefined}>{label}{sort === k ? (asc ? " ↑" : " ↓") : ""}</button></th>
  );
  return (
    <div className="flex flex-col gap-6">
      <Segmented label="Level" options={[{ value: "fbs", label: "FBS" }, { value: "all", label: "All schools" }]} value={level} onChange={setLevel} />
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Board title="Biggest winners" data={winners} />
        <Board title="Biggest losers" data={losers} />
      </div>
      <section className="flex flex-col gap-3">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 className="display m-0 text-[26px]">Every school</h2>
          <label className="sr-only" htmlFor="pq">Search schools</label>
          <input id="pq" type="search" className="field w-64" placeholder="Search schools" value={q} onChange={(e) => setQ(e.target.value)} />
        </div>
        <div className="card max-h-[640px] overflow-auto">
          <table className="tbl min-w-[620px]">
            <thead className="sticky top-0 bg-surface"><tr><th>School</th>{th("nIn", "In")}{th("nOut", "Out")}{th("in", "Rating in")}{th("out", "Rating out")}{th("net", "Net")}</tr></thead>
            <tbody>{list.map((r) => (
              <tr key={r.team}><td><Name t={r.team} /></td><td className="mono text-right">{r.nIn}</td><td className="mono text-right">{r.nOut}</td><td className="mono text-right">{r.in.toFixed(2)}</td><td className="mono text-right">{r.out.toFixed(2)}</td>
                <td className={`mono text-right font-bold ${r.net >= 0 ? "text-accent" : "text-loss"}`}>{signed(r.net, 2)}</td></tr>
            ))}</tbody>
          </table>
        </div>
        <p className="m-0 text-[12px] text-muted">Rating = the 247 transfer rating (0–1) summed over every player. Click a school for its full transfer breakdown.</p>
      </section>
    </div>
  );
}
