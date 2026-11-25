/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        navy: {
          950: '#070B14',
          900: '#0C1222',
          800: '#131C31',
          700: '#1C2942',
        },
        brand: {
          violet: '#7C3AED',
          blue: '#3B82F6',
        },
      },
    },
  },
  plugins: [],
};
