/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,

  images: {
    // Allow images from MinIO (local development) and future CDN origins
    remotePatterns: [
      {
        // Browser-accessible MinIO in local development (via Docker port mapping)
        protocol: "http",
        hostname: "localhost",
        port: "9000",
        pathname: "/**",
      },
      {
        // Docker-internal MinIO hostname (used when Next.js SSR resolves images
        // inside the container network, and for presigned URLs before proxying)
        protocol: "http",
        hostname: "minio",
        port: "9000",
        pathname: "/**",
      },
    ],
  },

  // ---------------------------------------------------------------------------
  // API rewrites
  //
  // These run server-side inside the Next.js container, so destinations must
  // use Docker Compose internal service names (guide-service:8000,
  // expedition-service:8000) — not the host-mapped ports (8002, 8001).
  //
  // Request flow (fresh clone, no .env.local):
  //   Browser  → GET /guides/api/v1/guides (relative, same origin :3000)
  //   Next.js  → rewrites to http://guide-service:8000/api/v1/guides
  //   Response → camelCase-transformed by axios response interceptor
  //
  // Only the /*/api/ prefixes are rewritten so App Router page routes
  // (/guides, /guides/[id], /my-trips, etc.) are handled normally.
  // ---------------------------------------------------------------------------
  async rewrites() {
    return [
      {
        // Guide Service — internal Docker hostname
        source: "/guides/api/:path*",
        destination: "http://guide-service:8000/api/:path*",
      },
      {
        // Expedition Service — internal Docker hostname
        source: "/expeditions/api/:path*",
        destination: "http://expedition-service:8000/api/:path*",
      },
      {
        // Trips API (MCP-1) — /api/v1/trips/* → expedition-service
        source: "/api/v1/trips/:path*",
        destination: "http://expedition-service:8000/api/v1/trips/:path*",
      },
      {
        // My Trips endpoint — /api/v1/users/me/trips → expedition-service
        source: "/api/v1/users/me/trips",
        destination: "http://expedition-service:8000/api/v1/users/me/trips",
      },
      {
        // Feed Service — internal Docker hostname
        source: "/feed/api/:path*",
        destination: "http://feed-service:8000/api/:path*",
      },
      {
        // Community Service — root collection endpoint (trailing slash required
        // by FastAPI to avoid a 307 redirect to http://community-service:8000/…
        // which the browser cannot resolve as an internal Docker hostname).
        source: "/communities/api/v1/communities",
        destination: "http://community-service:8000/api/v1/communities/",
      },
      {
        // Community Service — all other sub-paths (member actions, discussions,
        // join/leave, rules, etc.) — internal Docker hostname.
        source: "/communities/api/:path*",
        destination: "http://community-service:8000/api/:path*",
      },
    ];
  },
};

export default nextConfig;

