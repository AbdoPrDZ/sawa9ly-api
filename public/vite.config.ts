import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// The API this dev server talks to. Not configurable on purpose: development
// runs both on the same machine, and a wrong value here fails as a confusing
// 404 rather than as a config error.
const API = 'http://127.0.0.1:8000'

// Every API path prefix the dashboard can call, so the dev server forwards them
// instead of answering with its own index.html.
//
// `v1` covers the machine-facing contract; `auth` and `admin` are the
// dashboard's own endpoints, which the server mounts unversioned. `health` and
// `me` are unversioned too. Vite matches proxy keys as path prefixes, so
// `v1` also forwards `/v1/auth/...` style paths beneath it.
//
// Versioning also retired the old `/products` collision described in
// "Route collision" below: the API's scrape routes are `/v1/products/{id}` and
// the dashboard page is `/products`, so no prefix can serve both.
const API_PREFIXES = ['v1', 'auth', 'admin', 'health', 'me'] as const

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
