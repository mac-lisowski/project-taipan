import path from "node:path";
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  // Pin the trace root: if a root package.json/pnpm-lock.yaml appears,
  // standalone would nest server.js under apps/web/ and break the image.
  outputFileTracingRoot: path.resolve(import.meta.dirname),
  async headers() {
    return [
      {
        // Share links carry a private transcript; keep them out of
        // indexes at the header level too (page also sets robots meta).
        source: "/share/:path*",
        headers: [{ key: "X-Robots-Tag", value: "noindex" }],
      },
      {
        // Same transcript served as JSON; index neither surface.
        source: "/api/public/:path*",
        headers: [{ key: "X-Robots-Tag", value: "noindex" }],
      },
    ];
  },
};

export default nextConfig;
