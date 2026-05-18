import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        nebula: {
          DEFAULT: "#6d4aff",
          muted: "#f5f3ff",
          glow: "rgba(109, 74, 255, 0.35)",
        },
      },
      borderRadius: {
        xl: "16px",
        "2xl": "20px",
        "3xl": "24px",
      },
      boxShadow: {
        nebula: "0 12px 32px rgba(109, 74, 255, 0.12)",
        card: "0 4px 6px rgba(15, 13, 20, 0.03), 0 12px 32px rgba(109, 74, 255, 0.08)",
      },
      fontFamily: {
        sans: ["var(--font-inter)", "Inter", "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [],
};
export default config;
