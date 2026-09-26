/* global process */
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    // Respect an externally assigned port (falls back to Vite's default 5173)
    port: process.env.PORT ? Number(process.env.PORT) : 5173,
  },
})
