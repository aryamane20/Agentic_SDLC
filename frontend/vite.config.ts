import { fileURLToPath, URL } from "node:url"
import react from "@vitejs/plugin-react"
import { defineConfig } from "vite"

const srcDir = fileURLToPath(new URL("./src", import.meta.url))

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": srcDir,
    },
  },
  server: {
    // Avoid clashing with other local Vite apps that use the default :5173
    port: 5180,
    strictPort: false,
    proxy: {
      "/sessions": { target: "http://127.0.0.1:8000", changeOrigin: true },
      "/reports": { target: "http://127.0.0.1:8000", changeOrigin: true },
      "/gates": { target: "http://127.0.0.1:8000", changeOrigin: true },
      "/health": { target: "http://127.0.0.1:8000", changeOrigin: true },
    },
  },
})
