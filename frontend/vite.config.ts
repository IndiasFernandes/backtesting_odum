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
        // For local development: proxy to localhost:8000
        // For Docker: use BACKEND_PROXY_URL env var to override (defaults to backend:8000)
        // VITE_API_URL is for browser-side code, not for proxy config
        target: process.env.BACKEND_PROXY_URL || 
                (process.env.DOCKER === 'true' ? 'http://backend:8000' : 'http://localhost:8000'),
        changeOrigin: true,
        secure: false,
      },
    },
  },
})

