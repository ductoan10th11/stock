import path from "node:path"
import tailwindcss from "@tailwindcss/vite"
import react from "@vitejs/plugin-react"
import { defineConfig } from "vitest/config"

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: { alias: { "@": path.resolve(import.meta.dirname, "src") } },
  server: { proxy: { "/api": { target: process.env.API_URL ?? "http://127.0.0.1:8000", timeout: 0, proxyTimeout: 0 } } },
  test: { environment: "node" },
})
