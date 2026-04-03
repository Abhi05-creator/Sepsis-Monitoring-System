/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        'icu-dark':     '#0a0f1e',
        'icu-card':     '#111827',
        'icu-border':   '#1f2937',
        'vital-green':  '#22c55e',
        'vital-yellow': '#eab308',
        'vital-red':    '#ef4444',
        'vital-blue':   '#3b82f6',
      },
    },
  },
  plugins: [],
};
