/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{vue,js,jsx,ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: '#4F46E5',
        secondary: '#10B981',
        danger: '#EF4444',
        warning: '#F59E0B',
        info: '#3B82F6'
      },
      fontFamily: {
        sans: ['system-ui', 'sans-serif']
      },
      boxShadow: {
        card: '0 1px 3px rgba(0, 0, 0, 0.1)'
      }
    }
  },
  plugins: []
}
