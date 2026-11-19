// App shell. Nobody edits this file to add a page: drop a folder in src/modules/<name>/index.jsx and it is picked up.
import { useEffect, useState } from "react";
import { api, logout } from "./api.js";
import { Logo } from "./shared/ui.jsx";
import Login from "./shell/Login.jsx";

// Each module default-exports { id, label, order, roles, Component }
const found = import.meta.glob("./modules/*/index.jsx", { eager: true });
const modules = Object.values(found).map((m) => m.default).sort((a, b) => a.order - b.order);

const ROLE = { admin: "Administrator", clinical: "Clinical staff", patient: "Patient" };

export default function App() {
  const [me, setMe] = useState(null), [tab, setTab] = useState(null);
  useEffect(() => { if (localStorage.getItem("access")) api("/auth/me/").then(setMe).catch(() => logout()); }, []);
  if (!me) return <Login onDone={setMe} />;

  const visible = modules.filter((m) => m.roles.includes(me.role));
  const current = visible.find((m) => m.id === tab) || visible[0];
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
            <button key={m.id} className={`tab${current?.id === m.id ? " active" : ""}`} onClick={() => setTab(m.id)}>{m.label}</button>
          ))}
        </nav>
      </header>
      <main className="page">
        {current ? (
          <>
            <div className="page-title"><h1>{current.label}</h1></div>
            <current.Component me={me} />
          </>
        ) : <p>No pages available for your role.</p>}
      </main>
    </>
  );
}
