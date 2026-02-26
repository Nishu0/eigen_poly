/** @type {import('next').NextConfig} */
const nextConfig = {
  transpilePackages: ["@eigenpoly/ui"],
  images: {
    unoptimized: true,
  },
};

export default nextConfig;
