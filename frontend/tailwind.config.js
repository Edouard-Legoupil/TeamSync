/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        //Blue — primary action color.
        primary: {
          50: '#e9f4fb',
          100: '#d3e8f7',
          200: '#a6d1ef',
          300: '#74b7e4',
          400: '#3d96d2',
          500: '#1b7fc0',
          600: '#0072BC',
          700: '#005b96',
          800: '#004a7a',
          900: '#00395c',
        },
        // Navy — headings & dark text.
        navy: {
          50: '#eef2f7',
          100: '#d6dfeb',
          200: '#aabdd4',
          300: '#7d9ab8',
          400: '#4a7296',
          500: '#2a5680',
          600: '#18375F',
          700: '#142f52',
          800: '#102844',
          900: '#0b1d33',
        },
        success: {
          DEFAULT: '#00B398',
          100: '#c8f5ef',
          800: '#0a7663',
        },
        warning: {
          DEFAULT: '#FAEB00',
          100: '#fdf9c9',
          800: '#8a7d00',
        },
        danger: {
          DEFAULT: '#EF4A60',
          100: '#fde0e4',
          700: '#c3273e',
        },
        muted: '#666666',
        line: '#E6E6E6',
        canvas: '#F5F5F5',
      },
      fontFamily: {
        sans: ['Lato', 'Arial', 'Helvetica', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
