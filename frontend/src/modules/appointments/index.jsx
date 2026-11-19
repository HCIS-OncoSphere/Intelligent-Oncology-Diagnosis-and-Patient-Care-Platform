// appointments/ (doctors, availability, appointments). Feature F3.
// Patients book their own visits from the doctor's free slots; admins book for any patient; staff filter the list,
// mark visits completed / no-show, reschedule, cancel and see tomorrow's reminder list.
// Weekly availability: admins set any doctor's hours, each doctor sets only their own.
import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { api } from "../../api.js";
import { Badge, Msg, Table, errorText, useList } from "../../shared/ui.jsx";
import { useQueryState } from "../../shared/url.js";

const STATUSES = ["scheduled", "completed", "cancelled", "no_show"];
// reasons offered in the booking form; "Other" lets the user type their own
const REASONS = ["Consultation", "Follow-up visit", "Chemotherapy session", "Radiotherapy session", "Imaging / scan",
  "Lab results review", "Other"];
const DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];
const today = () => new Date().toLocaleDateString("en-CA"); // YYYY-MM-DD in local time
const hhmm = (iso) => new Date(iso).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
const day = (iso) => new Date(iso).toLocaleDateString([], { weekday: "short", day: "numeric", month: "short", year: "numeric" });
const when = (a) => `${day(a.start_time)}, ${hhmm(a.start_time)}–${hhmm(a.end_time)}`;

/** Pick a doctor + day and click one of the free slots returned by GET /doctors/{id}/slots/. */
function SlotPicker({ doctors, doctor, setDoctor, onPick, label, lockDoctor }) {
  const [date, setDate] = useState(today()), [slots, setSlots] = useState(null), [err, setErr] = useState("");
  const [reload, setReload] = useState(0), [now, setNow] = useState(Date.now());
  useEffect(() => {
    if (!doctor || !date) return;
    setErr("");
    api(`/doctors/${doctor}/slots/?date=${date}`).then((r) => setSlots(r.slots)).catch((e) => { setSlots([]); setErr(errorText(e)); });
  }, [doctor, date, reload]);
  // slots whose time has passed disappear while the page stays open
  useEffect(() => { const t = setInterval(() => setNow(Date.now()), 30000); return () => clearInterval(t); }, []);
  const free = slots && slots.filter((s) => new Date(s.start_time).getTime() > now);

  // the clicked slot disappears at once (no waiting for the server); the list is then re-read to stay exact
  const choose = async (slot) => {
    setSlots((cur) => cur.filter((x) => x.start_time !== slot.start_time));
    try { await onPick(slot); } finally { setReload((n) => n + 1); }
  };
  const dr = doctors.find((d) => String(d.id) === String(doctor));
  return (
    <>
      <div className="form-row">
        <label>Doctor
          <select value={doctor} disabled={lockDoctor} onChange={(e) => setDoctor(e.target.value)}>
            {doctors.map((d) => <option key={d.id} value={d.id}>{d.name} ({d.specialty})</option>)}
          </select>
        </label>
        <label>Day<input type="date" value={date} min={today()} onChange={(e) => setDate(e.target.value)} /></label>
      </div>
      {dr?.availability?.length > 0 && (
        <p className="hint">Works {dr.availability.map((w) => `${DAYS[w.day_of_week].slice(0, 3)} ${w.start_time.slice(0, 5)}–${w.end_time.slice(0, 5)}`).join(" · ")}</p>
      )}
      <div className="slots">
        {free === null ? <span className="empty-note">Choose a doctor and a day.</span>
          : free.length === 0 ? <span className="empty-note">{err || "No free slots on this day. Try another day."}</span>
          : free.map((s) => <button key={s.start_time} className="slot" onClick={() => choose(s)} title={label}>{hhmm(s.start_time)}</button>)}
      </div>
    </>
  );
}

