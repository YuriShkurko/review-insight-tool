import path from "node:path";
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Required for Dockerfile.prod: minimal `node server.js` runner (reliable PORT + Railway proxy).
  output: "standalone",
  // Pin Turbopack's workspace root to this directory. Without this, Next 16
  // detects the repo-root package-lock.json (which only carries an `aws`
  // helper dep) and tries to resolve frontend modules like `tailwindcss`
  // from there, breaking dev compilation.
  turbopack: {
    root: path.resolve(__dirname),
  },
};

export default nextConfig;
