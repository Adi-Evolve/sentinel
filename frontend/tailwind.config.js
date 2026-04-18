/** @type {import('tailwindcss').Config} */
export default {
  darkMode: ["class"],
  content: ["./index.html", "./src/**/*.{js,jsx,ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ['"Inter"', "ui-sans-serif", "system-ui", "sans-serif"],
        display: ['"Outfit"', "ui-sans-serif", "system-ui", "sans-serif"],
        mono: ['"Geist Mono"', "ui-monospace", "monospace"],
      },
      colors: {
        background: '#030712', // slate-950
        surface: 'rgba(15, 23, 42, 0.6)', 
        surfaceStrong: '#0f172a',
        border: 'rgba(255,255,255,0.08)',
        accent: {
          DEFAULT: '#38bdf8', // custom cyan/blue
          soft: 'rgba(56, 189, 248, 0.1)',
        },
        critical: '#ef4444',
        warning: '#f59e0b',
      }
    },
  },
  plugins: [],
};
