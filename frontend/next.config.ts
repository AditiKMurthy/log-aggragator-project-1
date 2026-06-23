import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  allowedDevOrigins: ["172.17.64.1"],
  async redirects() {
    return [
      {
        source: "/logs",
        destination: "/",
        permanent: true,
      },
    ];
  },
};

export default nextConfig;
