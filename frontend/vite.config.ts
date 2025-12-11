import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    host: '0.0.0.0',
    port: 5173,
    watch: {
      usePolling: true,
    },
    proxy: {
      '/api': {
        // For Docker: use backend service name (when BACKEND_PROXY_URL is set or in Docker)
        // For local development: use 127.0.0.1:8000 (IPv4, not localhost to avoid IPv6 issues)
        // Can override with BACKEND_PROXY_URL env var
        target: process.env.BACKEND_PROXY_URL || 'http://backend:8000',
        changeOrigin: true,
        secure: false,
        // Additional configuration to handle errors
        configure: (proxy, _options) => {
          proxy.on('error', (err, req, res) => {
            console.error('Proxy error:', err.message);
          });
        },
      },
    },
  },
})

