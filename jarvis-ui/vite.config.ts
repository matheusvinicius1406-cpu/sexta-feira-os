import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  build: {
    target: 'esnext',
    minify: 'esbuild',
    rollupOptions: {
      output: {
        manualChunks: {
          // Core 3D — largest bundle
          three: ['three'],
          // R3F + postprocessing
          r3f: ['@react-three/fiber', '@react-three/postprocessing', 'postprocessing'],
          // Animation
          animation: ['framer-motion'],
          // React + state management (stable, rarely changes)
          vendor: ['react', 'react-dom', 'zustand'],
        },
      },
    },
    // Prevent chunk size warning for Three.js (it's always large)
    chunkSizeWarningLimit: 1000,
  },
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
})