function Availability({ me, doctors, reloadDoctors }) {
  // admins manage every doctor's hours; a doctor manages only their own
  const admin = me.role === "admin";
  const own = doctors.find((d) => d.is_me);
  const [picked, setDoctor] = useState(doctors[0]?.id || "");
  const doctor = admin ? picked || doctors[0]?.id || "" : own?.id || "";
  const [rows, load] = useList(doctor ? `/availability/?doctor=${doctor}` : "/availability/?doctor=0");
  const [f, setF] = useState({ day_of_week: "0", start_time: "09:00", end_time: "17:00" }), [msg, setMsg] = useState({});
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });
  const done = (text) => { setMsg({ ok: true, text }); load(); reloadDoctors(); };
  const add = () => api("/availability/", { method: "POST", body: { ...f, doctor } }).then(() => done("Window added.")).catch((e) => setMsg({ text: errorText(e) }));
  const del = (w) => api(`/availability/${w.id}/`, { method: "DELETE" }).then(() => done("Window removed.")).catch((e) => setMsg({ text: errorText(e) }));
  if (!admin && !own) {
    return <p className="hint">{doctors.length ? "Your account has no doctor profile, so there are no working hours to set. Ask an admin." : "Loading…"}</p>;
  }
  return (
    <>
      <fieldset>
        <legend>{admin ? "Add a working window" : "My working hours"}</legend>
        <div className="form-row">
          <label>Doctor<select value={doctor} disabled={!admin} onChange={(e) => setDoctor(e.target.value)}>{doctors.map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}</select></label>
          <label>Day<select value={f.day_of_week} onChange={set("day_of_week")}>{DAYS.map((d, i) => <option key={d} value={i}>{d}</option>)}</select></label>
          <label>From<input type="time" value={f.start_time} onChange={set("start_time")} /></label>
          <label>To<input type="time" value={f.end_time} onChange={set("end_time")} /></label>
          <button className="primary" onClick={add} disabled={!doctor}>Add window</button>
        </div>
        <Msg m={msg} />
      </fieldset>
      <Table head={["Day", "From", "To", ""]} empty="No windows yet: this doctor can be booked at any time."
        rows={rows.map((w) => <tr key={w.id}><td>{DAYS[w.day_of_week]}</td><td>{w.start_time.slice(0, 5)}</td><td>{w.end_time.slice(0, 5)}</td>
          <td><button className="danger" onClick={() => del(w)}>Remove</button></td></tr>)} />
    </>
  );
}

