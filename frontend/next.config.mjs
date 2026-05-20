/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  reactStrictMode: true,
  skipTrailingSlashRedirect: true,
  async rewrites() {
    const backend = process.env.NODE_ENV === 'production'
      ? 'http://backend:8000'
      : 'http://localhost:8000';
    return {
      beforeFiles: [
        // 在 Next.js 文件系统路由之前拦截所有 /api 请求，避免尾部斜杠重定向
        { source: '/api/:path*', destination: `${backend}/api/:path*` },
        { source: '/api/:path*/', destination: `${backend}/api/:path*/` },
      ],
    };
  },
};

export default nextConfig;
