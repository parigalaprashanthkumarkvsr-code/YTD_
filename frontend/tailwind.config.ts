import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: "var(--bg)",
        surface: "var(--surface)",
        "surface-2": "var(--surface-2)",
        border: "var(--border)",
        text: "var(--text)",
        muted: "var(--text-muted)",
        accent: "var(--accent)",
        "accent-hover": "var(--accent-hover)",
        "accent-press": "var(--accent-press)",
        "on-accent": "var(--on-accent)",
        success: "var(--success)",
        error: "var(--error)",
        paper: "var(--paper)",
      },
      fontFamily: {
        mono: [
          '"JetBrains Mono"',
          '"IBM Plex Mono"',
          "ui-monospace",
          "SFMono-Regular",
          "Menlo",
          "Consolas",
          "monospace",
        ],
        sans: ['"JetBrains Mono"', "ui-monospace", "monospace"],
      },
      borderRadius: {
        DEFAULT: "6px",
      },
      fontSize: {
        label: ["13px", { lineHeight: "1.5" }],
        h1: ["24px", { lineHeight: "1.3" }],
      },
      maxWidth: {
        content: "720px",
      },
    },
  },
  plugins: [],
} satisfies Config;
