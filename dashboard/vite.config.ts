import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// The API this dev server talks to. Not configurable on purpose: development
// runs both on the same machine, and a wrong value here fails as a confusing
// 404 rather than as a config error.
const API = 'http://127.0.0.1:8000'

// Every path prefix the dashboard needs the API for, so the dev server forwards
// them instead of answering with its own index.html.
//
// The server nests the JSON API under `/api` — `v1` for the machine-facing
// contract, `auth` and `admin` for the dashboard's own endpoints, and the
// unversioned `health` and `me` — so the single `api` key covers all of them and
// a new endpoint under any of them is forwarded without touching this file.
//
// `pages` is the other half of the story: a *published* landing page is served
// by the API at `/pages/{public_id}`, and the dashboard builds that link from
// `window.location.origin`. Without this entry the link it shows would point at
// the dev server, which only serves under `/dashboard/` and would refuse it.
//
// It cannot swallow the app's own Pages screen: that is `/dashboard/pages`, and
// a proxy key matches from the root, so `/pages` never sees it.
const API_PREFIXES = ['api', 'pages'] as const

// Where the dashboard is served from. This has to agree with `DASHBOARD_BASE` in
// `src/server.py` and with `basename` in `src/main.tsx`: it is what makes the
// built asset URLs `/dashboard/assets/...` instead of `/assets/...`, which is
// what the server mounts and what keeps a future public site from needing the
// same asset paths.
const BASE = '/dashboard/'

const proxy = Object.fromEntries(
  API_PREFIXES.map((prefix) => [`/${prefix}`, { target: API, changeOrigin: false }]),
)

export default defineConfig({
  // Read by the router and the asset URLs, so the dashboard only ever works
  // from its own prefix.
  base: BASE,
  // Files served as-is, referenced by their own path rather than imported.
  //
  // This is where `favicon.ico` and `logo.png` live. Vite's default is
  // `public/`, which this project does not have, so without this the folder
  // would be read by nothing and the two files would never reach the build.
  //
  // Vite copies a publicDir's *contents* to the root of `outDir`, so these land
  // at `dist/favicon.ico` and `dist/logo.png` — served as `/dashboard/favicon.ico`
  // and `/dashboard/logo.png`. Not `/dashboard/assets/...`: `assets` is the
  // publicDir itself, not a folder inside it.
  //
  // Their names stay stable across builds, which is what a favicon wants —
  // browsers cache those hard, and a hashed name would change on every build.
  publicDir: 'assets',
  plugins: [react()],
  build: {
    outDir: 'dist',
    emptyOutDir: true,
    // The API serves <base>assets, so the bundle directory has to be called
    // assets rather than Vite's default `static`.
    assetsDir: 'assets',
    sourcemap: false,
  },
  server: {
    port: 5173,
    proxy,
  },
})
