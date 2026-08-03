import { defineConfig } from 'vite'
import path from 'path'

/**
 * The ARC HUD is one canvas and two hand-written modules — no framework, no 3D
 * library. The Three.js/R3F chunking that used to live here described the old
 * React interface and now only produced four empty chunks, so it is gone. The
 * whole interface ships in ~21 kB.
 */
export default defineConfig({
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
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
