import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Required for Dockerfile.prod: minimal `node server.js` runner (reliable PORT + Railway proxy).
  output: "standalone",
};

export default nextConfig;
