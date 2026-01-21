import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api/consultation': {
        target: 'http://localhost:8084',
        changeOrigin: true,
        rewrite: () => '/invocations',
        configure: (proxy) => {
          proxy.on('proxyReq', (proxyReq) => {
            proxyReq.setHeader('Content-Type', 'application/json');
          });
        },
      },
    },
  },
})
