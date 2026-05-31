import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        bg: "#0b0f19",
        surface: "#141927",
        border: "#1e2a3a",
        accent: "#3b82f6",
        muted: "#64748b",
      },
    },
  },
  plugins: [],
};

export default config;
