import type { NextConfig } from "next";

// Fully static site: every page is generated at build time from the JSON in
// public/data (written by export_web_data.py), so there's no server to run.
const nextConfig: NextConfig = {
  output: "export",
  images: { unoptimized: true },
  trailingSlash: true,
};

export default nextConfig;
