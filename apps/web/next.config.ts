import path from "node:path";
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  // Pin the trace root: if a root package.json/pnpm-lock.yaml appears,
  // standalone would nest server.js under apps/web/ and break the image.
  outputFileTracingRoot: path.resolve(import.meta.dirname),
};

export default nextConfig;
