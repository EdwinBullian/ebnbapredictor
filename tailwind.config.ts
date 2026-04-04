import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        tv: {
          bg: "#131722",
          "bg-secondary": "#1e222d",
          "bg-tertiary": "#2a2e39",
          text: "#d1d4dc",
          "text-secondary": "#787b86",
          border: "#363a45",
          green: "#26a69a",
          "green-bg": "#1b2a1b",
          red: "#ef5350",
          "red-bg": "#2a1b1b",
          blue: "#2962ff",
          "blue-hover": "#1e53e5",
        },
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "Consolas", "monospace"],
      },
    },
  },
  plugins: [],
};

export default config;
