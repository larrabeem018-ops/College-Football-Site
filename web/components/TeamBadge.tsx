"use client";
import { useEffect, useRef, useState } from "react";
import { luminance } from "@/lib/format";

type Props = { team: { school: string; abbr: string; color: string; logo: string | null }; size?: number; ring?: boolean; overlap?: boolean };

/** Team logo from the CFBD logo URL, falling back to a team-colored circle with the abbreviation. */
export default function TeamBadge({ team, size = 36, ring = true, overlap = false }: Props) {
  const [failed, setFailed] = useState(false);
  const img = useRef<HTMLImageElement>(null);
  // an image that failed before the page hydrated never fires onError, so check on mount
  useEffect(() => { const el = img.current; if (el && el.complete && el.naturalWidth === 0) setFailed(true); }, []);
  const style: React.CSSProperties = {
    width: size, height: size, marginLeft: overlap ? -Math.round(size * 0.25) : 0,
    boxShadow: ring ? `0 0 0 ${size > 48 ? 3 : 2}px var(--color-surface)` : undefined,
  };
  if (team.logo && !failed) {
    return (
      <span className="inline-flex shrink-0 items-center justify-center rounded-full bg-[#F4F6F8]" style={style}>
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img ref={img} src={team.logo} alt={`${team.school} logo`} width={size} height={size} loading="lazy"
          onError={() => setFailed(true)} style={{ width: size * 0.78, height: size * 0.78, objectFit: "contain" }} />
      </span>
    );
  }
  const text = luminance(team.color) > 0.3 ? "#0B0F14" : "#FFFFFF";
  return (
    <span role="img" aria-label={`${team.school} logo`} className="display inline-flex shrink-0 items-center justify-center rounded-full"
      style={{ ...style, background: team.color, color: text, fontSize: Math.max(8, size * (team.abbr.length <= 3 ? 0.32 : team.abbr.length === 4 ? 0.25 : 0.21)), letterSpacing: 0 }}>
      {team.abbr}
    </span>
  );
}

export function BadgePair({ away, home, size = 34 }: { away: Props["team"]; home: Props["team"]; size?: number }) {
  return (
    <span className="inline-flex shrink-0">
      <TeamBadge team={away} size={size} />
      <TeamBadge team={home} size={size} overlap />
    </span>
  );
}
