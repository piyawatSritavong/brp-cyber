import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        panel: "#FFFFFF",
        panelAlt: "#FFF4EF",
        ink: "#110B0A",
        accent: "#F76C45",
        warning: "#F76C45",
        danger: "#110B0A"
      },
      boxShadow: {
        neon: "0 0 28px rgba(247, 108, 69, 0.18)"
      }
    }
  },
  plugins: [],
};

export default config;
