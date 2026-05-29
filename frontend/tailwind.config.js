/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        'bg-primary': '#0d0d0d',
        'bg-secondary': '#161616',
        'bg-panel': '#1a1a1a',
        'bg-hover': '#222222',
        'border-default': '#2a2a2a',
        accent: '#86BC25',
        'accent-bright': '#86EB22',
        'accent-blue': '#00A3E0',
        'text-primary': '#f0f0f0',
        'text-secondary': '#888888',
        'text-muted': '#555555',
        'status-green': '#22c55e',
        'status-amber': '#f59e0b',
        'status-red': '#ef4444',
        'chart-1': '#86BC25',
        'chart-2': '#00A3E0',
        'chart-3': '#f59e0b',
        'chart-4': '#ef4444',
        'chart-5': '#8b5cf6',
      },
      fontFamily: {
        sans: ['DM Sans', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
      borderRadius: {
        sm: '4px',
        md: '8px',
      },
      keyframes: {
        'slide-in': {
          '0%': { opacity: '0', transform: 'translateY(8px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        'fade-in': {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        'slide-in-right': {
          '0%': { transform: 'translateX(100%)' },
          '100%': { transform: 'translateX(0)' },
        },
        'slide-up': {
          '0%': { transform: 'translateY(100%)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' },
        },
      },
      animation: {
        'slide-in': 'slide-in 200ms ease-out',
        'fade-in': 'fade-in 200ms ease-out',
        'slide-in-right': 'slide-in-right 200ms ease-out',
        'slide-up': 'slide-up 200ms ease-out',
      },
    },
  },
  plugins: [],
};