function Appointments({ me }) {
  const staff = me.role !== "patient";
  const canBook = me.role !== "clinical"; // patients book for themselves, admins for a patient, doctors do not book
  // view and filters live in the URL: /appointments?view=reminders, /appointments?status=scheduled&date=2026-11-20
  const [, setSearch] = useSearchParams();
  const [rawStatus, setStatus] = useQueryState("status", "", { replace: true });
  const [rawDate, setDate] = useQueryState("date", "", { replace: true });
  const [rawView, setView] = useQueryState("view", "list");
  // a hand-edited URL with a bad value is ignored instead of sent to the API
  const status = STATUSES.includes(rawStatus) ? rawStatus : "";
  const date = /^\d{4}-\d{2}-\d{2}$/.test(rawDate) ? rawDate : "";
  const filter = { status, date };
  const query = new URLSearchParams(Object.entries(filter).filter(([, v]) => v)).toString();
  const [rows, load] = useList(`/appointments/${query ? "?" + query : ""}`);
  const [doctors, setDoctors] = useState([]), [patients, setPatients] = useState([]);
  const [doctor, setDoctor] = useState(""), [patient, setPatient] = useState(""), [reasonChoice, setReasonChoice] = useState(REASONS[0]), [reasonOther, setReasonOther] = useState("");
  const reason = reasonChoice === "Other" ? reasonOther.trim() || "Other" : reasonChoice;
  const [moving, setMoving] = useState(null), [msg, setMsg] = useState({});
  const [reminders, loadReminders] = useList(staff ? "/appointments/reminders/" : "/appointments/?status=__none__");

  const loadDoctors = () => api("/doctors/").then((d) => { setDoctors(d); setDoctor((cur) => cur || (d[0] ? String(d[0].id) : "")); });
  useEffect(() => { loadDoctors().catch(() => {}); if (staff) api("/patients/").then(setPatients).catch(() => {}); }, []);
  const refresh = (text) => { setMsg({ ok: true, text }); load(); if (staff) loadReminders(); };
  const fail = (e) => setMsg({ text: errorText(e) });

  const pick = (slot) => {
    if (moving) {
      return api(`/appointments/${moving.id}/reschedule/`, { method: "POST", body: slot })
        .then(() => { setMoving(null); refresh("Appointment moved."); }).catch(fail);
    }
    if (staff && !patient) return setMsg({ text: "Choose the patient first." });
    const body = { doctor, ...slot, reason, ...(staff ? { patient } : {}) };
    return api("/appointments/", { method: "POST", body }).then(() => refresh(`Booked ${new Date(slot.start_time).toLocaleString()}.`)).catch(fail);
  };
  const act = (a, path, body, text) => api(`/appointments/${a.id}/${path}`, { method: path ? "POST" : "PATCH", body }).then(() => refresh(text)).catch(fail);
  const cancel = (a) => { if (confirm(`Cancel the appointment on ${when(a)}?`)) act(a, "cancel/", undefined, "Appointment cancelled."); };

  const views = { list: "Appointments", availability: "Doctor hours", reminders: `Tomorrow (${reminders.length})` };
  const view = staff && views[rawView] ? rawView : "list"; // patients, or an unknown ?view=, get the list
  return (
    <>
      {staff && (
        <div className="segmented" role="tablist">
          {Object.entries(views).map(([v, label]) => (
            <button key={v} role="tab" className={view === v ? "active" : ""} onClick={() => setView(v)}>{label}</button>
          ))}
        </div>
      )}

      {view === "availability" && staff && <Availability me={me} doctors={doctors} reloadDoctors={loadDoctors} />}

      {view === "reminders" && staff && (
        <>
          <p className="hint">Scheduled appointments for tomorrow, with phone numbers for reminder calls.</p>
          <Table head={["Time", "Patient", "MRN", "Phone", "Doctor", "Reason"]} empty="No appointments tomorrow."
            rows={reminders.map((a) => <tr key={a.id}><td><b>{hhmm(a.start_time)}</b></td><td>{a.patient_name}</td><td>{a.patient_mrn}</td>
              <td>{a.patient_phone || "—"}</td><td>{a.doctor_name}</td><td>{a.reason}</td></tr>)} />
        </>
      )}

      {view === "list" && (
        <>
          {(canBook || moving) ? <fieldset>
            <legend>{moving ? `Reschedule: ${when(moving)}` : "Book an appointment"}</legend>
            {!moving && (
              <div className="form-row">
                {staff && (
                  <label>Patient
                    <select value={patient} onChange={(e) => setPatient(e.target.value)}>
                      <option value="">Choose a patient…</option>
                      {patients.map((p) => <option key={p.id} value={p.id}>{p.name || "(no name)"} · {p.mrn}</option>)}
                    </select>
                  </label>
                )}
                <label>Reason
                  <select value={reasonChoice} onChange={(e) => setReasonChoice(e.target.value)}>
                    {REASONS.map((r) => <option key={r} value={r}>{r}</option>)}
                  </select>
                </label>
                {reasonChoice === "Other" && (
                  <label>Describe the reason<input value={reasonOther} maxLength={200} onChange={(e) => setReasonOther(e.target.value)} placeholder="e.g. new symptom" size="26" /></label>
                )}
              </div>
            )}
            {doctors.length ? (
              <SlotPicker doctors={doctors} doctor={moving ? String(moving.doctor) : doctor} setDoctor={setDoctor} lockDoctor={!!moving}
                onPick={pick} label={moving ? "Move here" : "Book this slot (30 min)"} />
            ) : <p className="hint">No doctors yet. An admin creates a clinical user with a license number.</p>}
            {moving && <button onClick={() => setMoving(null)}>Stop rescheduling</button>}
            <Msg m={msg} />
          </fieldset> : <Msg m={msg} />}

          <div className="form-row">
            <label>Status
              <select value={status} onChange={(e) => setStatus(e.target.value)}>
                <option value="">All</option>{STATUSES.map((s) => <option key={s} value={s}>{s.replace("_", "-")}</option>)}
              </select>
            </label>
            <label>Day<input type="date" value={date} onChange={(e) => setDate(e.target.value)} /></label>
            {(status || date) && <button className="ghost" onClick={() => setSearch({}, { replace: true })}>Clear filters</button>}
          </div>
          <Table head={["When", "Doctor", ...(staff ? ["Patient"] : []), "Reason", "Status", ""]} empty="No appointments found."
            rows={rows.map((a) => {
              const open = a.status === "scheduled", future = new Date(a.start_time) > new Date();
              return (
                <tr key={a.id}>
                  <td><b>{day(a.start_time)}</b><br /><small>{hhmm(a.start_time)}–{hhmm(a.end_time)}</small></td>
                  <td>{a.doctor_name}</td>
                  {staff && <td>{a.patient_name}<br /><small>{a.patient_mrn}</small></td>}
                  <td>{a.reason || "—"}</td><td><Badge s={a.status} /></td>
                  <td>
                    {open && future && <button onClick={() => { setMoving(a); setMsg({}); window.scrollTo({ top: 0, behavior: "smooth" }); }}>Reschedule</button>}
                    {open && <button className="danger" onClick={() => cancel(a)}>Cancel</button>}
                    {open && staff && !future && <>
                      <button onClick={() => act(a, "", { status: "completed" }, "Marked completed.")}>Completed</button>
                      <button onClick={() => act(a, "", { status: "no_show" }, "Marked no-show.")}>No-show</button>
                    </>}
                  </td>
                </tr>
              );
            })} />
        </>
      )}
    </>
  );
}

export default { id: "appointments", label: "Appointments", order: 20, roles: ["patient", "clinical", "admin"], Component: Appointments };
