// The full list: status chips and a day filter (kept in the URL), then a table with the actions each row allows.
import { useEffect } from "react";
import { useSearchParams } from "react-router-dom";
import { Avatar } from "../../shared/Avatar.jsx";
import { Icon } from "../../shared/Icon.jsx";
import { Badge, Table, useList } from "../../shared/ui.jsx";
import { useQueryState } from "../../shared/url.js";
import { ActionButtons, STATUSES, hhmm, isYmd, relDay, shortDay } from "./shared.jsx";

const CHIPS = [["", "All"], ["upcoming", "Upcoming"], ...STATUSES.map((s) => [s, s === "no_show" ? "No-show" : s[0].toUpperCase() + s.slice(1)])];

export function AppointmentList({ staff, ask, onMove, onBook, version }) {
  const [, setSearch] = useSearchParams();
  const [rawStatus, setStatus] = useQueryState("status", "", { replace: true });
  const [rawDate, setDate] = useQueryState("date", "", { replace: true });
  // a hand-edited URL with a bad value is ignored instead of sent to the API
  const status = CHIPS.some(([v]) => v === rawStatus) ? rawStatus : "";
  const date = isYmd(rawDate) ? rawDate : "";
  const q = new URLSearchParams();
  if (status === "upcoming") q.set("upcoming", "1"); else if (status) q.set("status", status);
  if (date) q.set("date", date);
  const [rows, load] = useList(`/appointments/?${q}`);
  useEffect(() => { if (version) load(); }, [version]); // re-read after an action on the page

  return (
    <>
      <div className="ap-toolbar">
        <div className="ap-chips" role="group" aria-label="Status">
          {CHIPS.map(([v, label]) => (
            <button key={v || "all"} type="button" className={status === v ? "on" : ""} aria-pressed={status === v}
                    onClick={() => setStatus(v)}>{label}</button>
          ))}
        </div>
        <span className="spacer" />
        <label className="ap-inline">Day<input type="date" value={date} onChange={(e) => setDate(e.target.value)} /></label>
        {(status || date) && <button className="ghost sm" onClick={() => setSearch((cur) => { const n = new URLSearchParams(cur); n.delete("status"); n.delete("date"); return n; }, { replace: true })}>Clear</button>}
        {onBook && <button className="primary with-icon" onClick={onBook}><Icon name="calendar" /> Book a visit</button>}
      </div>
      <p className="hint ap-count">{rows.length} appointment{rows.length === 1 ? "" : "s"}</p>
      <Table head={["When", "Doctor", ...(staff ? ["Patient"] : []), "Reason", "Status", ""]}
        empty={status || date ? "No appointments match these filters." : "No appointments yet."}
        rows={rows.map((a) => {
          const rel = relDay(a.start_time);
          return (
            <tr key={a.id} className={a.status === "cancelled" ? "ap-row-muted" : ""}>
              <td>
                <b>{shortDay(a.start_time)}</b>{rel && <span className="ap-rel">{rel}</span>}
                <br /><small>{hhmm(a.start_time)}–{hhmm(a.end_time)}</small>
              </td>
              <td><span className="ap-person"><Avatar name={a.doctor_name.replace(/^Dr\.\s*/, "")} seed={a.doctor} size={28} />{a.doctor_name}</span></td>
              {staff && <td>{a.patient_name}<br /><small>{a.patient_mrn}</small></td>}
              <td>{a.reason || "—"}</td>
              <td><Badge s={a.status} /></td>
              <td><ActionButtons a={a} staff={staff} ask={ask} onMove={onMove} /></td>
            </tr>
          );
        })} />
    </>
  );
}
