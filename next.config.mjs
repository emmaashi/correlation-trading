/** @type {import('next').NextConfig} */
const apiBase = process.env.CORRELATION_API_URL || "http://localhost:5050";

const nextConfig = {
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${apiBase}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
