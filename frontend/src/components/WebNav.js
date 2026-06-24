import { Link, useLocation, useNavigate } from "react-router-dom";
import { Sparkles, Menu, X, User as UserIcon, LogOut, Shield } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { useState } from "react";

const NAV_LINKS = [
  { to: "/dashboard", label: "Dashboard", auth: true },
  { to: "/paths", label: "Paths", auth: true },
  { to: "/tutor", label: "AI Tutor", auth: true },
  { to: "/models", label: "Models", auth: true },
];

export default function WebNav() {
  const { user, logout } = useAuth();
  const nav = useNavigate();
  const loc = useLocation();
  const [open, setOpen] = useState(false);
  const [menu, setMenu] = useState(false);

  const tierBadge = user && user.tier !== "free" && (
    <span className="px-2 py-0.5 rounded-full text-[10px] font-black tracking-wider"
      style={{ background: "#FFB000", color: "#000" }}>
      {user.tier.toUpperCase()}
    </span>
  );

  return (
    <header className="asc-glass sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-5 py-3 flex items-center justify-between">
        <Link to="/" className="flex items-center gap-2.5" data-testid="nav-logo">
          <div className="w-7 h-7 rounded-lg flex items-center justify-center" style={{ background: "#FFB000" }}>
            <Sparkles size={15} color="#000" />
          </div>
          <span className="font-black tracking-[0.32em] text-sm">ASCENDRA</span>
        </Link>

        <nav className="hidden md:flex items-center gap-7">
          {NAV_LINKS.filter((l) => !l.auth || user).map((l) => (
            <Link
              key={l.to}
              to={l.to}
              data-testid={`nav-link-${l.to.replace('/', '')}`}
              className={`text-sm font-medium transition ${loc.pathname === l.to ? "text-white" : "text-[var(--asc-text-dim)] hover:text-white"}`}
            >
              {l.label}
            </Link>
          ))}
        </nav>

        <div className="flex items-center gap-3">
          {!user ? (
            <Link to="/login" data-testid="nav-signin-btn" className="text-sm text-[var(--asc-text-dim)] hover:text-white">Sign in</Link>
          ) : (
            <div className="relative">
              {tierBadge}
              <button onClick={() => setMenu((v) => !v)} data-testid="nav-user-menu-btn" className="ml-2 flex items-center gap-2 px-3 py-1.5 rounded-full border border-[var(--asc-border)] hover:border-[var(--asc-border-strong)] transition">
                {user.picture ? (
                  <img src={user.picture} alt="" className="w-6 h-6 rounded-full" />
                ) : (
                  <div className="w-6 h-6 rounded-full grid place-items-center" style={{ background: "#7C3AED" }}>
                    <UserIcon size={13} />
                  </div>
                )}
                <span className="text-sm hidden sm:inline">{(user.name || user.email.split("@")[0]).slice(0, 14)}</span>
              </button>
              {menu && (
                <div className="absolute right-0 top-12 w-56 asc-card p-2 z-50" style={{ background: "#15102B" }}>
                  <Link to="/profile" onClick={() => setMenu(false)} className="flex items-center gap-2 px-3 py-2 rounded-lg hover:bg-[var(--asc-surface-2)]" data-testid="menu-profile"><UserIcon size={14} />Profile</Link>
                  {user.is_admin && (
                    <Link to="/admin" onClick={() => setMenu(false)} className="flex items-center gap-2 px-3 py-2 rounded-lg hover:bg-[var(--asc-surface-2)]" data-testid="menu-admin"><Shield size={14} />Admin</Link>
                  )}
                  <button onClick={() => { logout(); setMenu(false); nav("/"); }} className="w-full text-left flex items-center gap-2 px-3 py-2 rounded-lg hover:bg-[var(--asc-surface-2)] text-[var(--asc-danger)]" data-testid="menu-logout"><LogOut size={14} />Sign out</button>
                </div>
              )}
            </div>
          )}
          <button onClick={() => setOpen((v) => !v)} className="md:hidden p-2" aria-label="Menu">
            {open ? <X size={22} /> : <Menu size={22} />}
          </button>
        </div>
      </div>

      {open && (
        <nav className="md:hidden border-t border-[var(--asc-border)] px-5 py-4 flex flex-col gap-3">
          {NAV_LINKS.filter((l) => !l.auth || user).map((l) => (
            <Link key={l.to} to={l.to} onClick={() => setOpen(false)} className="text-sm text-[var(--asc-text-dim)] hover:text-white py-1">{l.label}</Link>
          ))}
        </nav>
      )}
    </header>
  );
}
