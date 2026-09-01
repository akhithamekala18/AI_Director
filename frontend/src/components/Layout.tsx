import { Link, Outlet, useLocation } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

const NAV_ITEMS = [
  { to: "/", label: "Dashboard" },
  { to: "/projects", label: "Projects" },
  { to: "/notifications", label: "Notifications" },
  { to: "/analytics", label: "Analytics" },
  { to: "/governance", label: "Governance" },
  { to: "/settings", label: "Settings" },
];

export function Layout() {
  const { user, logout } = useAuth();
  const location = useLocation();

  return (
    <div className="app-layout">
      <header className="app-header">
        <Link to="/" className="app-brand">
          AI Director
        </Link>
        <nav className="app-nav">
          {NAV_ITEMS.map((item) => (
            <Link
              key={item.to}
              to={item.to}
              className={
                location.pathname === item.to ||
                (item.to !== "/" && location.pathname.startsWith(item.to))
                  ? "nav-link active"
                  : "nav-link"
              }
            >
              {item.label}
            </Link>
          ))}
        </nav>
        <div className="app-user">
          <span className="user-role">{user?.role}</span>
          <span className="user-name">{user?.username}</span>
          <button
            type="button"
            className="btn-logout"
            onClick={() => logout()}
          >
            Logout
          </button>
        </div>
      </header>
      <main className="app-main">
        <Outlet />
      </main>
    </div>
  );
}
