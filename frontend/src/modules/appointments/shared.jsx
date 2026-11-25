// Pieces every appointments view uses: date helpers, the reasons list, and the confirm-then-act flow for
// cancel / completed / no-show (one popup, the same wording everywhere).
import { useState } from "react";
import { api } from "../../api.js";
import { ConfirmDialog } from "../../shared/ConfirmDialog.jsx";
import { errorText } from "../../shared/ui.jsx";

export const STATUSES = ["scheduled", "completed", "cancelled", "no_show"];
export const DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];

// reasons offered when booking; "Other" lets the person type their own
export const REASONS = [
  { label: "Consultation", icon: "stethoscope", text: "First visit or a new concern" },
  { label: "Follow-up visit", icon: "checkCircle", text: "Check progress with your doctor" },
  { label: "Chemotherapy session", icon: "droplet", text: "A planned treatment cycle" },
  { label: "Radiotherapy session", icon: "target", text: "A planned radiation session" },
  { label: "Imaging / scan", icon: "image", text: "CT, MRI, X-ray or ultrasound" },
  { label: "Lab results review", icon: "microscope", text: "Go over test results" },
  { label: "Other", icon: "pencil", text: "Tell us in a few words" },
];

// ---- dates (always local time; YYYY-MM-DD strings for days) ----
export const ymd = (d) => d.toLocaleDateString("en-CA");
export const todayYmd = () => ymd(new Date());
export const parseYmd = (s) => { const [y, m, d] = s.split("-").map(Number); return new Date(y, m - 1, d); };
export const addDays = (s, n) => { const d = parseYmd(s); d.setDate(d.getDate() + n); return ymd(d); };
export const mondayOf = (s) => { const d = parseYmd(s); return addDays(s, -((d.getDay() + 6) % 7)); };
export const isYmd = (s) => /^\d{4}-\d{2}-\d{2}$/.test(s) && !Number.isNaN(parseYmd(s).getTime());
export const hhmm = (iso) => new Date(iso).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
export const longDay = (iso) => new Date(iso).toLocaleDateString([], { weekday: "long", day: "numeric", month: "long" });
export const shortDay = (iso) => new Date(iso).toLocaleDateString([], { weekday: "short", day: "numeric", month: "short" });
export const when = (a) => `${shortDay(a.start_time)}, ${hhmm(a.start_time)}–${hhmm(a.end_time)}`;

/** "Today", "Tomorrow" or nothing, for a timestamp. */
export function relDay(iso) {
  const day = ymd(new Date(iso)), t = todayYmd();
  return day === t ? "Today" : day === addDays(t, 1) ? "Tomorrow" : "";
}

export const isFuture = (a) => new Date(a.start_time) > new Date();
export const isOpen = (a) => a.status === "scheduled";

// ---- confirm popups for the status actions ----
const ACTIONS = {
  cancel: {
    tone: "danger", icon: "x", confirmLabel: "Cancel appointment", cancelLabel: "Keep it", done: "Appointment cancelled.",
    title: () => "Cancel this appointment?",
    message: (a) => `${when(a)} with ${a.doctor_name}. The time goes back to the free slots.`,
    run: (a) => api(`/appointments/${a.id}/cancel/`, { method: "POST" }),
  },
  completed: {
    tone: "ok", icon: "checkCircle", confirmLabel: "Mark completed", done: "Marked completed.",
    title: () => "Mark this visit completed?",
    message: (a) => `${a.patient_name} · ${when(a)}.`,
    run: (a) => api(`/appointments/${a.id}/`, { method: "PATCH", body: { status: "completed" } }),
  },
  no_show: {
    tone: "danger", icon: "user", confirmLabel: "Mark no-show", done: "Marked no-show.",
    title: () => "Patient did not come?",
    message: (a) => `${a.patient_name} · ${when(a)}. This can't be undone.`,
    run: (a) => api(`/appointments/${a.id}/`, { method: "PATCH", body: { status: "no_show" } }),
  },
};

/** Returns [ask(kind, appointment), popupElement]. ask() opens the popup; confirming runs the action. */
export function useConfirmAction(onDone, onError) {
  const [pending, setPending] = useState(null);
  const ask = (kind, a) => setPending({ kind, a });
  let popup = null;
  if (pending) {
    const { kind, a } = pending, act = ACTIONS[kind];
    popup = (
      <ConfirmDialog tone={act.tone} icon={act.icon} title={act.title(a)} message={act.message(a)}
        confirmLabel={act.confirmLabel} cancelLabel={act.cancelLabel || "Not now"} onCancel={() => setPending(null)}
        onConfirm={() => { setPending(null); act.run(a).then(() => onDone(act.done)).catch((e) => onError(errorText(e))); }} />
    );
  }
  return [ask, popup];
}

/** The buttons a row / agenda item shows, depending on status, time and role. */
export function ActionButtons({ a, staff, ask, onMove }) {
  if (!isOpen(a)) return null;
  const future = isFuture(a);
  return (
    <span className="ap-actions">
      {future && <button className="sm" onClick={() => onMove(a)}>Reschedule</button>}
      {future && <button className="sm danger" onClick={() => ask("cancel", a)}>Cancel</button>}
      {!future && staff && <>
        <button className="sm ap-ok" onClick={() => ask("completed", a)}>Completed</button>
        <button className="sm danger" onClick={() => ask("no_show", a)}>No-show</button>
      </>}
    </span>
  );
}

/** Doctor filter used by the agenda and the week: "All doctors" or one. */
export function DoctorFilter({ doctors, value, onChange }) {
  return (
    <label className="ap-inline">Doctor
      <select value={value} onChange={(e) => onChange(e.target.value)}>
        <option value="all">All doctors</option>
        {doctors.map((d) => <option key={d.id} value={d.id}>{d.name}{d.is_me ? " (me)" : ""}</option>)}
      </select>
    </label>
  );
}
