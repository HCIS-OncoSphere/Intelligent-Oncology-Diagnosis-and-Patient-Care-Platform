// Profile page for patients and doctors. /profile is your own; /profile/<user id> opens someone else's
// (staff can open patients; anyone can open a doctor). Not a tab: it opens from your name in the header.
import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../../api.js";
import { Avatar } from "../../shared/Avatar.jsx";
import { Icon } from "../../shared/Icon.jsx";
import { errorText } from "../../shared/ui.jsx";
import { EditDialog, PhotoDialog } from "./dialogs.jsx";
import "./profile.css";

const GENDER = { M: "Male", F: "Female", O: "Other" };
const DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
const fmtDate = (d, opts) => new Intl.DateTimeFormat(undefined, opts).format(new Date(d));
const money = (v) => `EGP ${Number(v || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
const day = { day: "numeric", month: "short", year: "numeric" };
const ROLE_LABEL = { admin: "Administrator", clinical: "Clinical staff", patient: "Patient" };
const hhmm = (t) => String(t).slice(0, 5);
const list = (s) => String(s || "").split(",").map((x) => x.trim()).filter(Boolean);

const Stat = ({ icon, tone, label, value, children }) => (
  <div className={`pf-stat tone-${tone}`}>
    <span className="pf-stat-icon"><Icon name={icon} /></span>
    <div className="pf-stat-body">
      <span className="pf-stat-label">{label}</span>
      <span className="pf-stat-value">{value}</span>
      {children}
    </div>
  </div>
);

const Card = ({ icon, tone = "teal", title, children, className = "" }) => (
  <section className={`pf-card ${className}`}>
    <h3 className="pf-card-title"><span className={`pf-chip-icon tone-${tone}`}><Icon name={icon} /></span>{title}</h3>
    {children}
  </section>
);

const Row = ({ icon, label, children }) => (
  <div className="pf-row">
    <Icon name={icon} />
    <span className="pf-row-label">{label}</span>
    <span className="pf-row-value">{children || <span className="pf-empty">Not added</span>}</span>
  </div>
);

function Header({ p, onPhoto, onEdit, nav }) {
  const pt = p.patient, dr = p.doctor;
  return (
    <>
      <div className={`pf-cover ${p.cover ? "has-image" : ""}`} style={p.cover ? { backgroundImage: `url(${p.cover})` } : undefined}>
        {nav}
        {p.is_me && (
          <button className="pf-cover-btn" onClick={() => onPhoto("cover")}>
            <Icon name="image" /> {p.cover ? "Change cover" : "Add cover"}
          </button>
        )}
      </div>
      <div className="pf-head">
        <div className="pf-head-avatar">
          <Avatar src={p.avatar} name={p.full_name} size={120} seed={p.id} />
          {p.is_me && (
            <button className="pf-cam" onClick={() => onPhoto("avatar")} aria-label="Change profile photo">
              <Icon name="camera" />
            </button>
          )}
        </div>
        <div className="pf-head-text">
          <h1>{dr ? `Dr. ${p.full_name}` : p.full_name}</h1>
          <div className="pf-badges">
            {pt && <>
              <span className="pf-badge tone-teal"><Icon name="user" />Patient</span>
              <span className="pf-badge tone-blue"><Icon name="idCard" />{pt.mrn}</span>
              <span className="pf-badge tone-plain">{GENDER[pt.gender] || pt.gender} · {pt.age != null ? `${pt.age} years` : "Age not set"}</span>
            </>}
            {dr && <>
              <span className="pf-badge tone-blue"><Icon name="stethoscope" />{dr.specialty}</span>
              <span className="pf-badge tone-violet"><Icon name="award" />License {dr.license_no}</span>
              {dr.available_today
                ? <span className="pf-badge tone-green"><Icon name="checkCircle" />Available today</span>
                : <span className="pf-badge tone-plain">Not working today</span>}
            </>}
            {!pt && !dr && <span className="pf-badge tone-violet"><Icon name="shield" />{ROLE_LABEL[p.role] || p.role}</span>}
            {p.member_since && <span className="pf-badge tone-plain"><Icon name="clock" />Member since {fmtDate(p.member_since, { month: "short", year: "numeric" })}</span>}
          </div>
        </div>
        {p.is_me && <button className="primary pf-edit" onClick={onEdit}><Icon name="pencil" /> Edit profile</button>}
      </div>
    </>
  );
}

function PatientView({ p }) {
  const pt = p.patient;
  const stage = (pt.cancer_stage.match(/IV|III|II|I|[1-4]/) || [""])[0];
  const stageN = { I: 1, II: 2, III: 3, IV: 4 }[stage] || Number(stage) || 0;
  const next = pt.upcoming[0];
  return (
    <>
      <div className="pf-stats">
        <Stat icon="calendar" tone="teal" label="Next visit"
              value={next ? fmtDate(next.start_time, { weekday: "short", day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" }) : "None booked"} />
        <Stat icon="activity" tone="violet" label="Treatment"
              value={pt.active_plan ? pt.active_plan.type : "No active plan"}>
          {pt.active_plan && <span className="pf-stat-sub">Since {fmtDate(pt.active_plan.start_date, { day: "numeric", month: "short", year: "numeric" })}</span>}
        </Stat>
        <Stat icon="microscope" tone="blue" label="Latest result"
              value={pt.latest_result ? pt.latest_result.order_type : "No results yet"}>
          {pt.latest_result && <span className="pf-stat-sub">{fmtDate(pt.latest_result.reported_at, { day: "numeric", month: "short" })}</span>}
        </Stat>
        <Stat icon="pill" tone="amber" label="Prescriptions" value={pt.prescriptions} />
      </div>

      <div className="pf-grid">
        <Card icon="ribbon" tone="rose" title="Medical summary">
          <Row icon="ribbon" label="Cancer type">{pt.cancer_type && <span className="pf-pill tone-rose">{pt.cancer_type}</span>}</Row>
          <Row icon="layers" label="Stage">
            {pt.cancer_stage && <span className="pf-stage">
              <span className="pf-stage-bars">{[1, 2, 3, 4].map((i) => <i key={i} className={i <= stageN ? "on" : ""} />)}</span>
              {pt.cancer_stage}
            </span>}
          </Row>
          <Row icon="droplet" label="Blood type">{pt.blood_type && <span className="pf-pill tone-red">{pt.blood_type}</span>}</Row>
          <p className="pf-note">Your care team keeps this section up to date.</p>
        </Card>

        <Card icon="calendar" tone="teal" title="Coming up">
          {pt.upcoming.length ? pt.upcoming.map((a) => (
            <div key={a.id} className="pf-event">
              <span className="pf-date"><b>{fmtDate(a.start_time, { day: "numeric" })}</b>{fmtDate(a.start_time, { month: "short" })}</span>
              <span className="pf-event-text">
                <b>{a.reason || "Appointment"}</b>
                <span>{fmtDate(a.start_time, { weekday: "long", hour: "2-digit", minute: "2-digit" })} · {a.doctor}</span>
              </span>
            </div>
          )) : <p className="pf-empty-block">No upcoming appointments. <Link to="/appointments">Book one</Link></p>}
        </Card>

        <Card icon="user" tone="blue" title="Contact details">
          <Row icon="phone" label="Phone">{pt.phone || p.phone}</Row>
          <Row icon="mail" label="Email">{p.email}</Row>
          {/* made by the system at sign-up; shown only to its owner */}
          {p.is_me && <Row icon="user" label="Username">{p.username}</Row>}
          <Row icon="mapPin" label="Address">{pt.address}</Row>
          <Row icon="cake" label="Date of birth">
            {pt.date_of_birth ? fmtDate(pt.date_of_birth, { day: "numeric", month: "long", year: "numeric" }) : <span className="pf-empty">Not added</span>}
          </Row>
          <Row icon="idCard" label="National ID">{pt.national_id}</Row>
          <Row icon="clock" label="Registered">{pt.registered_on && fmtDate(pt.registered_on, day)}</Row>
        </Card>

        <Card icon="siren" tone="red" title="Emergency contact">
          {pt.emergency_contact || pt.emergency_contact_phone ? <>
            <Row icon="user" label="Name">{pt.emergency_contact}</Row>
            <Row icon="phone" label="Phone">{pt.emergency_contact_phone}</Row>
          </> : <p className="pf-empty-block">No emergency contact yet.{p.is_me && " Add one with Edit profile."}</p>}
        </Card>

        <Card icon="clipboard" tone="rose" title="Diagnoses">
          {pt.diagnoses.length ? pt.diagnoses.map((d) => (
            <div key={d.code} className="pf-line">
              <span className="pf-pill tone-rose">{d.code}</span>
              <span className="pf-line-text">{d.description}</span>
              {d.is_primary && <span className="pf-pill tone-violet">Primary</span>}
            </div>
          )) : <p className="pf-empty-block">No diagnoses recorded yet.</p>}
        </Card>

        <Card icon="activity" tone="violet" title="Treatment plans">
          {pt.plans.length ? pt.plans.map((t, i) => (
            <div key={i} className="pf-line">
              <span className="pf-line-text"><b>{t.type}</b>
                <small>{fmtDate(t.start_date, day)}{t.end_date ? ` to ${fmtDate(t.end_date, day)}` : " · ongoing"} · Dr. {t.doctor}</small>
                {t.description && <small>{t.description}</small>}
              </span>
              <span className={`pf-pill status-${t.status}`}>{t.status}</span>
            </div>
          )) : <p className="pf-empty-block">No treatment plans yet.</p>}
        </Card>

        <Card icon="pill" tone="amber" title="Medications">
          {pt.medications.length ? pt.medications.map((m, i) => (
            <div key={i} className="pf-line">
              <span className="pf-line-text"><b>{m.medication}</b>
                <small>{[m.dosage, m.frequency, m.duration].filter(Boolean).join(" · ")}</small>
                {m.instructions && <small>{m.instructions}</small>}
              </span>
              <small>{fmtDate(m.prescribed_on, { day: "numeric", month: "short" })}</small>
            </div>
          )) : <p className="pf-empty-block">No prescriptions yet.</p>}
        </Card>

        <Card icon="microscope" tone="blue" title="Tests and results">
          {pt.orders.length ? pt.orders.map((o, i) => (
            <div key={i} className="pf-line">
              <span className="pf-line-text"><b>{o.type}{o.description ? `: ${o.description}` : ""}</b>
                <small>{o.result || "Waiting for the result"}</small>
              </span>
              <span className={`pf-pill status-${o.status}`}>{o.status}</span>
            </div>
          )) : <p className="pf-empty-block">No tests ordered yet.</p>}
        </Card>

        <Card icon="image" tone="teal" title="Imaging">
          {pt.imaging ? <>
            <Row icon="image" label="Latest scan">{pt.imaging.modality}{pt.imaging.body_part ? ` · ${pt.imaging.body_part}` : ""}</Row>
            <Row icon="calendar" label="Scan date">{fmtDate(pt.imaging.study_date, day)}</Row>
            <Row icon="layers" label="Studies on file">{pt.imaging.count}</Row>
          </> : <p className="pf-empty-block">No scans on file.</p>}
        </Card>

        <Card icon="receipt" tone="green" title="Visits and billing">
          <Row icon="calendar" label="Completed visits">{String(pt.visits.completed)}</Row>
          <Row icon="clock" label="Last visit">{pt.visits.last_visit && fmtDate(pt.visits.last_visit, day)}</Row>
          {pt.billing && <>
            <Row icon="receipt" label="To pay">{pt.billing.unpaid_count ? `${money(pt.billing.amount_due)} (${pt.billing.unpaid_count} invoice${pt.billing.unpaid_count > 1 ? "s" : ""})` : "Nothing due"}</Row>
            <Row icon="checkCircle" label="Paid invoices">{String(pt.billing.paid_count)}</Row>
          </>}
        </Card>

        <Card icon="users" tone="violet" title="Care team" className="pf-span">
          {pt.care_team.length ? (
            <div className="pf-team">
              {pt.care_team.map((d) => (
                <Link key={d.user_id} to={`/profile/${d.user_id}`} className="pf-person">
                  <Avatar src={d.avatar} name={d.name} size={44} seed={d.user_id} />
                  <span><b>Dr. {d.name}</b><span>{d.specialty}</span></span>
                  <Icon name="chevronRight" />
                </Link>
              ))}
            </div>
          ) : <p className="pf-empty-block">Your doctors appear here after your first appointment.</p>}
        </Card>
      </div>
    </>
  );
}

const STATUS = { scheduled: "Upcoming", completed: "Done", no_show: "No-show" };

function DoctorView({ p }) {
  const dr = p.doctor;
  const days = Object.fromEntries(dr.availability.map((a) => [a.day_of_week, a]));
  const todayIdx = (new Date().getDay() + 6) % 7;
  const own = !!dr.stats; // the doctor (or an admin) sees numbers and today's patients; visitors don't
  const about = (
    <Card icon="user" tone="amber" title="About" className={own ? "pf-span" : ""}>
      {dr.bio ? <p className="pf-bio">{dr.bio}</p>
        : <p className="pf-empty-block">{p.is_me ? "Tell patients about your work with Edit profile." : "No introduction yet."}</p>}
      <div className="pf-tags">
        {!own && dr.years_experience != null && <span className="pf-badge tone-amber"><Icon name="award" />{dr.years_experience} years experience</span>}
        {dr.education && <span className="pf-badge tone-violet"><Icon name="graduation" />{dr.education}</span>}
        {list(dr.languages).map((l) => <span key={l} className="pf-badge tone-teal"><Icon name="languages" />{l}</span>)}
        {list(dr.focus_areas).map((f) => <span key={f} className="pf-badge tone-rose"><Icon name="target" />{f}</span>)}
      </div>
    </Card>
  );
  return (
    <>
      {own && (
        <div className="pf-stats">
          <Stat icon="calendar" tone="blue" label="Today" value={`${dr.stats.today} visits`} />
          <Stat icon="trending" tone="teal" label="This week" value={`${dr.stats.week} visits`} />
          <Stat icon="users" tone="violet" label="Patients" value={dr.stats.patients} />
          <Stat icon="checkCircle" tone="green" label="Completed visits" value={dr.stats.completed} />
          <Stat icon="award" tone="amber" label="Experience" value={dr.years_experience != null ? `${dr.years_experience} years` : "Not added"} />
        </div>
      )}

      <div className="pf-grid">
        {!own && about}
        {own && (
          <Card icon="clipboard" tone="blue" title="Today's schedule">
            {dr.today.length ? dr.today.map((a) => (
              <Link key={a.id} to={`/profile/${a.patient_user_id}`} className="pf-slot">
                <span className="pf-slot-time">{fmtDate(a.start_time, { hour: "2-digit", minute: "2-digit" })}</span>
                <Avatar name={a.patient} size={34} seed={a.patient_user_id} />
                <span className="pf-event-text"><b>{a.patient}</b><span>{a.reason || "Appointment"}</span></span>
                <span className={`pf-pill status-${a.status}`}>{STATUS[a.status] || a.status}</span>
              </Link>
            )) : <p className="pf-empty-block">No appointments today.</p>}
          </Card>
        )}

        {own && (
          <Card icon="calendar" tone="teal" title="Coming up">
            {dr.upcoming.length ? dr.upcoming.map((a) => (
              <Link key={a.id} to={`/profile/${a.patient_user_id}`} className="pf-slot">
                <span className="pf-date"><b>{fmtDate(a.start_time, { day: "numeric" })}</b>{fmtDate(a.start_time, { month: "short" })}</span>
                <span className="pf-event-text"><b>{a.patient}</b><span>{fmtDate(a.start_time, { weekday: "short", hour: "2-digit", minute: "2-digit" })} · {a.reason || "Appointment"}</span></span>
              </Link>
            )) : <p className="pf-empty-block">No upcoming appointments.</p>}
          </Card>
        )}

        <Card icon="clock" tone="teal" title="Working hours">
          <div className="pf-week">
            {DAYS.map((d, i) => (
              <span key={d} className={`pf-day ${days[i] ? "on" : ""} ${i === todayIdx ? "today" : ""}`}>
                <b>{d}</b>{days[i] ? `${hhmm(days[i].start_time)}–${hhmm(days[i].end_time)}` : "Off"}
              </span>
            ))}
          </div>
          <Row icon="mail" label="Email">{p.email}</Row>
          {p.is_me && <Row icon="user" label="Username">{p.username}</Row>}
          <Row icon="phone" label="Phone">{p.phone}</Row>
          <Row icon="clock" label="Joined">{dr.registered_on && fmtDate(dr.registered_on, day)}</Row>
        </Card>

        {own && about}
      </div>
    </>
  );
}

function AccountCard({ p }) {
  return (
    <Card icon="user" tone="blue" title="Account">
      <Row icon="mail" label="Email">{p.email}</Row>
      {p.is_me && <Row icon="user" label="Username">{p.username}</Row>}
      <Row icon="phone" label="Phone">{p.phone}</Row>
      <Row icon="clock" label="Member since">{p.member_since && fmtDate(p.member_since, day)}</Row>
      {p.last_login && <Row icon="activity" label="Last sign-in">{fmtDate(p.last_login, { ...day, hour: "2-digit", minute: "2-digit" })}</Row>}
    </Card>
  );
}

function AdminView({ p }) {
  const a = p.admin;
  const u = a.users || {};
  return (
    <>
      <div className="pf-stats">
        <Stat icon="users" tone="violet" label="People" value={a.active_users}>
          <span className="pf-stat-sub">{u.patient || 0} patients · {u.clinical || 0} doctors</span>
        </Stat>
        <Stat icon="shield" tone="rose" label="Doctor requests" value={a.pending_requests} />
        <Stat icon="calendar" tone="teal" label="Visits today" value={a.today_visits} />
        <Stat icon="receipt" tone="amber" label="Unpaid invoices" value={a.unpaid_invoices} />
      </div>
      <div className="pf-grid">
        <AccountCard p={p} />
        <Card icon="activity" tone="violet" title="Recent activity">
          {a.recent_activity.length ? a.recent_activity.map((x, i) => (
            <div key={i} className="pf-line">
              <span className="pf-line-text"><b>{x.action} <code>{x.path}</code></b>
                <small>{x.user || "Anonymous"} · {fmtDate(x.created_at, { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" })}</small>
              </span>
              <span className={`pf-pill ${x.status_code < 400 ? "status-completed" : "status-no_show"}`}>{x.status_code}</span>
            </div>
          )) : <p className="pf-empty-block">Nothing logged yet.</p>}
          <p className="pf-note"><Link to="/admin?tab=audit">Open the full audit log</Link></p>
        </Card>
      </div>
    </>
  );
}

function Profile() {
  const userId = useParams()["*"];
  const nav = null; // the app header and sidebar already carry Home, theme and Sign out
  const [p, setP] = useState(null);
  const [error, setError] = useState("");
  const [dialog, setDialog] = useState(null); // "edit" | "avatar" | "cover"

  useEffect(() => {
    setP(null); setError("");
    api(userId ? `/profile/${userId}/` : "/profile/")
      .then((data) => { setP(data); document.title = `${data.full_name} · OncoSphere`; })
      .catch((e) => setError(e?.status === 404 ? "This profile isn't available." : errorText(e)));
  }, [userId]);

  // the header shows your name and photo, so tell the app shell to refresh them
  const changed = (data) => { setP(data); window.dispatchEvent(new Event("oncosphere:me-changed")); };

  if (error || !p) return (
    <div className="pf" aria-busy={!error}>
      <div className="pf-cover">{nav}</div>
      <div className="page"><p className={error ? "pf-empty-block" : "hint"}>{error || "Loading profile…"}</p></div>
    </div>
  );

  return (
    <div className="pf">
      <Header p={p} nav={nav} onPhoto={setDialog} onEdit={() => setDialog("edit")} />
      <div className="pf-body">
        {p.patient && <PatientView p={p} />}
        {p.doctor && <DoctorView p={p} />}
        {p.admin && <AdminView p={p} />}
        {!p.patient && !p.doctor && !p.admin && (
          <div className="pf-grid"><AccountCard p={p} /></div>
        )}
      </div>
      {dialog === "edit" && <EditDialog p={p} onClose={() => setDialog(null)} onSaved={changed} />}
      {(dialog === "avatar" || dialog === "cover") &&
        <PhotoDialog p={p} kind={dialog} onClose={() => setDialog(null)} onSaved={changed} />}
    </div>
  );
}

// nav: false keeps it out of the sidebar (it opens from your name in the header); hero: false hides the page
// banner (the profile draws its own cover). It shows inside the normal app header and sidebar.
export default { id: "profile", label: "My profile", order: 99, roles: ["patient", "clinical", "admin"], nav: false, hero: false, Component: Profile };
