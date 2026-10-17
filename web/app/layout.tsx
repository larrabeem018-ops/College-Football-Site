import type { Metadata, Viewport } from "next";
import "./globals.css";
import SiteHeader, { MobileTabBar } from "@/components/SiteHeader";
import { getMeta } from "@/lib/data";

export const metadata: Metadata = {
  title: { default: "CFB Analytics Hub", template: "%s · CFB Analytics Hub" },
  description: "Weekly college football model picks, matchups, team roster turnover, quarterbacks, the transfer portal and ATS results.",
  icons: { icon: "/favicon.svg" },
};
export const viewport: Viewport = { themeColor: "#0B0F14", width: "device-width", initialScale: 1 };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  const meta = getMeta();
  const updated = new Date(meta.generated).toLocaleString("en-US", { month: "short", day: "numeric", hour: "numeric", minute: "2-digit", timeZone: "America/New_York" });
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="" />
        <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@600;700&family=JetBrains+Mono:wght@500;600&family=Manrope:wght@400;500;600;700&display=swap" />
      </head>
      <body className="min-h-screen pb-24 lg:pb-0">
        <SiteHeader />
        <main id="main" className="mx-auto flex max-w-[1280px] flex-col gap-12 px-4 pb-16 pt-8 sm:px-6 sm:pt-10">
          {children}
          <footer className="mt-6 flex flex-wrap justify-between gap-2 border-t border-line pt-5 text-[13px] text-muted">
            <span>For entertainment and analysis, not betting advice. Built by a college football fan and data enthusiast.</span>
            <span>Data: <a href="https://collegefootballdata.com" className="text-muted underline hover:text-ink">collegefootballdata.com</a> · Updated {updated} ET</span>
          </footer>
        </main>
        <MobileTabBar />
      </body>
    </html>
  );
}
