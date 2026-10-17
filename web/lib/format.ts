import type { Game, TeamRef } from "./types";

export const TIER_LABEL: Record<string, string> = {
  fav_value: "Watchlist", big_gap: "Big disagreement", lean: "Lean", pass: "No edge",
};
export const TIER_LONG: Record<string, string> = {
  fav_value: "Model backs the favorite", big_gap: "Big disagreement", lean: "Lean (3–10 pt gap)", pass: "No edge",
};

const TZ = "America/New_York";
export function kickShort(iso: string) {
  const d = new Date(iso);
  const day = d.toLocaleDateString("en-US", { weekday: "short", timeZone: TZ });
  const t = d.toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit", timeZone: TZ });
  return `${day} ${t}`;
}
export function kickLong(iso: string) {
  const d = new Date(iso);
  const date = d.toLocaleDateString("en-US", { weekday: "short", month: "short", day: "numeric", timeZone: TZ });
  const t = d.toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit", timeZone: TZ });
  return `${date} · ${t} ET`;
}
export function dateShort(iso: string) {
  return new Date(iso).toLocaleDateString("en-US", { month: "short", day: "numeric", timeZone: TZ });
}

const MINUS = "−";
/** Spread in favorite form from the home-perspective number: "LOU −15.5". */
export function favLine(home: TeamRef, away: TeamRef, spreadHome: number | null, useAbbr = true) {
  if (spreadHome == null) return "No line";
  const name = (t: TeamRef) => (useAbbr ? t.abbr : t.school);
  if (Math.abs(spreadHome) < 0.05) return "Pick'em";
  return spreadHome < 0 ? `${name(home)} ${MINUS}${Math.abs(spreadHome).toFixed(1)}` : `${name(away)} ${MINUS}${spreadHome.toFixed(1)}`;
}
/** "Team +3.5" from one team's point of view. */
export function teamLine(team: string, home: string, spreadHome: number) {
  const v = team === home ? spreadHome : -spreadHome;
  if (Math.abs(v) < 0.01) return `${team} PK`;
  return `${team} ${v > 0 ? "+" : MINUS}${Math.abs(v).toFixed(1)}`;
}
export const fmt = (v: number | null | undefined, d = 1) => (v == null || Number.isNaN(v) ? "—" : v.toFixed(d));
export const fmtInt = (v: number | null | undefined) => (v == null ? "—" : Math.round(v).toLocaleString("en-US"));
export const signed = (v: number, d = 1) => `${v > 0 ? "+" : v < 0 ? MINUS : ""}${Math.abs(v).toFixed(d)}`;
export const money = (v: number) => `${v < 0 ? MINUS : ""}$${Math.abs(v).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
export const recordText = (w: number, l: number, p = 0) => `${w}–${l}${p ? `–${p}` : ""}`;
export const pctText = (w: number, l: number) => (w + l ? `${((100 * w) / (w + l)).toFixed(0)}%` : "—");

/** Render the **bold** markdown used in the model's explanations. */
export function boldParts(s: string): { text: string; bold: boolean }[] {
  return s.split(/(\*\*[^*]+\*\*)/g).filter(Boolean).map((p) => (p.startsWith("**") ? { text: p.slice(2, -2), bold: true } : { text: p, bold: false }));
}

export function luminance(hex: string) {
  const h = hex.replace("#", "");
  if (h.length !== 6) return 0;
  const c = [0, 2, 4].map((i) => {
    const v = parseInt(h.slice(i, i + 2), 16) / 255;
    return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4);
  });
  return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2];
}
export const teamHref = (t: TeamRef | { slug: string | null }) => (t.slug ? `/teams/${t.slug}/` : null);
export const gameTitle = (g: Game) => `${g.away.school} ${g.neutral ? "vs" : "@"} ${g.home.school}`;
export const heightText = (inches: number | null) => (inches ? `${Math.floor(inches / 12)}'${Math.round(inches % 12)}"` : "—");
