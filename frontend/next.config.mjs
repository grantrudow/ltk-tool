// next.config.mjs
/** @type {import('next').NextConfig} */
const nextConfig = {
    env: {
      API_URL: process.env.API_URL || 'http://localhost:8000',
      NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
    },
    // Add async headers to allow CORS
    async headers() {
      return [
        {
          // Apply these headers to all routes
          source: '/(.*)',
          headers: [
            { key: 'Access-Control-Allow-Credentials', value: 'true' },
            { key: 'Access-Control-Allow-Origin', value: '*' },
            { key: 'Access-Control-Allow-Methods', value: 'GET,DELETE,PATCH,POST,PUT' },
            { key: 'Access-Control-Allow-Headers', value: 'X-CSRF-Token, X-Requested-With, Accept, Accept-Version, Content-Length, Content-MD5, Content-Type, Date, X-Api-Version' },
          ],
        },
      ];
    },
    // Add rewrites for API routes
    async rewrites() {
      const apiUrl = process.env.API_URL || 'http://localhost:8000';
      return [
        // Direct API routes
        {
          source: '/api/direct/download',
          destination: `${apiUrl}/api/download`,
        },
        {
          source: '/api/direct/download/:path*',
          destination: `${apiUrl}/api/download/:path*`,
        },
        // Fallback for any other direct API routes
        {
          source: '/api/direct/:path*',
          destination: `${apiUrl}/api/:path*`,
        },
      ];
    },
  };
  
  export default nextConfig;