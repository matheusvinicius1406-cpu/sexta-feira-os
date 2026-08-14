import { defineConfig } from 'vite'

/**
 * The ARC HUD is one canvas and two hand-written modules — no framework, no 3D
 * library. The whole interface ships in ~21 kB.
 *
 * (The React/Three.js interface that used to live here — src/widgets, the 3D
 * scene, zustand — was removed: nothing referenced its entry point since the
 * ARC took over index.html. History has it if it ever comes back.)
 */
export default defineConfig({
  build: {
    target: 'esnext',
    minify: 'esbuild',
  },
  server: {
    port: 3000,
    // The kernel is same-origin from the browser's point of view, so it never
    // has to deal with CORS — the dev server forwards /api to the backend.
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
})
