import { useState } from "react";
import { Routes, Route, Navigate, NavLink, useNavigate } from "react-router-dom";
import { getToken, clearToken } from "./api.js";
import Login from "./pages/Login.jsx";
import Overview from "./pages/Overview.jsx";
import Submissions from "./pages/Submissions.jsx";
import SubmissionDetail from "./pages/SubmissionDetail.jsx";
import Users from "./pages/Users.jsx";
import UserDetail from "./pages/UserDetail.jsx";
import FraudLogs from "./pages/FraudLogs.jsx";
import CreditRules from "./pages/CreditRules.jsx";
import Settings from "./pages/Settings.jsx";
import AuditLog from "./pages/AuditLog.jsx";

const NAV = [
  ["/", "Overview"],
  ["/submissions", "Review queue"],
  ["/users", "Users"],
  ["/fraud", "Fraud flags"],
  ["/credit-rules", "Credit rules"],
  ["/settings", "Settings"],
  ["/audit", "Audit log"],
];

function Layout({ children }) {
  const navigate = useNavigate();
  const [menuOpen, setMenuOpen] = useState(false);
  const logout = () => {
    clearToken();
    navigate("/login");
  };
  return (
    <div className="layout">
      <aside className="sidebar">
        <div className="sidebar-head">
          <div className="brand"><span className="leaf" aria-hidden="true">&#127807;</span> Carbon Guard</div>
          <button className="btn secondary small menu-btn" aria-expanded={menuOpen}
                  onClick={() => setMenuOpen((o) => !o)}>Menu</button>
        </div>
        <p className="muted small">Admin dashboard</p>
        <nav className={menuOpen ? "open" : ""} onClick={() => setMenuOpen(false)}>
          {NAV.map(([to, label]) => <NavLink key={to} to={to} end={to === "/"}>{label}</NavLink>)}
        </nav>
        <button className="btn secondary logout" onClick={logout}>Log out</button>
      </aside>
      <main className="content">{children}</main>
    </div>
  );
}

function Protected({ children }) {
  return getToken() ? <Layout>{children}</Layout> : <Navigate to="/login" replace />;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/" element={<Protected><Overview /></Protected>} />
      <Route path="/submissions" element={<Protected><Submissions /></Protected>} />
      <Route path="/submissions/:id" element={<Protected><SubmissionDetail /></Protected>} />
      <Route path="/users" element={<Protected><Users /></Protected>} />
      <Route path="/users/:id" element={<Protected><UserDetail /></Protected>} />
      <Route path="/fraud" element={<Protected><FraudLogs /></Protected>} />
      <Route path="/credit-rules" element={<Protected><CreditRules /></Protected>} />
      <Route path="/settings" element={<Protected><Settings /></Protected>} />
      <Route path="/audit" element={<Protected><AuditLog /></Protected>} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
