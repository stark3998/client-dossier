/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        'bg-primary':    'rgb(var(--color-bg-primary) / <alpha-value>)',
        'bg-secondary':  'rgb(var(--color-bg-secondary) / <alpha-value>)',
        'bg-panel':      'rgb(var(--color-bg-panel) / <alpha-value>)',
        'bg-hover':      'rgb(var(--color-bg-hover) / <alpha-value>)',
        'border-default':'rgb(var(--color-border) / <alpha-value>)',
        accent:          'rgb(var(--color-accent) / <alpha-value>)',
        'accent-bright': 'rgb(var(--color-accent-bright) / <alpha-value>)',
        'accent-blue':   'rgb(var(--color-accent-blue) / <alpha-value>)',
        'text-primary':  'rgb(var(--color-text-primary) / <alpha-value>)',
        'text-secondary':'rgb(var(--color-text-secondary) / <alpha-value>)',
        'text-muted':    'rgb(var(--color-text-muted) / <alpha-value>)',
        'status-green': '#22c55e',
        'status-amber': '#f59e0b',
        'status-red':   '#ef4444',
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
      boxShadow: {
        'card':       '0 1px 3px 0 rgb(0 0 0/0.10), 0 1px 2px -1px rgb(0 0 0/0.06)',
        'card-hover': '0 4px 12px 0 rgb(0 0 0/0.12), 0 2px 4px -1px rgb(0 0 0/0.06)',
        'panel':      '0 8px 24px 0 rgb(0 0 0/0.08)',
      },
      transitionProperty: {
        elevation: 'box-shadow, transform',
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
        'panel-expand': {
          '0%': { opacity: '0', transform: 'translateY(-4px) scaleY(0.97)' },
          '100%': { opacity: '1', transform: 'translateY(0) scaleY(1)' },
        },
        'press': {
          '0%':   { transform: 'scale(1)' },
          '50%':  { transform: 'scale(0.96)' },
          '100%': { transform: 'scale(1)' },
        },
      },
      animation: {
        'slide-in':      'slide-in 200ms ease-out',
        'fade-in':       'fade-in 200ms ease-out',
        'slide-in-right':'slide-in-right 200ms ease-out',
        'slide-up':      'slide-up 200ms ease-out',
        'panel-expand':  'panel-expand 200ms cubic-bezier(0.4, 0, 0.2, 1)',
        'press':         'press 150ms ease-out',
      },
    },
  },
  plugins: [],
};
