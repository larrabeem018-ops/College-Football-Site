"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";

export const NAV = [
  { href: "/", label: "This Week", match: (p: string) => p === "/" },
  { href: "/picks/", label: "Picks", match: (p: string) => p.startsWith("/picks") },
  { href: "/matchups/", label: "Matchups", match: (p: string) => p.startsWith("/matchups") || p.startsWith("/games") },
  { href: "/teams/", label: "Teams", match: (p: string) => p.startsWith("/teams") || p.startsWith("/compare") },
  { href: "/quarterbacks/", label: "Quarterbacks", match: (p: string) => p.startsWith("/quarterbacks") },
  { href: "/portal/", label: "Transfer Portal", match: (p: string) => p.startsWith("/portal") },
  { href: "/betting/", label: "ATS Results", match: (p: string) => p.startsWith("/betting") },
  { href: "/model/", label: "Model Record", match: (p: string) => p.startsWith("/model") },
];

export function Logo() {
  return (
    <svg width="28" height="28" viewBox="0 0 32 32" fill="none" aria-hidden="true">
      <ellipse cx="16" cy="16" rx="13" ry="9" transform="rotate(-32 16 16)" stroke="#2FD27A" strokeWidth="2" />
      <line x1="8.5" y1="20.2" x2="23.5" y2="11.8" stroke="#2FD27A" strokeWidth="2" />
      <line x1="12" y1="14.4" x2="14.2" y2="17.4" stroke="#2FD27A" strokeWidth="1.6" />
      <line x1="15" y1="12.8" x2="17.2" y2="15.8" stroke="#2FD27A" strokeWidth="1.6" />
      <line x1="18" y1="11.2" x2="20.2" y2="14.2" stroke="#2FD27A" strokeWidth="1.6" />
    </svg>
  );
}

export default function SiteHeader() {
  const path = usePathname() || "/";
  const [open, setOpen] = useState(false);
  return (
    <header className="sticky top-0 z-30 border-b border-line bg-bg/95 backdrop-blur">
      <a href="#main" className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-3 focus:z-50 focus:rounded focus:bg-ink focus:px-3 focus:py-2 focus:text-bg">Skip to content</a>
      <nav aria-label="Primary" className="mx-auto flex max-w-[1280px] items-center gap-4 px-4 py-3 sm:px-6">
        <Link href="/" className="flex shrink-0 items-center gap-2.5 text-ink hover:text-ink">
          <Logo />
          <span className="display text-[22px] tracking-wide">CFB Analytics Hub</span>
        </Link>
        <div className="hidden flex-1 flex-wrap items-center gap-0.5 lg:flex">
          {NAV.map((n) => {
            const on = n.match(path);
            return (
              <Link key={n.href} href={n.href} aria-current={on ? "page" : undefined}
                className={`rounded-lg px-3 py-2.5 text-[14px] font-semibold ${on ? "bg-raised text-ink" : "text-soft hover:bg-raised hover:text-ink"}`}>
                {n.label}
              </Link>
            );
          })}
        </div>
        <button type="button" className="ml-auto flex h-11 w-11 cursor-pointer items-center justify-center rounded-xl border border-line-strong lg:hidden"
          aria-expanded={open} aria-controls="mobile-menu" aria-label={open ? "Close menu" : "Open menu"} onClick={() => setOpen(!open)}>
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#AEB8C4" strokeWidth="2" strokeLinecap="round" aria-hidden="true">
            {open ? (<><line x1="6" y1="6" x2="18" y2="18" /><line x1="18" y1="6" x2="6" y2="18" /></>) : (<><line x1="4" y1="7" x2="20" y2="7" /><line x1="4" y1="12" x2="20" y2="12" /><line x1="4" y1="17" x2="20" y2="17" /></>)}
          </svg>
        </button>
      </nav>
      {open && (
        <div id="mobile-menu" className="border-t border-line px-4 pb-4 lg:hidden">
          {NAV.map((n) => (
            <Link key={n.href} href={n.href} onClick={() => setOpen(false)} aria-current={n.match(path) ? "page" : undefined}
              className={`flex min-h-12 items-center border-b border-line text-[16px] font-semibold ${n.match(path) ? "text-accent" : "text-ink"}`}>
              {n.label}
            </Link>
          ))}
        </div>
      )}
    </header>
  );
}

const TAB_ICONS: Record<string, React.ReactNode> = {
  "/": <><rect x="3" y="5" width="18" height="16" rx="2" /><line x1="3" y1="10" x2="21" y2="10" /><line x1="8" y1="3" x2="8" y2="7" /><line x1="16" y1="3" x2="16" y2="7" /></>,
  "/picks/": <><circle cx="12" cy="12" r="8" /><circle cx="12" cy="12" r="4" /></>,
  "/teams/": <path d="M12 3l8 4v5c0 5-3.5 8-8 9-4.5-1-8-4-8-9V7z" />,
  "/quarterbacks/": <polygon points="12,3 20,9 17,19 7,19 4,9" />,
  "/matchups/": <><path d="M7 8h10" /><path d="M15 5l3 3-3 3" /><path d="M17 16H7" /><path d="M9 13l-3 3 3 3" /></>,
};

/** Bottom tab bar on phones. */
export function MobileTabBar() {
  const path = usePathname() || "/";
  const tabs = [NAV[0], NAV[1], NAV[2], NAV[3], NAV[4]];
  return (
    <nav aria-label="Quick" className="fixed inset-x-0 bottom-0 z-30 grid grid-cols-5 border-t border-line bg-surface-2/95 px-1 pb-[max(10px,env(safe-area-inset-bottom))] pt-1.5 backdrop-blur lg:hidden">
      {tabs.map((t) => {
        const on = t.match(path);
        return (
          <Link key={t.href} href={t.href} aria-current={on ? "page" : undefined}
            className={`flex min-h-12 flex-col items-center justify-center gap-1 text-[11px] font-bold ${on ? "text-accent" : "text-muted"}`}>
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{TAB_ICONS[t.href]}</svg>
            {t.label === "Quarterbacks" ? "QBs" : t.label}
          </Link>
        );
      })}
    </nav>
  );
}
