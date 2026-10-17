// Server-side data access. Every page is pre-rendered at build time, so these
// read the JSON files that export_web_data.py writes to public/data.
import fs from "node:fs";
import path from "node:path";
import type { BettingFile, CompareFile, DirectoryTeam, GameDetail, Meta, PortalRow, TeamDoc, TeamInfo, TrackRecord, WeekFile } from "./types";

const DIR = path.join(process.cwd(), "public", "data");
const cache = new Map<string, unknown>();

function load<T>(rel: string): T {
  if (!cache.has(rel)) cache.set(rel, JSON.parse(fs.readFileSync(path.join(DIR, rel), "utf8")));
  return cache.get(rel) as T;
}
function exists(rel: string) {
  return fs.existsSync(path.join(DIR, rel));
}

export const getMeta = () => load<Meta>("meta.json");
export const getWeek = (w: number) => load<WeekFile>(`weeks/${w}.json`);
export const getGame = (id: number | string) => load<GameDetail>(`games/${id}.json`);
export const getTrackRecord = () => load<TrackRecord>("track_record.json");
export const getTeams = () => load<Record<string, TeamInfo>>("teams.json");
export const getDirectory = () => load<DirectoryTeam[]>("team_directory.json");
export const getTeam = (slug: string) => load<TeamDoc>(`teams/${slug}.json`);
export const getBetting = (season: number) => load<BettingFile>(`betting/${season}.json`);
export const getPortal = () => load<PortalRow[]>("portal.json");
export const getCompare = () => load<CompareFile>("compare.json");

export function allGameIds(): string[] {
  return fs.readdirSync(path.join(DIR, "games")).filter((f) => f.endsWith(".json")).map((f) => f.replace(".json", ""));
}
export function currentWeek(): WeekFile | null {
  const m = getMeta();
  return m.currentWeek != null && exists(`weeks/${m.currentWeek}.json`) ? getWeek(m.currentWeek) : null;
}
export function tierRow(tier: string) {
  return getTrackRecord().tiers.find((t) => t.tier === tier) ?? null;
}
