import type { NextConfig } from "next";

// The browser calls the API on the same origin (`/api/...`) and Next.js
// proxies it to FastAPI. API and frontend run in one container, so the
// default is the API process next to us. `next build` bakes rewrites into
// the build, so set API_PROXY_TARGET at build time (or for `next dev`; the
// local development stack points it at the api container).
const apiProxyTarget = (process.env.API_PROXY_TARGET ?? "http://127.0.0.1:8000").replace(/\/+$/, "");

const nextConfig: NextConfig = {
  output: "standalone",
  // `next dev` behind a local proxy on a *.localhost name loads
  // its dev assets and HMR from that host; the shared `browser` container (CDP,
  // MCP `open-revoke-browser`) reaches the panel as http://web:3000.
  allowedDevOrigins: ["*.localhost", "web"],
  // Bottom left would cover the signed-in user in the sidebar footer.
  devIndicators: { position: "bottom-right" },
  // Clickjacking and sniffing guards for the panel's pages (the proxied API sets its own). The live view
  // of the shared browser is framed by the panel itself, so frames stay allowed on the same origin.
  async headers() {
    return [
      {
        source: "/:path*",
        headers: [
          { key: "X-Frame-Options", value: "SAMEORIGIN" },
          { key: "Content-Security-Policy", value: "frame-ancestors 'self'" },
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
        ],
      },
    ];
  },
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${apiProxyTarget}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
