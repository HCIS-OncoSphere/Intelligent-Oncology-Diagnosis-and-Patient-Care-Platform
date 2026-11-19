// App shell. Nobody edits this file to add a page: drop a folder in src/modules/<name>/index.jsx and it is picked up.
// Each module gets its own URL, /<id>, so refresh, Back/Forward and shared links open the same page.
import { useEffect, useState } from "react";
import { NavLink, Navigate, Route, Routes } from "react-router-dom";
import { api, logout } from "./api.js";
import { Logo } from "./shared/ui.jsx";
import Login from "./shell/Login.jsx";

// Each module default-exports { id, label, order, roles, Component }
const found = import.meta.glob("./modules/*/index.jsx", { eager: true });
const modules = Object.values(found).map((m) => m.default).sort((a, b) => a.order - b.order);

const ROLE = { admin: "Administrator", clinical: "Clinical staff", patient: "Patient" };

function Page({ module, me }) {
  useEffect(() => { document.title = `${module.label} · OncoSphere`; }, [module]);
  return (
    <>
      <div className="page-title"><h1>{module.label}</h1></div>
      <module.Component me={me} />
    </>
  );
}

export default function App() {
  const [me, setMe] = useState(null);
  const [checking, setChecking] = useState(() => !!localStorage.getItem("access"));
  useEffect(() => {
    if (!checking) return;
    api("/auth/me/").then(setMe).catch(() => logout()).finally(() => setChecking(false));
  }, []);

  if (checking) return <p className="hint" style={{ padding: 24 }}>Loading…</p>;
  // signed out: show the sign-in form at whatever URL was opened, so a shared link lands on its page after sign-in
  if (!me) return <Login onDone={setMe} />;

  const visible = modules.filter((m) => m.roles.includes(me.role));
  const home = visible[0] ? `/${visible[0].id}` : null;
  const name = [me.first_name, me.last_name].filter(Boolean).join(" ") || me.username;
  return (
    <>
      <header className="topbar">
        <div className="topbar-in">
          <div className="brand"><Logo /> OncoSphere</div>
          <div className="spacer" />
          <div className="user-chip">
            <span className="avatar">{name[0]}</span>
            <span className="who"><b>{name}</b><span className="role-tag">{ROLE[me.role] || me.role}</span></span>
            <button className="sm" onClick={() => { logout(); setMe(null); }}>Sign out</button>
          </div>
        </div>
        <nav className="tabs" aria-label="Main">
          {visible.map((m) => (
            <NavLink key={m.id} to={`/${m.id}`} className={({ isActive }) => `tab${isActive ? " active" : ""}`}>{m.label}</NavLink>
          ))}
        </nav>
      </header>
      <main className="page">
        {home ? (
          <Routes>
            {visible.map((m) => <Route key={m.id} path={`/${m.id}/*`} element={<Page module={m} me={me} />} />)}
            {/* the home page and any unknown or not-allowed address go to the first page of this role */}
            <Route path="*" element={<Navigate to={home} replace />} />
          </Routes>
        ) : <p>No pages available for your role.</p>}
      </main>
    </>
  );
}
