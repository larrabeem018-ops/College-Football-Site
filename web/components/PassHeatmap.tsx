"use client";
import { useState } from "react";
import type { QbLocations, ZoneAvg, ZoneName } from "@/lib/types";
import { luminance } from "@/lib/format";

export type HeatMetric = "pct" | "share" | "ypa";
export const HEAT_METRICS: { value: HeatMetric; label: string }[] = [
  { value: "pct", label: "Completion %" },
  { value: "share", label: "Share of throws" },
  { value: "ypa", label: "Yards / attempt" },
];
// fixed domains so two quarterbacks (and two seasons) are colored on the same scale
const DOMAIN: Record<HeatMetric, [number, number]> = { pct: [20, 95], share: [0, 45], ypa: [3, 20] };
// one hue (turf green), dark -> light; the low end recedes toward the dark surface
const RAMP = ["#12301F", "#164029", "#1B5234", "#20663F", "#267C4B", "#2C9558", "#33B066", "#4FC67D", "#7DD9A0", "#B2EBC8"];
const ROWS: { depth: string; zones: ZoneName[] }[] = [
  { depth: "Deep", zones: ["deep left", "deep middle", "deep right"] },
  { depth: "Short", zones: ["short left", "short middle", "short right"] },
];
const SMALL = 5;

function colorFor(v: number | null, m: HeatMetric) {
  if (v == null) return null;
  const [lo, hi] = DOMAIN[m];
  const t = Math.max(0, Math.min(1, (v - lo) / (hi - lo)));
  return RAMP[Math.round(t * (RAMP.length - 1))];
}
const fmtMetric = (v: number | null, m: HeatMetric) => (v == null ? "—" : m === "ypa" ? v.toFixed(1) : `${Math.round(v)}%`);
const title = (z: string) => z.replace(/\b\w/g, (c) => c.toUpperCase());

