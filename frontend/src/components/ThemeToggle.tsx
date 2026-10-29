import { useEffect, useState } from "react";

type Theme = "dark" | "light";

function initialTheme(): Theme {
  return document.documentElement.dataset.theme === "light" ? "light" : "dark";
}

export function ThemeToggle() {
  const [theme, setTheme] = useState<Theme>(initialTheme);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    try {
      localStorage.setItem("ytd-theme", theme);
    } catch {
      // Theme still applies for this page when storage is unavailable.
    }
  }, [theme]);

  const nextTheme = theme === "dark" ? "light" : "dark";

  return (
    <button
      type="button"
      onClick={() => setTheme(nextTheme)}
      aria-label={`Switch to ${nextTheme} theme`}
      title={`Switch to ${nextTheme} theme`}
      className="inline-flex h-10 w-10 items-center justify-center rounded border border-border bg-transparent text-muted transition-colors hover:border-accent hover:text-text"
    >
      {theme === "dark" ? (
        <svg
          aria-hidden="true"
          width="18"
          height="18"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.8"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <circle cx="12" cy="12" r="4.2" />
          <path d="M12 2.2v2.1M12 19.7v2.1M4.1 4.1l1.5 1.5M18.4 18.4l1.5 1.5M2.2 12h2.1M19.7 12h2.1M4.1 19.9l1.5-1.5M18.4 5.6l1.5-1.5" />
        </svg>
      ) : (
        <svg
          aria-hidden="true"
          width="18"
          height="18"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.8"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <path d="M20.4 14.2A8.5 8.5 0 0 1 9.8 3.6 8.6 8.6 0 1 0 20.4 14.2Z" />
        </svg>
      )}
    </button>
  );
}
