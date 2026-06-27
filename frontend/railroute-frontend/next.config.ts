import type { NextConfig } from "next"

const nextConfig: NextConfig = {
  // Allow 127.0.0.1 for WebSocket HMR connections
  allowedDevOrigins: ['127.0.0.1'],
  async rewrites() {
    return [
      {
        source: "/api/v1/:path*",
        destination: "http://127.0.0.1:8000/api/v1/:path*",
      },
    ]
  },
}

export default nextConfig
