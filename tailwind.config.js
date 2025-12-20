/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./templates/**/*.html",
    "./theme/templates/**/*.html",
    "./core/**/*.py",
    "./intelligence/**/*.py",
    "./accounts/**/*.py",
    "./theme/static_src/src/**/*.js",
  ],
  theme: {
    extend: {},
  },
  plugins: [],
}
