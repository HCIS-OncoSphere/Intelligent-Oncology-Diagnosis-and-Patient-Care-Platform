// App shell. Nobody edits this file to add a page: drop a folder in src/modules/<name>/index.jsx and it is picked up.
// Each module gets its own URL, /<id>, so refresh, Back/Forward and shared links open the same page.
import { useEffect, useState } from "react";
import { NavLink, Navigate, Route, Routes, useLocation } from "react-router-dom";
import { api, logout } from "./api.js";
import { Avatar } from "./shared/Avatar.jsx";
import { ConfirmDialog } from "./shared/ConfirmDialog.jsx";
import { ThemeToggle } from "./shared/ThemeToggle.jsx";
import { Logo } from "./shared/ui.jsx";
import Login from "./shell/Login.jsx";
import Register from "./shell/Register.jsx";

// Each module default-exports { id, label, order, roles, Component }.
// Optional: nav: false (no tab; reached by link), hero: false (no title banner),
// chrome: false (no app header either; the page gets `home` and `onSignOut` props), description.
const found = import.meta.glob("./modules/*/index.jsx", { eager: true });
const modules = Object.values(found).map((m) => m.default).sort((a, b) => a.order - b.order);

const ROLE = { admin: "Administrator", clinical: "Clinical staff", patient: "Patient" };

// One line under each page title in the banner. A module can set its own with a `description` field.
const DESCRIPTIONS = {
  appointments: "Book, reschedule and track visits with the oncology team.",
  records: "Medical records, prescriptions, treatment plans and clinical orders.",
  reports: "Key numbers and trends across the clinic.",
  admin: "System settings and the audit log.",
};
const today = new Intl.DateTimeFormat(undefined, { weekday: "long", day: "numeric", month: "long" });

function Page({ module, me, home, onSignOut }) {
  useEffect(() => { document.title = `${module.label} · OncoSphere`; }, [module]);
  const description = module.description ?? DESCRIPTIONS[module.id];
  // the page draws its own header
  if (module.hero === false) return <module.Component me={me} home={home} onSignOut={onSignOut} />;
  return (
    <>
      <section className="page-hero">
        <div className="page-hero-in">
          <div className="page-hero-text">
            <h1>{module.label}</h1>
            {description && <p>{description}</p>}
          </div>
          <span className="page-hero-date">{today.format(new Date())}</span>
        </div>
      </section>
      <div className="page"><module.Component me={me} /></div>
    </>
  );
}

export default function App() {
  const { pathname } = useLocation();
  const [me, setMe] = useState(null);
  const [askSignOut, setAskSignOut] = useState(false);
  const [checking, setChecking] = useState(() => !!localStorage.getItem("access"));
  useEffect(() => {
    if (!checking) return;
    api("/auth/me/").then(setMe).catch(() => logout()).finally(() => setChecking(false));
  }, []);
  // pages that change your name or photo (the profile) ask the header to refresh
  useEffect(() => {
    const refresh = () => api("/auth/me/").then(setMe).catch(() => {});
    window.addEventListener("oncosphere:me-changed", refresh);
    return () => window.removeEventListener("oncosphere:me-changed", refresh);
  }, []);

  if (checking) return <p className="hint" style={{ padding: 24 }}>Loading…</p>;
  // signed out: /register shows sign-up; any other URL shows the sign-in form in place,
  // so a shared link lands on its page after sign-in
  if (!me) return (
    <Routes>
      <Route path="/register" element={<Register onDone={setMe} />} />
      <Route path="*" element={<Login onDone={setMe} />} />
    </Routes>
  );

  const visible = modules.filter((m) => m.roles.includes(me.role));
  const tabs = visible.filter((m) => m.nav !== false);
  const home = tabs[0] ? `/${tabs[0].id}` : null;
  const hasProfile = visible.some((m) => m.id === "profile");
  const name = [me.first_name, me.last_name].filter(Boolean).join(" ") || me.username;
  // Sign out buttons (header and profile bar) only open the confirmation; signing out happens on confirm.
  const signOut = () => setAskSignOut(true);
  const confirmSignOut = () => { setAskSignOut(false); logout(); setMe(null); };
  // a page with chrome: false (the profile) replaces the header with its own bar
  const current = visible.find((m) => pathname === `/${m.id}` || pathname.startsWith(`/${m.id}/`));
  const showHeader = current?.chrome !== false;
  const who = (
    <>
      <Avatar src={me.avatar} name={name} size={38} seed={me.id} />
      <span className="who"><b>{name}</b><span className="role-tag">{ROLE[me.role] || me.role}</span></span>
    </>
  );
  return (
    <>
      {showHeader && <header className="topbar">
        <div className="topbar-in">
          <div className="brand"><Logo /> OncoSphere</div>
          <div className="spacer" />
          <ThemeToggle />
          <div className="user-chip">
            {hasProfile
              ? <NavLink to="/profile" end className="user-link" title="Your profile">{who}</NavLink>
              : who}
            <button className="sm" onClick={signOut}>Sign out</button>
          </div>
        </div>
        <nav className="tabs" aria-label="Main">
          {tabs.map((m) => (
            <NavLink key={m.id} to={`/${m.id}`} className={({ isActive }) => `tab${isActive ? " active" : ""}`}>{m.label}</NavLink>
          ))}
        </nav>
      </header>}
      <main>
        {home ? (
          <Routes>
            {visible.map((m) => <Route key={m.id} path={`/${m.id}/*`} element={<Page module={m} me={me} home={home} onSignOut={signOut} />} />)}
            {/* the home page and any unknown or not-allowed address go to the first page of this role */}
            <Route path="*" element={<Navigate to={home} replace />} />
          </Routes>
        ) : <p className="page">No pages available for your role.</p>}
      </main>
      {askSignOut && (
        <ConfirmDialog
          title="Sign out of OncoSphere?"
          message="You'll need your username or email and password to sign back in."
          confirmLabel="Sign out"
          onConfirm={confirmSignOut}
          onCancel={() => setAskSignOut(false)}
        />
      )}
    </>
  );
}
