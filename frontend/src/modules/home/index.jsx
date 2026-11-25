// The Home page everybody lands on after signing in. For each role it shows what matters first:
// a main action, a few live numbers, the next things to deal with (visits, bills, requests),
// and shortcuts to the other pages. Every request is optional: one that fails just leaves its piece out.
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../../api.js";
import { Icon } from "../../shared/Icon.jsx";
import { money } from "../billing/money.js";
import "./home.css";

const ABOUT = {
  appointments: "Book, reschedule and track visits.",
  records: "Medical records, plans and orders.",
  billing: "Invoices, payments and receipts.",
  imaging: "Scans and the image viewer.",
  reports: "Key numbers and trends.",
  hl7: "Messages exchanged with other systems.",
  admin: "Doctor requests, staff, settings and the audit log.",
};
const ICONS = { appointments: "calendar", records: "clipboard", billing: "receipt", imaging: "image", reports: "barChart", hl7: "activity", admin: "shield" };

const localDay = () => {
  const d = new Date();
  d.setMinutes(d.getMinutes() - d.getTimezoneOffset());
  return d.toISOString().slice(0, 10);
};
const hello = () => {
  const h = new Date().getHours();
  return h < 12 ? "Good morning" : h < 18 ? "Good afternoon" : "Good evening";
};
const dateLong = new Intl.DateTimeFormat(undefined, { weekday: "long", day: "numeric", month: "long" });
const time = (v) => new Date(v).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
const dayName = (v) => {
  const d = new Date(v), t = new Date();
  const diff = Math.round((new Date(d.getFullYear(), d.getMonth(), d.getDate()) - new Date(t.getFullYear(), t.getMonth(), t.getDate())) / 864e5);
  return diff === 0 ? "Today" : diff === 1 ? "Tomorrow" : d.toLocaleDateString([], { weekday: "short" });
};
const get = (path) => api(path).then((r) => (Array.isArray(r) ? r : r?.results || [])).catch(() => null);
const pending = (rows) => rows.filter((i) => i.status === "pending");
const owed = (i) => Number(i.total_amount) - Number(i.paid_amount);
const initials = (n = "") => n.split(" ").filter(Boolean).slice(0, 2).map((w) => w[0]).join("").toUpperCase();

/** A visit as a list row: date block, who/what, time. */
const visitItem = (a, who) => ({
  key: `a${a.id}`, to: "/appointments", date: a.start_time,
  title: who === "doctor" ? a.doctor_name : a.patient_name,
  sub: [a.reason, who === "both" ? `with ${a.doctor_name}` : ""].filter(Boolean).join(" · "),
  right: `${dayName(a.start_time)}, ${time(a.start_time)}`,
});
const billItem = (i, staff) => ({
  key: `i${i.id}`, to: `/billing?receipt=${i.id}`, icon: "receipt",
  title: staff ? i.patient_name : i.invoice_number,
  sub: staff ? `${i.invoice_number} · ${i.items.map((x) => x.service_name).join(", ")}` : i.items.map((x) => x.service_name).join(", "),
  right: money(owed(i)), strong: true,
});

