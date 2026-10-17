import Link from "next/link";
import type { ReactNode } from "react";
import { boldParts, TIER_LABEL } from "@/lib/format";

export function PageHeader({ eyebrow, title, children, crumbs, right }: { eyebrow?: string; title: ReactNode; children?: ReactNode; crumbs?: { href: string; label: string }[]; right?: ReactNode }) {
  return (
    <div className="flex flex-col gap-3">
      {crumbs && (
        <nav aria-label="Breadcrumb" className="text-[13px] text-muted">
          {crumbs.map((c, i) => (
            <span key={c.href}>
              <Link href={c.href} className="text-muted hover:text-ink">{c.label}</Link>
              {i < crumbs.length - 1 ? " / " : ""}
            </span>
          ))}
        </nav>
      )}
      {eyebrow && <div className="eyebrow text-accent">{eyebrow}</div>}
      <div className="flex flex-wrap items-end justify-between gap-4">
        <h1 className="display m-0 text-[40px] leading-none sm:text-[56px]">{title}</h1>
        {right}
      </div>
      {children && <div className="max-w-[760px] text-[16px] leading-relaxed text-soft">{children}</div>}
    </div>
  );
}

export function SectionTitle({ children, right, id }: { children: ReactNode; right?: ReactNode; id?: string }) {
  return (
    <div className="flex flex-wrap items-baseline justify-between gap-2">
      <h2 id={id} className="display m-0 text-[28px]">{children}</h2>
      {right && <div className="text-[13px] text-muted">{right}</div>}
    </div>
  );
}

export function StatCard({ label, value, sub, tone = "muted" }: { label: string; value: ReactNode; sub?: ReactNode; tone?: "good" | "bad" | "muted" | "amber" }) {
  const color = tone === "good" ? "text-accent" : tone === "bad" ? "text-loss" : tone === "amber" ? "text-amber" : "text-soft";
  return (
    <div className="card p-5">
      <div className="text-[13px] font-semibold text-muted">{label}</div>
      <div className="mono mt-2 text-[28px] font-semibold leading-tight">{value}</div>
      {sub && <div className={`mt-1 text-[13px] font-semibold ${color}`}>{sub}</div>}
    </div>
  );
}

const TIER_STYLE: Record<string, string> = {
  fav_value: "bg-accent-tint text-accent",
  big_gap: "bg-amber-tint text-amber",
  lean: "bg-blue-tint text-blue-text",
  pass: "bg-chip text-muted",
};
export function TierTag({ tier }: { tier: string | null }) {
  if (!tier) return <span className="rounded-full bg-chip px-2 py-[3px] text-[11px] font-bold text-muted">No line</span>;
  return <span className={`whitespace-nowrap rounded-full px-2 py-[3px] text-[11px] font-bold ${TIER_STYLE[tier]}`}>{TIER_LABEL[tier]}</span>;
}
export function ResultTag({ result }: { result: string | null }) {
  if (!result || result === "Pending") return null;
  const cls = result === "Win" ? "bg-accent text-[#06120B]" : result === "Loss" ? "bg-loss text-[#1A0806]" : "bg-chip text-soft";
  return <span className={`rounded-full px-2 py-[3px] text-[11px] font-bold ${cls}`}>{result}</span>;
}

export function GapBar({ edge, tier }: { edge: number | null; tier: string | null }) {
  const e = Math.abs(edge ?? 0);
  const color = tier === "fav_value" ? "var(--color-accent)" : tier === "big_gap" ? "var(--color-amber)" : tier === "lean" ? "var(--color-blue)" : "var(--color-muted)";
  return (
    <div className="flex items-center gap-2">
      <div className="h-2 flex-1 overflow-hidden rounded bg-chip">
        <div className="h-full rounded" style={{ width: `${Math.min(100, e * 7)}%`, background: color }} />
      </div>
      <span className="mono w-9 text-right text-[13px] font-semibold">{e.toFixed(1)}</span>
    </div>
  );
}

export function Bold({ text }: { text: string }) {
  return (
    <>
      {boldParts(text).map((p, i) => (p.bold ? <strong key={i} className="text-ink">{p.text}</strong> : <span key={i}>{p.text}</span>))}
    </>
  );
}

export function Callout({ tone = "amber", title, children }: { tone?: "amber" | "green" | "plain"; title?: ReactNode; children: ReactNode }) {
  const cls = tone === "amber" ? "bg-amber-tint border-amber-line text-amber-text" : tone === "green" ? "bg-accent-tint border-[#1E4A30] text-body" : "bg-surface border-line text-soft";
  return (
    <div className={`rounded-2xl border p-5 text-[14px] leading-relaxed ${cls}`}>
      {title && <div className={`mb-1 font-bold ${tone === "amber" ? "text-amber" : "text-ink"}`}>{title}</div>}
      {children}
    </div>
  );
}

export function Empty({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <div className="rounded-2xl border border-dashed border-line-strong p-10 text-center text-muted">
      <div className="mb-1 text-[17px] font-bold text-ink">{title}</div>
      {children}
    </div>
  );
}

export function Arrow() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <line x1="5" y1="12" x2="19" y2="12" /><polyline points="13,6 19,12 13,18" />
    </svg>
  );
}
