import { Link, useNavigate } from "react-router-dom";

import { useAuth } from "../context/useAuth";
import { useTheme } from "../hooks/useTheme";

function Logo() {
  return (
    <svg viewBox="0 0 64 64" className="h-8 w-8" aria-hidden="true">
      <rect width="64" height="64" rx="14" fill="#4f46e5" />
      <g stroke="#fff" strokeWidth="3" strokeLinecap="round">
        <line x1="20" y1="22" x2="44" y2="20" />
        <line x1="20" y1="22" x2="30" y2="44" />
        <line x1="44" y1="20" x2="30" y2="44" />
      </g>
      <circle cx="20" cy="22" r="6" fill="#fff" />
      <circle cx="44" cy="20" r="6" fill="#fbbf24" />
      <circle cx="30" cy="44" r="6" fill="#34d399" />
    </svg>
  );
}

export default function Header() {
  const { theme, toggleTheme } = useTheme();
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  function handleLogout() {
    logout();
    navigate("/login");
  }

  return (
    <header className="sticky top-0 z-20 border-b border-slate-200/80 bg-white/80 backdrop-blur dark:border-slate-800 dark:bg-slate-950/80">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3">
        <Link to="/" className="flex items-center gap-2.5">
          <Logo />
          <span className="font-display text-xl font-semibold text-slate-900 dark:text-white">
            Research Mate
          </span>
        </Link>

        <div className="flex items-center gap-3">
          {user && (
            <span className="hidden text-sm text-slate-400 sm:inline dark:text-slate-500">{user.email}</span>
          )}
          <button onClick={toggleTheme} aria-label="Toggle dark mode" className="btn-ghost h-9 w-9 !p-0">
            {theme === "dark" ? "☾" : "☀"}
          </button>
          {user && (
            <button onClick={handleLogout} className="btn-ghost">
              Log out
            </button>
          )}
        </div>
      </div>
    </header>
  );
}
