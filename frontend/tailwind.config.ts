import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        panel: "#09141f",
        panelAlt: "#0f2030",
        ink: "#d9eef7",
        accent: "#17c964",
        warning: "#f5a524",
        danger: "#f31260"
      },
      boxShadow: {
        neon: "0 0 30px rgba(23, 201, 100, 0.2)"
      }
    }
  },
  plugins: [],
};

export default config;
