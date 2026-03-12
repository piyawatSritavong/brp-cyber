"use client";

import { useEffect, useState } from "react";

type ThemeMode = "dark" | "light";

export function ThemeToggle() {
  const [theme, setTheme] = useState<ThemeMode>("dark");

  useEffect(() => {
    const saved = (typeof window !== "undefined" ? window.localStorage.getItem("brp-theme") : "") as ThemeMode | null;
    const initial: ThemeMode = saved === "light" ? "light" : "dark";
    setTheme(initial);
    document.documentElement.setAttribute("data-theme", initial);
  }, []);

  const toggle = () => {
    const next: ThemeMode = theme === "dark" ? "light" : "dark";
    setTheme(next);
    document.documentElement.setAttribute("data-theme", next);
    window.localStorage.setItem("brp-theme", next);
  };

  return (
    <button
      type="button"
      onClick={toggle}
      className="rounded-md border border-slate-700 px-3 py-1.5 text-xs text-slate-200 hover:border-slate-500"
      title="Toggle light/dark mode"
    >
      {theme === "dark" ? "Light Mode" : "Dark Mode"}
    </button>
  );
}

