/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
      animation: {
        'fade-in': 'fadeIn 0.3s ease-out',
        'slide-up': 'slideUp 0.3s ease-out',
        'slide-in': 'slideIn 0.25s ease-out',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideUp: {
          '0%': { opacity: '0', transform: 'translateY(8px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        slideIn: {
          '0%': { opacity: '0', transform: 'translateX(-12px)' },
          '100%': { opacity: '1', transform: 'translateX(0)' },
        },
      },
    },
  },
  plugins: [require('daisyui')],
  daisyui: {
    themes: [
      {
        pablito: {
          "primary": "#818cf8",        // Indigo suave
          "primary-content": "#0f0f1a",
          "secondary": "#a78bfa",      // Violet
          "secondary-content": "#0f0f1a",
          "accent": "#34d399",         // Emerald
          "accent-content": "#0f0f1a",
          "neutral": "#1e1e2e",
          "neutral-content": "#cdd6f4",
          "base-100": "#11111b",       // Fondo principal (muy oscuro)
          "base-200": "#181825",       // Cards/superficies
          "base-300": "#1e1e2e",       // Bordes/separadores
          "base-content": "#cdd6f4",   // Texto principal
          "info": "#89b4fa",
          "info-content": "#0f0f1a",
          "success": "#a6e3a1",
          "success-content": "#0f0f1a",
          "warning": "#f9e2af",
          "warning-content": "#0f0f1a",
          "error": "#f38ba8",
          "error-content": "#0f0f1a",
        },
      },
    ],
  },
}
