/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Forward FastAPI's auto-mounted endpoints to the Python function.
  // /api/* is auto-handled by Vercel detecting api/index.py as a serverless function.
  async rewrites() {
    return [
      { source: "/health", destination: "/api/index" },
      { source: "/docs", destination: "/api/index" },
      { source: "/openapi.json", destination: "/api/index" },
    ];
  },
};

module.exports = nextConfig;
