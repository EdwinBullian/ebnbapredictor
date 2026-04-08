import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        code: ["Fira Code", "monospace"],
        ui: ["Fira Sans", "sans-serif"],
      },
    },
  },
  plugins: [],
};

export default config;
