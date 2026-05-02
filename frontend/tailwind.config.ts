import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        cosmos: {
          bg: "#0a0a1a",
          surface: "#12122a",
          card: "#1a1a3a",
          border: "#2a2a4a",
          nebula: "#6b5ce7",
          gold: "#f0c040",
          shard: "#4a9eff",
          amber: "#ef9f27",
          danger: "#ff4757",
          success: "#2ed573",
          text: "#e0e0f0",
          muted: "#8887a8",
        },
      },
      fontFamily: {
        display: ['"Segoe UI"', "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [],
};

export default config;
