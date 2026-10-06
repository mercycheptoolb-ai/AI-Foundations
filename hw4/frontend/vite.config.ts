import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// FastAPI backend (backend/main.py), started with: uvicorn main:app --reload --port 8000
// Override with BACKEND_URL=http://127.0.0.1:<port> if 8000 is busy.
const backend = process.env.BACKEND_URL ?? 'http://127.0.0.1:8000'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  // 5180 so it doesn't clash with other course projects on Vite's default 5173.
  server: {
    port: 5180,
    strictPort: true,
    // Forward API and image requests to the backend.
    proxy: {
      '/api': backend,
      '/images': backend,
    },
  },
})
