"use client";

import { useEffect, useState } from "react";

type ThemeMode = "dark" | "light";

export function ThemeToggle() {
  const [theme, setTheme] = useState<ThemeMode>("light");

  useEffect(() => {
    const saved = (typeof window !== "undefined" ? window.localStorage.getItem("cyberwitcher-theme") : "") as ThemeMode | null;
    const initial: ThemeMode = saved === "dark" ? "dark" : "light";
    setTheme(initial);
    document.documentElement.setAttribute("data-theme", initial);
  }, []);

  const toggle = () => {
    const next: ThemeMode = theme === "dark" ? "light" : "dark";
    setTheme(next);
    document.documentElement.setAttribute("data-theme", next);
    window.localStorage.setItem("cyberwitcher-theme", next);
  };

  return (
    <button
      type="button"
      onClick={toggle}
      className="rounded-2xl border border-slate-200 bg-white px-3 py-2 text-xs font-medium text-[#110B0A] shadow-sm hover:border-[#F76C45]"
      title="Toggle light/dark mode"
    >
      {theme === "dark" ? "Light Mode" : "Dark Mode"}
    </button>
  );
}
