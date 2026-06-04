import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: [
          "Inter",
          "-apple-system",
          "BlinkMacSystemFont",
          "Segoe UI",
          "sans-serif",
        ],
      },
      colors: {
        ink: "#0F172A",
        muted: "#64748B",
        soft: "#94A3B8",
        bg: "#F1F5F9",
        line: "#E2E8F0",
        accent: "#2563EB",
        primary: "#1E3A5F",
        ok: "#059669",
        warn: "#D97706",
        danger: "#DC2626",
        chipBlue: "#EFF6FF",
        chipGreen: "#ECFDF5",
        chipAmber: "#FFFBEB",
        chipViolet: "#F5F3FF",
        chipRose: "#FEF2F2",
      },
      boxShadow: {
        card: "0 1px 2px rgba(15,23,42,0.04), 0 1px 1px rgba(15,23,42,0.02)",
        cardHover: "0 4px 16px rgba(37,99,235,0.08)",
      },
    },
  },
  plugins: [],
};
export default config;