/** What to show per role. Returns { action, stats, panels } */
async function load(role) {
  const scheduled = (a) => a.filter((x) => x.status === "scheduled");
  if (role === "patient") {
    const [appts, inv] = await Promise.all([get("/appointments/?upcoming=1"), get("/invoices/")]);
    const up = appts ? scheduled(appts) : null, due = inv ? pending(inv) : null;
    return {
      action: { label: "Book an appointment", to: "/appointments", icon: "calendar" },
      stats: [
        up && { icon: "calendar", tone: "primary", label: "Next appointment", value: up[0] ? `${dayName(up[0].start_time)}, ${time(up[0].start_time)}` : "None booked", hint: up[0] ? `with ${up[0].doctor_name}` : "Book one in a minute", to: "/appointments" },
        up && { icon: "clock", tone: "info", label: "Upcoming visits", value: up.length, to: "/appointments" },
        due && { icon: "receipt", tone: due.length ? "warn" : "ok", label: "To pay", value: due.length ? money(due.reduce((s, i) => s + owed(i), 0)) : "All paid", hint: due.length ? `${due.length} invoice(s)` : "", to: "/billing?status=pending" },
      ],
      panels: [
        up && { title: "Your upcoming visits", to: "/appointments", more: "All appointments", empty: "No visits booked yet.", items: up.slice(0, 4).map((a) => visitItem(a, "doctor")) },
        due && { title: "Bills to pay", to: "/billing?status=pending", more: "All invoices", empty: "Nothing to pay. You're all set.", items: due.slice(0, 4).map((i) => billItem(i, false)) },
      ],
    };
  }
  if (role === "clinical") {
    const [today, up] = await Promise.all([get(`/appointments/?date=${localDay()}`), get("/appointments/?upcoming=1")]);
    const t = today ? scheduled(today) : null, u = up ? scheduled(up) : null;
    return {
      action: { label: "Open my schedule", to: "/appointments", icon: "calendar" },
      stats: [
        t && { icon: "stethoscope", tone: "primary", label: "Today's visits", value: t.length, hint: t[0] ? `First at ${time(t[0].start_time)}` : "A free day", to: "/appointments" },
        u && { icon: "clock", tone: "info", label: "Upcoming visits", value: u.length, to: "/appointments" },
      ],
      panels: [
        t && { title: "Today's patients", to: "/appointments", more: "Full schedule", empty: "No visits today.", items: t.slice(0, 6).map((a) => visitItem(a, "patient")) },
        u && { title: "Coming up", to: "/appointments", more: "All appointments", empty: "No upcoming visits.", items: u.filter((a) => !t || !t.some((x) => x.id === a.id)).slice(0, 5).map((a) => visitItem(a, "patient")) },
      ],
    };
  }
  if (role === "finance") {
    const inv = await get("/invoices/");
    if (!inv) return { stats: [], panels: [] };
    const due = pending(inv);
    return {
      action: { label: "Open invoices", to: "/billing", icon: "receipt" },
      stats: [
        { icon: "receipt", tone: due.length ? "warn" : "ok", label: "Unpaid invoices", value: due.length, to: "/billing?status=pending" },
        { icon: "barChart", tone: "danger", label: "Amount owed", value: money(due.reduce((s, i) => s + owed(i), 0)), to: "/billing?status=pending" },
        { icon: "checkCircle", tone: "ok", label: "Paid invoices", value: inv.filter((i) => i.status === "paid").length, to: "/billing?status=paid" },
      ],
      panels: [{ title: "Waiting for payment", to: "/billing?status=pending", more: "All unpaid", empty: "Everything is paid.", items: due.slice(0, 6).map((i) => billItem(i, true)) }],
    };
  }
  // admin
  const [reqs, up, inv] = await Promise.all([get("/admin/doctor-requests/?status=pending"), get("/appointments/?upcoming=1"), get("/invoices/")]);
  const u = up ? scheduled(up) : null, due = inv ? pending(inv) : null;
  return {
    action: reqs && reqs.length ? { label: `Review ${reqs.length} doctor request${reqs.length > 1 ? "s" : ""}`, to: "/admin?tab=requests", icon: "users" } : { label: "Book for a patient", to: "/appointments", icon: "calendar" },
    stats: [
      reqs && { icon: "users", tone: reqs.length ? "danger" : "ok", label: "Doctor requests", value: reqs.length, hint: reqs.length ? "Waiting for a decision" : "Nothing waiting", to: "/admin?tab=requests" },
      u && { icon: "calendar", tone: "primary", label: "Upcoming visits", value: u.length, to: "/appointments" },
      due && { icon: "receipt", tone: due.length ? "warn" : "ok", label: "Unpaid invoices", value: due.length, to: "/billing?status=pending" },
    ],
    panels: [
      reqs && { title: "Doctor requests", to: "/admin?tab=requests", more: "Review all", empty: "No requests are waiting.", items: reqs.slice(0, 4).map((r) => ({ key: `r${r.id}`, to: "/admin?tab=requests", initials: initials(r.name), title: `Dr. ${r.name}`, sub: [r.doctor?.specialty, r.doctor?.license_no].filter(Boolean).join(" · "), right: new Date(r.submitted_at).toLocaleDateString([], { day: "numeric", month: "short" }) })) },
      u && { title: "Upcoming visits", to: "/appointments", more: "All appointments", empty: "No upcoming visits.", items: u.slice(0, 5).map((a) => visitItem(a, "both")) },
    ],
  };
}

