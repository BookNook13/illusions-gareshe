/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#14161A", // page background — warm charcoal, not neutral black
        surface: "#1B1E23", // raised panels, input fields
        parchment: "#E8E3D9", // primary text — warm off-white
        muted: "#8B8D93", // secondary text, timestamps, meta
        hairline: "#2A2E35", // dividers
        brass: "#B08D57", // the single accent: reserved for moments of insight
        "brass-dim": "#8A6F45",
        slate: "#6E8CA0", // second run / comparison color only
      },
      fontFamily: {
        serif: ["var(--font-story)", "Georgia", "serif"],
        sans: ["var(--font-ui)", "system-ui", "sans-serif"],
      },
      maxWidth: {
        reading: "640px",
      },
    },
  },
  plugins: [],
};
