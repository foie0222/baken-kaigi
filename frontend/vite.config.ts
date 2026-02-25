import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': {
        target: 'https://ryzl2uhi94.execute-api.ap-northeast-1.amazonaws.com/prod',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
        headers: {
          'x-api-key': 'I1aD1js0dZ9QjkCTTVyxV9HIKcVl8qql9JZmcvk9',
        },
      },
    },
  },
})
