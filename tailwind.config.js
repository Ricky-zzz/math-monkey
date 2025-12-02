/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./game/templates/game/*.html", // Scans your HTML
    "./game/**/*.js", // Scans your JS (if any)
  ],
  theme: {
    extend: {},
  },
  plugins: [require("daisyui")],
};
