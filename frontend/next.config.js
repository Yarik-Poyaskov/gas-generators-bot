/** @type {import('next').NextConfig} */
const nextConfig = {
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: 'http://localhost:7895/api/:path*', // Добавляем /api в место назначения
      },
    ];
  },
};

module.exports = nextConfig;
