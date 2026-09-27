import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// The API this dev server talks to. Not configurable on purpose: development
// runs both on the same machine, and a wrong value here fails as a confusing
// 404 rather than as a config error.
const API = 'http://127.0.0.1:8000'

// Every API path prefix the dashboard can call, so the dev server forwards them
// instead of answering with its own index.html.
//
// `/products` is deliberately absent: the API has `/products/{id}` (the scrape
// endpoints) and the dashboard has its own `/products` page. Vite cannot serve
// both, and the dashboard reads the catalogue through `/catalogue`, so nothing
// needs the API's `/products` from the browser. See "Route collision" below.
const API_PREFIXES = [
  'admin',
  'auth',
  'cart',
  'catalogue',
  'checkout',
  'clients',
  'health',
  'me',
  'orders',
  'trackers',
] as const

const proxy = Object.fromEntries(
  API_PREFIXES.map((prefix) => [`/${prefix}`, { target: API, changeOrigin: false }]),
)

export default defineConfig({
  plugins: [react()],
  build: {
    outDir: 'dist',
    emptyOutDir: true,
    // The API serves /assets, so the bundle directory has to be called assets
    // rather than Vite's default `static`.
    assetsDir: 'assets',
    sourcemap: false,
  },
  server: {
    port: 5173,
    proxy,
  },
})