/** Six-zone passing heatmap drawn on a half field, from the quarterback's point of view. */
export default function PassHeatmap({ name, loc, avg, metric }: { name: string; loc: QbLocations | null; avg: ZoneAvg; metric: HeatMetric }) {
  const [hover, setHover] = useState<ZoneName | null>(null);
  if (!loc) {
    return <div className="flex min-h-[300px] items-center justify-center rounded-xl border border-dashed border-line-strong p-6 text-center text-[14px] text-muted">No pass-location data for {name} this season.</div>;
  }
  const total = Object.values(loc.zones).reduce((a, z) => a + z.att, 0);
  const value = (z: ZoneName): number | null => {
    const s = loc.zones[z];
    if (metric === "pct") return s.att ? (s.comp / s.att) * 100 : null;
    if (metric === "share") return total ? (s.att / total) * 100 : null;
    return s.att ? s.ypa : null;
  };
  const detail = hover ? loc.zones[hover] : null;
  const a = hover ? avg[hover] : null;

  return (
    <div className="flex flex-col gap-3">
      <div className="relative overflow-hidden rounded-xl border border-line-strong bg-[#0D1A13]">
        {/* yard lines */}
        <div aria-hidden="true" className="pointer-events-none absolute inset-0" style={{ backgroundImage: "repeating-linear-gradient(0deg, transparent 0 39px, #ffffff10 39px 40px)" }} />
        <div className="relative grid grid-cols-[44px_repeat(3,minmax(0,1fr))] gap-[2px] p-2 pb-0">
          <div />
          {["Left", "Middle", "Right"].map((d) => <div key={d} className="pb-1 text-center text-[11px] font-bold uppercase tracking-wider text-muted">{d}</div>)}
          {ROWS.map((row) => (
            <div key={row.depth} className="contents">
              <div className="flex items-center justify-center text-[11px] font-bold uppercase tracking-wider text-muted [writing-mode:vertical-rl] rotate-180">{row.depth}</div>
              {row.zones.map((z) => {
                const s = loc.zones[z];
                const v = value(z);
                const bg = colorFor(v, metric);
                const dark = bg ? luminance(bg) > 0.3 : false;
                const av = metric === "pct" ? avg[z]?.pct : metric === "share" ? avg[z]?.share : avg[z]?.ypa;
                const diff = v != null && av != null ? v - av : null;
                const label = `${title(z)}: ${s.comp} of ${s.att} completed${s.att ? ` (${Math.round((s.comp / s.att) * 100)}%)` : ""}, ${fmtMetric(v, metric)} ${HEAT_METRICS.find((x) => x.value === metric)!.label.toLowerCase()}`;
                return (
                  <button key={z} type="button" aria-label={label} onMouseEnter={() => setHover(z)} onFocus={() => setHover(z)} onMouseLeave={() => setHover(null)} onBlur={() => setHover(null)}
                    className={`relative flex h-[118px] cursor-default flex-col items-center justify-center gap-0.5 rounded-md outline-offset-[-2px] ${hover === z ? "ring-2 ring-ink" : ""}`}
                    style={{ background: bg ?? "repeating-linear-gradient(135deg, #1A2430 0 6px, #141C26 6px 12px)", opacity: s.att && s.att < SMALL ? 0.55 : 1, color: dark ? "#0B0F14" : "#E8EDF2" }}>
                    <span className="mono text-[24px] font-semibold leading-none">{s.att ? fmtMetric(v, metric) : "—"}</span>
                    <span className="mono text-[12px] opacity-85">{s.comp}/{s.att}</span>
                    {diff != null && s.att >= SMALL && (
                      <span className="mono text-[11px] font-semibold opacity-85">{diff >= 0 ? "+" : "−"}{metric === "ypa" ? Math.abs(diff).toFixed(1) : Math.round(Math.abs(diff))} vs FBS</span>
                    )}
                  </button>
                );
              })}
            </div>
          ))}
        </div>
        {/* line of scrimmage + quarterback */}
        <div className="relative mx-2 mt-2 border-t-2 border-dashed border-amber/70" />
        <div className="relative flex items-center justify-center gap-2 py-2 text-[11px] font-bold uppercase tracking-wider text-muted">
          <span className="h-3 w-3 rounded-full bg-amber" aria-hidden="true" />Line of scrimmage
        </div>
      </div>

      <div className="min-h-[44px] rounded-lg bg-surface-2 px-3 py-2 text-[13px] leading-relaxed text-soft" aria-live="polite">
        {detail && hover ? (
          <>
            <b className="text-ink">{title(hover)}</b> · {detail.comp}/{detail.att} ({detail.att ? Math.round((detail.comp / detail.att) * 100) : 0}%)
            {detail.ypa != null && <> · {detail.ypa.toFixed(1)} Y/A</>}{detail.adot != null && <> · {detail.adot.toFixed(1)} yd avg depth</>}
            {" "}· {detail.int} INT{detail.success != null && <> · {Math.round(detail.success * 100)}% success</>}
            {a?.pct != null && <span className="text-muted"> · FBS avg {Math.round(a.pct)}% comp</span>}
          </>
        ) : (
          <span className="text-muted">Hover or tab to a zone for details. {total} charted throws{loc.unknown ? ` (${loc.unknown} more without a recorded location)` : ""}.</span>
        )}
      </div>
    </div>
  );
}

export function HeatLegend({ metric }: { metric: HeatMetric }) {
  const [lo, hi] = DOMAIN[metric];
  const f = (v: number) => (metric === "ypa" ? `${v}` : `${v}%`);
  return (
    <div className="flex items-center gap-3 text-[12px] text-muted">
      <span className="mono">{f(lo)}</span>
      <div className="h-2.5 w-44 rounded-full" style={{ background: `linear-gradient(90deg, ${RAMP.join(",")})` }} aria-hidden="true" />
      <span className="mono">{f(hi)}+</span>
      <span className="ml-2 inline-flex items-center gap-1.5"><span className="inline-block h-3 w-3 rounded-sm opacity-55" style={{ background: RAMP[5] }} />Fewer than {SMALL} throws</span>
    </div>
  );
}
