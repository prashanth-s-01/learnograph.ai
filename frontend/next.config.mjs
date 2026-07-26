/** @type {import('next').NextConfig} */
const nextConfig = {
  // Proxy /api/* → backend service so the frontend never hard-codes the backend URL.
  // In development set BACKEND_URL=http://localhost:8000 in frontend/.env.local.
  // In production Render sets BACKEND_URL automatically from the backend service URL.
  async rewrites() {
    const raw = process.env.BACKEND_URL ?? "http://localhost:8000";
    // Render sets BACKEND_URL to the bare host (e.g. "learnograph-backend.onrender.com").
    // Locally it is the full URL. Normalise to always have a scheme.
    const backendUrl = raw.startsWith("http") ? raw : `https://${raw}`;
    return [
      {
        source: "/api/:path*",
        destination: `${backendUrl}/:path*`,
      },
    ];
  },
};

export default nextConfig;
