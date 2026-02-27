import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  // Base URL for GitHub Pages deployment
  // Note: GitHub Pages serves from repo root, files are at dashboards2/dist/
  base: '/immo-bot-luxembourg/dashboards2/dist/',
  server: {
    port: 5173,
    host: true
  },
  build: {
    outDir: 'dist',
    minify: 'terser',
    terserOptions: {
      compress: {
        drop_console: true
      }
    },
    rollupOptions: {
      output: {
        manualChunks: {
          'pinia': ['pinia'],
          'leaflet': ['leaflet']
        }
      }
    }
  }
})
