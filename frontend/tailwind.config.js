/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        'primary': '#0f1419',
        'secondary': '#1a1f2e',
        'card': '#242b3d',
        'text-primary': '#e8eaed',
        'text-secondary': '#9aa0a6',
        'accent': '#4c9aff',
        'accent-hover': '#3a7dd6',
        'success': '#36b37e',
        'error': '#ff5630',
        'border': '#2d3748',
      },
    },
  },
  plugins: [],
};
