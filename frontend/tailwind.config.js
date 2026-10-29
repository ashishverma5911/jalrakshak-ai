/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        navy: {
          950: '#040d14',
          900: '#071520',
          850: '#0a1d2c',
          800: '#0e2638',
          750: '#133045',
          700: '#193d56',
          600: '#235272',
          500: '#327099',
        },
        flood: {
          cyan: '#00e5ff',
          blue: '#0091ea',
          deep: '#0b3c61',
          glow: 'rgba(0, 229, 255, 0.35)',
        },
        drought: {
          amber: '#f59e0b',
          orange: '#ea580c',
          gold: '#fbbf24',
          brown: '#78350f',
          glow: 'rgba(245, 158, 11, 0.35)',
        },
        risk: {
          high: '#ef4444',
          moderate: '#f59e0b',
          low: '#10b981',
          nodata: '#334155',
        }
      },
      boxShadow: {
        'glow-cyan': '0 0 20px -3px rgba(0, 229, 255, 0.35), 0 0 8px rgba(0, 229, 255, 0.2)',
        'glow-amber': '0 0 20px -3px rgba(245, 158, 11, 0.35), 0 0 8px rgba(245, 158, 11, 0.2)',
        'card-3d': '0 10px 30px -10px rgba(0, 0, 0, 0.5), 0 0 0 1px rgba(255, 255, 255, 0.07)',
        'card-hover': '0 18px 40px -10px rgba(0, 0, 0, 0.65), 0 0 0 1px rgba(255, 255, 255, 0.15)',
        'sidebar-nav': '0 4px 14px 0 rgba(0, 118, 255, 0.39)',
      },
      fontFamily: {
        sans: ['Plus Jakarta Sans', 'Inter', 'system-ui', '-apple-system', 'sans-serif'],
      }
    },
  },
  plugins: [],
}