function Row({ it }) {
  const d = it.date ? new Date(it.date) : null;
  return (
    <Link to={it.to} className="hm-row">
      {d ? <span className="hm-date"><b>{d.getDate()}</b>{d.toLocaleDateString([], { month: "short" })}</span>
        : it.initials ? <span className="hm-badge">{it.initials}</span>
        : <span className="hm-badge"><Icon name={it.icon || "layers"} size={18} /></span>}
      <span className="hm-row-main"><b>{it.title}</b><small>{it.sub}</small></span>
      <span className={`hm-row-right${it.strong ? " strong" : ""}`}>{it.right}</span>
    </Link>
  );
}

function Home({ me, links = [] }) {
  const [data, setData] = useState(null);
  useEffect(() => { load(me.role).then(setData); }, [me.role]);
  const name = me.first_name || me.username;
  const stats = (data?.stats || []).filter(Boolean), panels = (data?.panels || []).filter(Boolean);
  return (
    <>
      <section className="page-hero">
        <div className="page-hero-in">
          <div className="page-hero-text">
            <h1>{hello()}, {name}</h1>
            <p>{dateLong.format(new Date())} · here is what needs your attention.</p>
          </div>
          {data?.action && (
            <Link to={data.action.to} className="hm-cta"><Icon name={data.action.icon} size={18} />{data.action.label}</Link>
          )}
        </div>
      </section>

      <div className="page home">
        {!data && <div className="hm-stats" aria-busy="true">{[0, 1, 2].map((i) => <div key={i} className="card hm-stat skeleton" style={{ minHeight: 96 }} />)}</div>}

        {stats.length > 0 && (
          <div className="hm-stats">
            {stats.map((s) => (
              <Link key={s.label} to={s.to} className={`card hm-stat t-${s.tone}`}>
                <span className="hm-stat-icon"><Icon name={s.icon} size={22} /></span>
                <span className="hm-stat-text">
                  <small>{s.label}</small>
                  <b>{s.value}</b>
                  {s.hint && <em>{s.hint}</em>}
                </span>
              </Link>
            ))}
          </div>
        )}

        {panels.length > 0 && (
          <div className="hm-panels">
            {panels.map((p) => (
              <section key={p.title} className="card hm-panel">
                <header><h2>{p.title}</h2><Link to={p.to}>{p.more} <Icon name="arrowRight" size={14} /></Link></header>
                {p.items.length ? p.items.map((it) => <Row key={it.key} it={it} />) : <p className="hm-empty">{p.empty}</p>}
              </section>
            ))}
          </div>
        )}

        {links.length > 0 && (
          <>
            <h2 className="hm-h">Shortcuts</h2>
            <div className="hm-links">
              {links.map((m) => (
                <Link key={m.id} to={`/${m.id}`} className="card hm-link">
                  <span className="hm-link-icon"><Icon name={ICONS[m.id] || "layers"} size={20} /></span>
                  <span><b>{m.label}</b><small>{m.description || ABOUT[m.id] || ""}</small></span>
                </Link>
              ))}
            </div>
          </>
        )}
      </div>
    </>
  );
}

export default {
  id: "home", label: "Home", order: 0, roles: ["patient", "clinical", "admin", "finance"], hero: false, Component: Home,
};
