import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'

const backendPort = process.env.VITE_BACKEND_PORT || process.env.PORT || '10000'
const backendTarget = process.env.BACKEND_URL || `http://localhost:${backendPort}`

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: backendTarget,
        changeOrigin: true,
      },
    },
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['src/test/setup.ts'],
  },
})
