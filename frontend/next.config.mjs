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
    // Remove any rewrites or redirects related to API proxying
    // For example, if you had something like:
    // async rewrites() {
    //   return [
    //     {
    //       source: '/api/proxy/:path*',
    //       destination: 'https://backend-url/:path*',
    //     },
    //   ];
    // },
    productionBrowserSourceMaps: true,
  };
  
  export default nextConfig;