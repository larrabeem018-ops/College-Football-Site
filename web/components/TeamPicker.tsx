"use client";
import { useMemo, useState } from "react";
import type { DirectoryTeam } from "@/lib/types";
import TeamBadge from "./TeamBadge";

/** Searchable team chooser (combobox-style list). */
export default function TeamPicker({ teams, value, onChange, label, id }: { teams: DirectoryTeam[]; value: string | null; onChange: (slug: string) => void; label: string; id: string }) {
  const [q, setQ] = useState("");
  const [open, setOpen] = useState(false);
  const cur = teams.find((t) => t.slug === value);
  const hits = useMemo(() => {
    const s = q.trim().toLowerCase();
    return (s ? teams.filter((t) => t.school.toLowerCase().includes(s) || (t.abbr ?? "").toLowerCase() === s) : teams).slice(0, 40);
  }, [q, teams]);
  return (
    <div className="relative flex flex-col gap-1.5">
      <label htmlFor={id} className="text-[13px] font-semibold text-muted">{label}</label>
      <div className="field flex items-center gap-2 px-2">
        {cur && <TeamBadge team={cur} size={28} ring={false} />}
        <input id={id} role="combobox" aria-expanded={open} aria-controls={`${id}-list`} aria-autocomplete="list" autoComplete="off"
          className="h-full min-w-0 flex-1 bg-transparent outline-none" placeholder={cur?.school ?? "Search teams"}
          value={open ? q : cur?.school ?? ""} onFocus={() => { setOpen(true); setQ(""); }} onBlur={() => setTimeout(() => setOpen(false), 150)}
          onChange={(e) => setQ(e.target.value)}
          onKeyDown={(e) => { if (e.key === "Enter" && hits[0]?.slug) { onChange(hits[0].slug); setOpen(false); (e.target as HTMLInputElement).blur(); } }} />
      </div>
      {open && (
        <ul id={`${id}-list`} role="listbox" className="absolute top-full z-20 mt-1 max-h-80 w-full overflow-auto rounded-xl border border-line-strong bg-surface p-1 shadow-2xl">
          {hits.map((t) => (
            <li key={t.slug} role="option" aria-selected={t.slug === value}>
              <button type="button" onMouseDown={(e) => e.preventDefault()} onClick={() => { onChange(t.slug!); setOpen(false); }}
                className="flex min-h-11 w-full cursor-pointer items-center gap-3 rounded-lg px-2 text-left hover:bg-raised">
                <TeamBadge team={t} size={26} ring={false} /><span className="font-semibold">{t.school}</span><span className="ml-auto text-[12px] text-muted">{t.conference}</span>
              </button>
            </li>
          ))}
          {!hits.length && <li className="p-3 text-muted">No teams found</li>}
        </ul>
      )}
    </div>
  );
}
