import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  // Base URL for GitHub Pages deployment
  // Note: GitHub Pages serves from dashboards2/ (not dashboards2/dist/)
  // because peaceiris/actions-gh-pages copies dist/* to dashboards2/
  base: '/immo-bot-luxembourg/dashboards2/',
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
