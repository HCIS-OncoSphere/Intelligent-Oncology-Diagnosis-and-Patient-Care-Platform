// Public home page, shown at "/" to visitors who are not signed in. Signed-in people go straight to their
// first page (see App.jsx). Everything listed here is something OncoSphere really does today.
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Icon } from "../shared/Icon.jsx";
import { ThemeToggle } from "../shared/ThemeToggle.jsx";
import { Logo } from "../shared/ui.jsx";
import { HeroArt } from "./HeroArt.jsx";
import "./home.css";

// The path a patient takes through the clinic, and where OncoSphere keeps it.
const JOURNEY = [
  { icon: "calendar", title: "First visit", text: "Book a consultation from the oncologist's free slots." },
  { icon: "image", title: "Diagnosis & imaging", text: "Scans and ICD-10 diagnoses land in one record." },
  { icon: "clipboard", title: "Treatment plan", text: "Chemotherapy, radiotherapy or surgery, planned by your team." },
  { icon: "activity", title: "Sessions", text: "Each session is booked, tracked and billed in order." },
  { icon: "checkCircle", title: "Follow-up", text: "Results reviewed and the next check-up already on the calendar." },
];

const FEATURES = [
  {
    big: true, icon: "calendar", tone: "violet", title: "Appointments that fit around treatment",
    text: "Patients pick a free slot from the doctor's weekly hours. Staff reschedule, cancel, and mark visits completed or no-show, with tomorrow's reminder list ready.",
    tags: ["Consultation", "Chemotherapy session", "Radiotherapy session", "Follow-up visit"],
  },
  { icon: "clipboard", tone: "orange", title: "Medical records", text: "Diagnoses with ICD-10 codes, prescriptions, treatment plans and clinical orders." },
  { icon: "image", tone: "violet", title: "Imaging", text: "DICOM studies linked from the Orthanc PACS to each patient." },
  { icon: "receipt", tone: "orange", title: "Invoices", text: "Every visit and session billed, with a clear paid or pending status." },
  { icon: "barChart", tone: "violet", title: "Clinic reports", text: "Appointments per day and per doctor, patients by gender, top diagnoses." },
  { icon: "link", tone: "orange", title: "HL7 v2 integration", text: "Messages exchanged with other hospital systems, each one logged." },
];

const ROLES = {
  patient: {
    label: "Patients", icon: "user",
    lead: "Your care, in your pocket. No phone queues, no lost papers.",
    points: [
      "Book, reschedule or cancel your own visits",
      "See your diagnoses, prescriptions and treatment plan",
      "Follow your imaging studies and results",
      "Keep track of every invoice",
    ],
  },
  clinical: {
    label: "Care team", icon: "stethoscope",
    lead: "Doctors and nurses see the whole patient before they walk in.",
    points: [
      "Set your weekly hours; patients book into them",
      "Record diagnoses, prescriptions and treatment plans",
      "Place clinical orders and link imaging studies",
      "Mark visits completed or no-show in one click",
    ],
  },
  admin: {
    label: "Administrators", icon: "shield",
    lead: "Run the clinic with the numbers in front of you.",
    points: [
      "Create staff accounts and manage roles",
      "Book visits on behalf of any patient",
      "Clinic reports with export",
      "System settings, audit log and HL7 message log",
    ],
  },
};

// Decorative day of slots on the appointments card: one taken, one being picked. Not real data.
const SLOTS = [["09:00", "taken"], ["09:30", ""], ["10:00", ""], ["10:30", "pick"], ["11:00", ""], ["11:30", "taken"]];
const SlotsPreview = () => (
  <div className="lp-slots" aria-hidden="true">
    <span className="lp-slots-day"><Icon name="calendar" /> Tuesday · Oncology clinic</span>
    <div>{SLOTS.map(([t, s]) => <span key={t} className={s}>{t}</span>)}</div>
  </div>
);

