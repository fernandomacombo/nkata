/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        nk: {
          red: "#c8102e",
          redDark: "#9f0d24",
          black: "#070707",
          ink: "#111111",
          cream: "#f8f6f3",
          gold: "#d7b46a",
          muted: "#6f6f6f"
        }
      },
      boxShadow: {
        premium: "0 28px 90px rgba(0,0,0,0.22)",
        soft: "0 18px 60px rgba(0,0,0,0.10)"
      },
      borderRadius: {
        app: "28px",
        card: "34px"
      },
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui", "Segoe UI", "sans-serif"]
      }
    }
  },
  plugins: []
};
