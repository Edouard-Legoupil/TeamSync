import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// During local development, proxy API calls to the FastAPI backend so the SPA
// and API share one origin (avoids CORS/cookie friction).
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
