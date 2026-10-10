import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [react()],
  // CORS on the backend only allows this origin, so don't silently hop ports.
  server: { port: 5173, strictPort: true },
})
