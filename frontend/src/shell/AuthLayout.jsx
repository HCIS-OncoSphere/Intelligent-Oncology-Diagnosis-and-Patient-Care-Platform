// Shared frame and form pieces for the signed-out pages (sign in, create account).
import { useEffect, useId, useState } from "react";
import { ThemeToggle } from "../shared/ThemeToggle.jsx";
import { Logo } from "../shared/ui.jsx";
import "./auth.css";

const PATHS = {
  user: "M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2M12 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8z",
  mail: "M4 4h16a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2zM22 6l-10 7L2 6",
  lock: "M7 11V7a5 5 0 0 1 10 0v4M5 11h14a2 2 0 0 1 2 2v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-7a2 2 0 0 1 2-2z",
  phone: "M22 16.9v3a2 2 0 0 1-2.2 2 19.8 19.8 0 0 1-8.6-3.1 19.5 19.5 0 0 1-6-6A19.8 19.8 0 0 1 2.1 4.2 2 2 0 0 1 4.1 2h3a2 2 0 0 1 2 1.7c.1 1 .4 1.9.7 2.8a2 2 0 0 1-.5 2.1L8 9.9a16 16 0 0 0 6 6l1.3-1.3a2 2 0 0 1 2.1-.4c.9.3 1.8.6 2.8.7a2 2 0 0 1 1.7 2z",
  calendar: "M8 2v4M16 2v4M3 10h18M5 4h14a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2z",
  eye: "M2 12s3.6-7 10-7 10 7 10 7-3.6 7-10 7S2 12 2 12zM12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6z",
  eyeOff: "M9.9 4.2A9.1 9.1 0 0 1 12 4c6.4 0 10 8 10 8a18 18 0 0 1-2.2 3.2M6.6 6.6A17.6 17.6 0 0 0 2 12s3.6 8 10 8a9.7 9.7 0 0 0 5.4-1.6M14.1 14.1a3 3 0 1 1-4.2-4.2M2 2l20 20",
  alert: "M12 9v4M12 17h.01M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z",
  check: "M20 6 9 17l-5-5",
  scan: "M3 7V5a2 2 0 0 1 2-2h2M17 3h2a2 2 0 0 1 2 2v2M21 17v2a2 2 0 0 1-2 2h-2M7 21H5a2 2 0 0 1-2-2v-2M7 12h10",
  clipboard: "M9 2h6a1 1 0 0 1 1 1v2a1 1 0 0 1-1 1H9a1 1 0 0 1-1-1V3a1 1 0 0 1 1-1zM16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2M9 14l2 2 4-4",
  shield: "M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z",
};

export const Icon = ({ name, className = "icon" }) => (
  <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"
       strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
    <path d={PATHS[name]} />
  </svg>
);

// Decorative example cards floating around the artwork (not real data).
const ART_CARDS = [
  { cls: "c1", icon: "calendar", title: "Appointment booked", text: "Oncology clinic" },
  { cls: "c2", icon: "clipboard", title: "Treatment plan", text: "Updated by your care team" },
  { cls: "c3", icon: "scan", title: "Results ready", text: "Imaging · CT scan" },
];

const RIBBON = "M12 3c-2.2 0-3.5 1.8-3.5 3.8 0 2.4 1.6 4.6 3.5 7.2l4.5 7M12 3c2.2 0 3.5 1.8 3.5 3.8 0 2.4-1.6 4.6-3.5 7.2l-4.5 7";

/** The light illustrated panel: the logo's ribbon-in-a-sphere, drawn large, with floating cards. */
function AuthArt() {
  return (
    <aside className="auth-art" aria-hidden="true">
      <div className="art-stage">
        <svg className="art-rings" viewBox="0 0 400 400">
          <circle cx="200" cy="200" r="196" className="ring-1" />
          <circle cx="200" cy="200" r="150" className="ring-2" />
          <circle cx="200" cy="200" r="104" className="ring-3" />
          <circle cx="200" cy="200" r="104" className="ring-line" />
          <path d={RIBBON} className="ring-ribbon" transform="translate(200 200) scale(6.2) translate(-12 -12)" />
          <circle cx="54" cy="150" r="7" className="dot" />
          <circle cx="342" cy="262" r="5" className="dot" />
          <circle cx="300" cy="70" r="4" className="dot" />
        </svg>
        {ART_CARDS.map((c) => (
          <div key={c.cls} className={`art-card ${c.cls}`}>
            <span className="art-card-icon"><Icon name={c.icon} /></span>
            <span><b>{c.title}</b><small>{c.text}</small></span>
          </div>
        ))}
      </div>
      <div className="art-caption">
        <h2>Your care, connected.</h2>
        <p>Appointments, treatment plans and results, shared between you and your care team.</p>
      </div>
    </aside>
  );
}

export function AuthLayout({ title, children }) {
  useEffect(() => { document.title = `${title} · OncoSphere`; }, [title]);
  return (
    <div className="auth">
      <main className="auth-main">
        <div className="auth-top">
          <div className="auth-brand"><Logo /> OncoSphere</div>
          <ThemeToggle />
        </div>
        <div className="auth-panel">{children}</div>
        <p className="auth-copy"><Icon name="shield" /> Each role sees only its own pages and records · © {new Date().getFullYear()} OncoSphere</p>
      </main>
      <AuthArt />
    </div>
  );
}

/** Labelled input with a leading icon, an inline error, and an optional hint below. */
export function AuthField({ label, icon, error, hint, trailing, className = "", ...input }) {
  const id = useId();
  const describedBy = error ? `${id}-err` : hint ? `${id}-hint` : undefined;
  return (
    <div className={`auth-field ${error ? "has-error" : ""} ${className}`}>
      <label htmlFor={id}>{label}</label>
      <div className="auth-input">
        {icon && <Icon name={icon} />}
        <input id={id} aria-invalid={!!error} aria-describedby={describedBy} {...input} />
        {trailing}
      </div>
      {error ? <p id={`${id}-err`} className="auth-error"><Icon name="alert" /> {error}</p>
        : hint ? <p id={`${id}-hint`} className="auth-hint">{hint}</p> : null}
    </div>
  );
}

/** Password input with show/hide and a Caps Lock warning. */
export function PasswordField(props) {
  const [show, setShow] = useState(false);
  const [caps, setCaps] = useState(false);
  const watchCaps = (e) => setCaps(!!e.getModifierState?.("CapsLock"));
  return (
    <AuthField
      {...props}
      icon="lock"
      type={show ? "text" : "password"}
      onKeyDown={watchCaps}
      onKeyUp={watchCaps}
      onBlur={() => setCaps(false)}
      hint={caps ? "Caps Lock is on." : props.hint}
      trailing={
        <button type="button" className="auth-reveal" onClick={() => setShow(!show)}
                aria-label={show ? "Hide password" : "Show password"} aria-pressed={show}>
          <Icon name={show ? "eyeOff" : "eye"} />
        </button>
      }
    />
  );
}

export function Alert({ children }) {
  if (!children) return null;
  return <div className="auth-alert" role="alert"><Icon name="alert" /><span>{children}</span></div>;
}

export function SubmitButton({ busy, children, busyText = "Please wait…" }) {
  return (
    <button className="primary auth-submit" disabled={busy} aria-busy={busy}>
      {busy && <span className="auth-spinner" aria-hidden="true" />}
      {busy ? busyText : children}
    </button>
  );
}

/** One readable line for a failed request: network trouble vs. the server's own message. */
export function requestProblem(e) {
  if (!e || e.status === undefined || e.status >= 500) {
    return "Can't reach the OncoSphere server right now. Check that the backend is running and try again.";
  }
  return null;
}
