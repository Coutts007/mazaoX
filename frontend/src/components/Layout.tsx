import { useEffect, useRef, useState } from "react";
import { Link, NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { api } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import type { Role } from "../api/types";

interface NavItem {
  to: string;
  label: string;
  icon: string;
  end?: boolean;
}

function navFor(role: Role | null): NavItem[] {
  if (role === "farmer")
    return [
      { to: "/farm", label: "Farm", icon: "🌾", end: true },
      { to: "/farm/listings", label: "Listings", icon: "🧺" },
      { to: "/farm/orders", label: "Orders", icon: "🧾" },
      { to: "/farm/demand", label: "Demand", icon: "📣" },
    ];
  if (role === "admin")
    return [
      { to: "/admin", label: "Overview", icon: "📊", end: true },
      { to: "/admin/users", label: "Users", icon: "👥" },
      { to: "/admin/listings", label: "Listings", icon: "🧺" },
      { to: "/admin/issues", label: "Issues", icon: "🛟" },
    ];
  if (role === "buyer")
    return [
      { to: "/", label: "Home", icon: "🏠", end: true },
      { to: "/browse", label: "Browse", icon: "🔎" },
      { to: "/orders", label: "Orders", icon: "🧾" },
      { to: "/requests", label: "Requests", icon: "📣" },
    ];
  return [
    { to: "/", label: "Home", icon: "🏠", end: true },
    { to: "/browse", label: "Browse", icon: "🔎" },
    { to: "/login", label: "Log in", icon: "🔑" },
  ];
}

function NotificationBell() {
  const [unread, setUnread] = useState(0);
  useEffect(() => {
    let stop = false;
    const load = () =>
      api.get<unknown[]>("/notifications", { page_size: 1 }).then(
        (r) => !stop && setUnread(r.unread_count ?? 0),
        () => undefined,
      );
    load();
    const t = window.setInterval(load, 45000);
    const onRead = () => load();
    window.addEventListener("mazaox:notifications-changed", onRead);
    return () => {
      stop = true;
      window.clearInterval(t);
      window.removeEventListener("mazaox:notifications-changed", onRead);
    };
  }, []);
  return (
    <Link to="/notifications" className="icon-btn" aria-label={unread ? `Notifications, ${unread} unread` : "Notifications"}>
      <span aria-hidden="true">🔔</span>
      {unread > 0 && <span className="dot">{unread > 99 ? "99+" : unread}</span>}
    </Link>
  );
}

function UserMenu() {
  const { user, logout } = useAuth();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();
  const location = useLocation();
  useEffect(() => {
    setOpen(false);
  }, [location.pathname]);
  useEffect(() => {
    if (!open) return;
    const close = (e: MouseEvent) => !ref.current?.contains(e.target as Node) && setOpen(false);
    const esc = (e: KeyboardEvent) => e.key === "Escape" && setOpen(false);
    document.addEventListener("mousedown", close);
    document.addEventListener("keydown", esc);
    return () => {
      document.removeEventListener("mousedown", close);
      document.removeEventListener("keydown", esc);
    };
  }, [open]);
  if (!user) return null;
  const initials = user.full_name.split(" ").map((p) => p[0]).slice(0, 2).join("").toUpperCase();
  return (
    <div className="relative" ref={ref}>
      <button className="avatar" onClick={() => setOpen((o) => !o)} aria-haspopup="menu" aria-expanded={open} aria-label="Account menu">{initials}</button>
      {open && (
        <div className="menu" role="menu">
          <div className="who"><b>{user.full_name}</b><div className="muted small">{user.email ?? user.phone} · {user.role}</div></div>
          <Link to="/me" role="menuitem">My profile</Link>
          {user.role === "buyer" && <Link to="/orders" role="menuitem">My orders</Link>}
          <Link to="/notifications" role="menuitem">Notifications</Link>
          <button role="menuitem" onClick={async () => { await logout(); navigate("/"); }}>Log out</button>
        </div>
      )}
    </div>
  );
}

function Header() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [q, setQ] = useState("");
  const items = navFor(user?.role ?? null);
  return (
    <header className="header">
      <div className="wrap">
        <Link to="/" className="brand" aria-label="MazaoX home"><img src="/logo.png" alt="MazaoX" /></Link>
        {user?.role !== "admin" && (
          <form className="hsearch" role="search" onSubmit={(e) => { e.preventDefault(); navigate(`/browse${q.trim() ? `?q=${encodeURIComponent(q.trim())}` : ""}`); }}>
            <span aria-hidden="true">🔍</span>
            <input className="input" value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search tomatoes, maize, kale…" aria-label="Search produce" />
          </form>
        )}
        <nav className="nav" aria-label="Main">
          {items.filter((i) => i.to !== "/login").map((i) => <NavLink key={i.to} to={i.to} end={i.end} className={({ isActive }) => (isActive ? "active" : "")}>{i.label}</NavLink>)}
        </nav>
        <div className="hactions">
          {user ? (
            <>
              <NotificationBell />
              <UserMenu />
            </>
          ) : (
            <>
              <Link className="btn btn-ghost btn-sm" to="/register?role=farmer">Sell produce</Link>
              <Link className="btn btn-primary btn-sm" to="/login">Log in</Link>
            </>
          )}
        </div>
      </div>
    </header>
  );
}

function TabBar() {
  const { user } = useAuth();
  const items = navFor(user?.role ?? null);
  return (
    <nav className="tabbar" aria-label="Main">
      {items.map((i) => (
        <NavLink key={i.to} to={i.to} end={i.end} className={({ isActive }) => (isActive ? "active" : "")}>
          <b aria-hidden="true">{i.icon}</b>
          {i.label}
        </NavLink>
      ))}
    </nav>
  );
}

function Footer() {
  return (
    <footer className="footer">
      <div className="wrap">
        <img src="/logo.png" alt="MazaoX" />
        <p>MazaoX is an academic prototype. Payments are simulated and no real money moves. Demo data only.</p>
      </div>
    </footer>
  );
}

export function Layout() {
  const location = useLocation();
  useEffect(() => {
    window.scrollTo(0, 0);
  }, [location.pathname]);
  return (
    <>
      <a className="skip" href="#main">Skip to content</a>
      <Header />
      <main id="main"><Outlet /></main>
      <Footer />
      <TabBar />
    </>
  );
}
