"use client";

import Link from "next/link";
import { useAuth } from "@/lib/auth";
import { useTheme } from "@/lib/theme";

function ThemeToggle() {
  const { theme, setTheme } = useTheme();

  function cycle() {
    if (theme === "light") setTheme("dark");
    else if (theme === "dark") setTheme("system");
    else setTheme("light");
  }

  return (
    <button
      onClick={cycle}
      aria-label="Toggle theme"
      title={`Theme: ${theme}`}
      className="text-text-muted hover:text-text-primary transition-colors p-1 rounded-md hover:bg-surface-elevated"
    >
      {theme === "dark" ? (
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
        </svg>
      ) : theme === "light" ? (
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <circle cx="12" cy="12" r="5" />
          <line x1="12" y1="1" x2="12" y2="3" />
          <line x1="12" y1="21" x2="12" y2="23" />
          <line x1="4.22" y1="4.22" x2="5.64" y2="5.64" />
          <line x1="18.36" y1="18.36" x2="19.78" y2="19.78" />
          <line x1="1" y1="12" x2="3" y2="12" />
          <line x1="21" y1="12" x2="23" y2="12" />
          <line x1="4.22" y1="19.78" x2="5.64" y2="18.36" />
          <line x1="18.36" y1="5.64" x2="19.78" y2="4.22" />
        </svg>
      ) : (
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <circle cx="12" cy="12" r="4" />
          <path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41" />
          <path d="M12 8a4 4 0 0 1 0 8" strokeDasharray="2 2" />
        </svg>
      )}
    </button>
  );
}

export default function NavBar() {
  const { user, logout, isLoading } = useAuth();

  if (isLoading || !user) return null;

  return (
    <nav className="bg-surface-card border-b border-border">
      <div className="max-w-screen-xl mx-auto px-4 h-12 flex items-center justify-between">
        <Link href="/businesses" className="font-semibold text-base text-text-primary">
          Review Insight
        </Link>
        <div className="flex items-center gap-3 text-sm">
          <ThemeToggle />
          <span className="text-text-muted hidden sm:block">{user.email}</span>
          <button onClick={logout} className="text-red-500 hover:text-red-600 font-medium transition-colors">
            Logout
          </button>
        </div>
      </div>
    </nav>
  );
}
