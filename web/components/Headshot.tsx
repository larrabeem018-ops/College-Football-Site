"use client";
import { useEffect, useRef, useState } from "react";

/** ESPN headshot by player id (CFBD athlete ids are ESPN ids), with an initials fallback. */
export default function Headshot({ id, name, size = 96 }: { id: number; name: string; size?: number }) {
  const [failed, setFailed] = useState(false);
  const img = useRef<HTMLImageElement>(null);
  useEffect(() => { setFailed(false); }, [id]);
  useEffect(() => { const el = img.current; if (el && el.complete && el.naturalWidth === 0) setFailed(true); }, [id]);
  const initials = name.split(" ").filter(Boolean).map((p) => p[0]).slice(0, 2).join("");
  const box = { width: size, height: size };
  if (failed) {
    return (
      <span role="img" aria-label={name} style={{ ...box, fontSize: size * 0.34 }}
        className="display inline-flex shrink-0 items-center justify-center rounded-full border border-line-strong bg-chip text-soft">{initials}</span>
    );
  }
  return (
    <span style={box} className="inline-flex shrink-0 overflow-hidden rounded-full border border-line-strong bg-chip">
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img ref={img} key={id} alt={`${name} headshot`} loading="lazy" onError={() => setFailed(true)}
        src={`https://a.espncdn.com/combiner/i?img=/i/headshots/college-football/players/full/${id}.png&w=${size * 2}&h=${Math.round(size * 1.45)}`}
        style={{ width: "100%", height: "100%", objectFit: "cover", objectPosition: "center top" }} />
    </span>
  );
}
