/** @type {import('tailwindcss').Config} */
export default {
  darkMode: "class",
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        canvas: "#f4f4f3",
        ink: "#3a3a3a",
        muted: "#9a9a9a",
        line: "#c4c4c4",
        // Dark mode palette — duller, lower contrast
        "dark-bg":     "#18181b",   // near-black, not pure
        "dark-ink":    "#c4c4c0",   // warm off-white, not bright
        "dark-muted":  "#6b6b68",   // mid-grey, clearly secondary
        "dark-line":   "#3a3a38",   // subtle border, barely visible
      },
      fontFamily: {
        sans: ["Dosis", "system-ui", "sans-serif"],
        mono: ["DynaPuff", "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [],
};