export default function Home() {
  const [role, setRole] = useState("patient");
  useEffect(() => { document.title = "OncoSphere · Oncology care, connected"; }, []);
  const r = ROLES[role];

  return (
    <div className="lp">
      <header className="lp-nav">
        <div className="lp-nav-in">
          <Link to="/" className="lp-brand"><Logo /> OncoSphere</Link>
          <nav className="lp-links" aria-label="Sections">
            <a href="#journey">Care journey</a>
            <a href="#features">Features</a>
            <a href="#roles">Who it's for</a>
          </nav>
          <div className="spacer" />
          <ThemeToggle />
          <Link to="/login" className="lp-btn ghost">Sign in</Link>
          <Link to="/register" className="lp-btn primary lp-hide-sm">Create account</Link>
        </div>
      </header>

      {/* ---------- hero ---------- */}
      <section className="lp-hero">
        <div className="lp-hero-in">
          <div className="lp-hero-text">
            <span className="lp-eyebrow"><Icon name="ribbon" /> Built for oncology clinics</span>
            <h1>From the first scan to the last follow-up, <em>one connected record.</em></h1>
            <p>
              OncoSphere brings appointments, treatment plans, imaging and invoices together, so patients
              and their care team always look at the same picture.
            </p>
            <div className="lp-cta">
              <Link to="/register" className="lp-btn accent lg">Create a patient account <Icon name="arrowRight" /></Link>
              <Link to="/login" className="lp-btn on-dark lg">Sign in</Link>
            </div>
            <ul className="lp-proof">
              <li><Icon name="shield" /> Role-based access</li>
              <li><Icon name="link" /> HL7 v2 ready</li>
              <li><Icon name="image" /> DICOM via Orthanc</li>
            </ul>
          </div>
          <HeroArt />
        </div>
      </section>

      {/* ---------- care journey ---------- */}
      <section id="journey" className="lp-section">
        <div className="lp-head">
          <span className="lp-kicker">The care journey</span>
          <h2>Every step of treatment, in order</h2>
          <p>Cancer care is a long road with many stops. OncoSphere keeps each stop linked to the one before it.</p>
        </div>
        <ol className="lp-journey">
          {JOURNEY.map((s, i) => (
            <li key={s.title}>
              <span className="lp-step-icon"><Icon name={s.icon} /><span className="lp-step-n">{i + 1}</span></span>
              <b>{s.title}</b>
              <span>{s.text}</span>
            </li>
          ))}
        </ol>
      </section>

      {/* ---------- features ---------- */}
      <section id="features" className="lp-section lp-tint">
        <div className="lp-head">
          <span className="lp-kicker">What's inside</span>
          <h2>One platform instead of six tools</h2>
          <p>Each part works on its own and shares the same patient record with the rest.</p>
        </div>
        <div className="lp-bento">
          {FEATURES.map((f) => (
            <article key={f.title} className={`lp-feature ${f.big ? "big" : ""}`}>
              {f.big && <SlotsPreview />}
              <span className={`lp-feature-icon ${f.tone}`}><Icon name={f.icon} /></span>
              <h3>{f.title}</h3>
              <p>{f.text}</p>
              {f.tags && <div className="lp-tags">{f.tags.map((t) => <span key={t}>{t}</span>)}</div>}
            </article>
          ))}
        </div>
      </section>

      {/* ---------- roles ---------- */}
      <section id="roles" className="lp-section">
        <div className="lp-head">
          <span className="lp-kicker">Who it's for</span>
          <h2>Each role sees what it needs, and only that</h2>
        </div>
        <div className="lp-roles">
          <div className="lp-role-tabs" role="tablist" aria-label="Roles">
            {Object.entries(ROLES).map(([k, v]) => (
              <button key={k} role="tab" type="button" aria-selected={role === k} id={`tab-${k}`} aria-controls="role-panel"
                      className={role === k ? "on" : ""} onClick={() => setRole(k)}>
                <Icon name={v.icon} /> {v.label}
              </button>
            ))}
          </div>
          <div className="lp-role-panel" role="tabpanel" id="role-panel" aria-labelledby={`tab-${role}`}>
            <p className="lp-role-lead">{r.lead}</p>
            <ul>
              {r.points.map((p) => <li key={p}><Icon name="checkCircle" /> {p}</li>)}
            </ul>
            {role === "patient"
              ? <Link to="/register" className="lp-btn primary">Create a patient account <Icon name="arrowRight" /></Link>
              : <p className="lp-note"><Icon name="shield" /> Staff accounts are created by your clinic's administrator.</p>}
          </div>
        </div>
      </section>

      {/* ---------- closing call to action ---------- */}
      <section className="lp-band">
        <div className="lp-band-in">
          <div>
            <h2>Ready when your care team is.</h2>
            <p>Create your account in a minute and book your first visit today.</p>
          </div>
          <div className="lp-cta">
            <Link to="/register" className="lp-btn accent lg">Get started</Link>
            <Link to="/login" className="lp-btn on-dark lg">I already have an account</Link>
          </div>
        </div>
      </section>

      <footer className="lp-foot">
        <div className="lp-brand"><Logo /> OncoSphere</div>
        <span>Intelligent oncology diagnosis and patient care</span>
        <span className="spacer" />
        <span>© {new Date().getFullYear()} OncoSphere</span>
      </footer>
    </div>
  );
}
