/** @type {import('next').NextConfig} */
const nextConfig = {
    output: 'standalone',
    typescript: {
        // Allow production builds to successfully complete even if your project has type errors
        ignoreBuildErrors: true,
    },
    eslint: {
        // Allow production builds to successfully complete even if your project has ESLint errors
        ignoreDuringBuilds: true,
    },
    productionBrowserSourceMaps: process.env.ENABLE_SOURCE_MAPS === 'true',
    headers() {
        const headers = [
            {
                source: '/:path*',
                headers: ENGINE_HEADERS,
            },
            {
                source: '/static/:path*',
                headers: ENGINE_HEADERS.concat({
                    key: 'Cache-Control',
                    value: 'public, max-age=2592000, immutable',
                }),
            },
        ];

        return headers;
    },
};

const ENGINE_HEADERS = [
    {
        key: 'Cross-Origin-Embedder-Policy',
        value: 'require-corp',
    },
    {
        key: 'Cross-Origin-Opener-Policy',
        value: 'same-origin',
    },
];

export default nextConfig;
