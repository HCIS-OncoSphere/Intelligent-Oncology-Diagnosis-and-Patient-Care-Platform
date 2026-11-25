// appointments/ (doctors, availability, appointments). Feature F3.
// Patients book their own visits in short steps (reason → doctor → time, then confirm); admins book for any patient.
// Staff work from today's agenda or the week calendar, and can still open the full list, the doctor hours and
// tomorrow's reminder list. Every cancel / completed / no-show asks first in a popup.
import { useEffect, useState } from "react";
import { api } from "../../api.js";
import { Msg, Table, useList } from "../../shared/ui.jsx";
import { useQueryState } from "../../shared/url.js";
import { AppointmentList } from "./AppointmentList.jsx";
import { Availability } from "./Availability.jsx";
import { BookingWizard } from "./BookingWizard.jsx";
import { DayAgenda } from "./DayAgenda.jsx";
import { WeekCalendar } from "./WeekCalendar.jsx";
import { hhmm, useConfirmAction } from "./shared.jsx";
import "./appointments.css";

function Appointments({ me }) {
  const staff = me.role !== "patient";
  const admin = me.role === "admin";
  const canBook = me.role !== "clinical"; // patients book for themselves, admins for a patient, doctors do not

  const [doctors, setDoctors] = useState([]), [patients, setPatients] = useState([]), [nextFree, setNextFree] = useState(null);
  const [moving, setMoving] = useState(null), [msg, setMsg] = useState({}), [version, setVersion] = useState(0);
  const [reminders, loadReminders] = useList(staff ? "/appointments/reminders/" : "/appointments/?status=__none__");

  const loadDoctors = () => api("/doctors/").then(setDoctors);
  const loadNextFree = () => api("/doctors/next-free/").then((r) => setNextFree(Object.fromEntries(r.map((x) => [x.doctor, x])))).catch(() => setNextFree({}));
  useEffect(() => {
    loadDoctors().catch(() => {});
    if (canBook) loadNextFree();
    if (admin) api("/patients/").then(setPatients).catch(() => {});
  }, []);

  // after any change: show the message and re-read everything on screen
  const changed = (text) => { setMsg({ ok: true, text }); setVersion((v) => v + 1); if (staff) loadReminders(); if (canBook) loadNextFree(); };
  const failed = (text) => setMsg({ text });
  const [ask, popup] = useConfirmAction(changed, failed);

  // views live in the URL (?view=week) so refresh and Back keep your place
  const views = staff
    ? { today: "Today", week: "Week", list: "All appointments", ...(admin ? { book: "Book a visit" } : {}),
        hours: admin ? "Doctor hours" : "My hours", reminders: `Tomorrow (${reminders.length})` }
    : { list: "My appointments", book: "Book a visit" };
  const [rawView, setView] = useQueryState("view", staff ? "today" : "list");
  const view = views[rawView] ? rawView : staff ? "today" : "list";

  // agenda and week share one doctor filter; a doctor starts on their own schedule
  const own = doctors.find((d) => d.is_me);
  const [rawDoctor, setDoctor] = useQueryState("doctor", own ? String(own.id) : "all", { replace: true });
  const doctor = rawDoctor === "all" || doctors.some((d) => String(d.id) === rawDoctor) ? rawDoctor : "all";

  const startMove = (a) => { setMoving(a); setMsg({}); window.scrollTo({ top: 0, behavior: "smooth" }); };
  const props = { doctors, doctor, setDoctor, staff, ask, onMove: startMove, version };

  return (
    <>
      <Msg m={msg} />
      {popup}

      {moving ? (
        <BookingWizard me={me} doctors={doctors} moving={moving}
          onDone={(t) => { setMoving(null); changed(t); }} onStopMoving={() => setMoving(null)} />
      ) : (
        <>
          <div className="segmented ap-views" role="tablist">
            {Object.entries(views).map(([v, label]) => (
              <button key={v} role="tab" aria-selected={view === v} className={view === v ? "active" : ""} onClick={() => { setView(v); setMsg({}); }}>{label}</button>
            ))}
          </div>

          {view === "today" && <DayAgenda {...props} />}
          {view === "week" && <WeekCalendar {...props} />}
          {view === "list" && <AppointmentList {...props} onBook={canBook ? () => setView("book") : null} />}
          {view === "book" && canBook && (
            <BookingWizard me={me} doctors={doctors} nextFree={nextFree} patients={patients}
              onDone={(t) => { changed(t); if (!admin) setView("list"); }} />
          )}
          {view === "hours" && <Availability me={me} doctors={doctors} reloadDoctors={loadDoctors} />}
          {view === "reminders" && (
            <>
              <p className="hint">Scheduled appointments for tomorrow, with phone numbers for reminder calls.</p>
              <Table head={["Time", "Patient", "MRN", "Phone", "Doctor", "Reason"]} empty="No appointments tomorrow."
                rows={reminders.map((a) => <tr key={a.id}><td><b>{hhmm(a.start_time)}</b></td><td>{a.patient_name}</td><td>{a.patient_mrn}</td>
                  <td>{a.patient_phone || "—"}</td><td>{a.doctor_name}</td><td>{a.reason}</td></tr>)} />
            </>
          )}
        </>
      )}
    </>
  );
}

export default { id: "appointments", label: "Appointments", order: 20, roles: ["patient", "clinical", "admin"], Component: Appointments };
