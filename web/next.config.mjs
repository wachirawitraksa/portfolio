const api = process.env.API_INTERNAL_URL ?? "http://localhost:8000";

/** @type {import('next').NextConfig} */
export default {
  output: "standalone",
  // The dev-mode "N" badge sits on top of the activity bar and the ASK Me button.
  devIndicators: false,
  // Dev only: in production Caddy sends /api/* to the API, so the browser's relative /api URLs (photo, CV, ask)
  // work. `npm run dev` has no proxy, so forward them here.
  async rewrites() {
    return process.env.NODE_ENV === "production" ? [] : [{ source: "/api/:path*", destination: `${api}/api/:path*` }];
  },
};
