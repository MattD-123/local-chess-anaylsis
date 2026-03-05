/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#111827",
        ivory: "#fefce8",
        ember: "#c2410c",
        pine: "#14532d",
        dusk: "#334155"
      },
      fontFamily: {
        heading: ["Merriweather", "Georgia", "serif"],
        body: ["Source Sans 3", "Segoe UI", "sans-serif"],
      },
      boxShadow: {
        panel: "0 12px 30px rgba(15, 23, 42, 0.18)",
      },
      keyframes: {
        pulseSoft: {
          "0%, 100%": { opacity: "0.35", transform: "scale(1)" },
          "50%": { opacity: "0.9", transform: "scale(1.05)" },
        },
        riseIn: {
          "0%": { opacity: "0", transform: "translateY(8px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
      },
      animation: {
        pulseSoft: "pulseSoft 1.4s ease-in-out infinite",
        riseIn: "riseIn 260ms ease-out",
      },
    },
  },
  plugins: [],
};
