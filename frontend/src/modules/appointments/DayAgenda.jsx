// One day, in time order: each visit with the buttons it needs, and (for one doctor) the free gaps between them.
import { useEffect, useState } from "react";
import { api } from "../../api.js";
import { Icon } from "../../shared/Icon.jsx";
import { Badge, useList } from "../../shared/ui.jsx";
import { useQueryState } from "../../shared/url.js";
import { ActionButtons, DoctorFilter, addDays, hhmm, isYmd, longDay, parseYmd, todayYmd } from "./shared.jsx";

/** Join back-to-back free slots into ranges: 10:30–12:00. */
function freeRanges(slots) {
  const out = [];
  for (const s of slots) {
    const last = out[out.length - 1];
    if (last && last.end_time === s.start_time) last.end_time = s.end_time;
    else out.push({ ...s, free: true });
  }
  return out;
}

export function DayAgenda({ doctors, doctor, setDoctor, ask, onMove, version }) {
  const today = todayYmd();
  const [raw, setDay] = useQueryState("day", today, { replace: true });
  const day = isYmd(raw) ? raw : today;
  const one = doctor !== "all";
  const [rows, load] = useList(`/appointments/?date=${day}${one ? `&doctor=${doctor}` : ""}`);
  const [free, setFree] = useState([]);
  useEffect(() => { if (version) load(); }, [version]);
  useEffect(() => {
    setFree([]);
    if (!one || day < today) return;
    api(`/doctors/${doctor}/slots/?date=${day}`).then((r) => setFree(freeRanges(r.slots))).catch(() => {});
  }, [doctor, day, version]);

  const items = [...rows, ...free].sort((a, b) => new Date(a.start_time) - new Date(b.start_time));
  const count = (s) => rows.filter((a) => a.status === s).length;

  return (
    <>
      <div className="ap-toolbar">
        <div className="ap-daynav">
          <button className="icon-btn" onClick={() => setDay(addDays(day, -1))} aria-label="Previous day">‹</button>
          <button className={day === today ? "on" : ""} onClick={() => setDay(today)}>Today</button>
          <button className="icon-btn" onClick={() => setDay(addDays(day, 1))} aria-label="Next day">›</button>
        </div>
        <h2 className="ap-day-h">{longDay(parseYmd(day))}</h2>
        <span className="spacer" />
        <input type="date" value={day} aria-label="Pick a day" onChange={(e) => isYmd(e.target.value) && setDay(e.target.value)} />
        <DoctorFilter doctors={doctors} value={doctor} onChange={setDoctor} />
      </div>

      <div className="ap-stats">
        <span><b>{rows.length}</b> visits</span>
        <span className="s-scheduled"><b>{count("scheduled")}</b> waiting</span>
        <span className="s-completed"><b>{count("completed")}</b> completed</span>
        <span className="s-no_show"><b>{count("no_show")}</b> no-show</span>
        {count("cancelled") > 0 && <span><b>{count("cancelled")}</b> cancelled</span>}
      </div>

      {!items.length ? (
        <div className="ap-empty card"><Icon name="calendar" /> No visits on this day{one && day < today ? "" : one ? " and no free time either" : ""}.</div>
      ) : (
        <ol className="ap-agenda">
          {items.map((a) => a.free ? (
            <li key={`free-${a.start_time}`} className="ap-free">
              <span className="ap-agenda-time">{hhmm(a.start_time)}</span>
              <span className="ap-free-line">Free until {hhmm(a.end_time)}</span>
            </li>
          ) : (
            <li key={a.id} className={`ap-visit s-${a.status}`}>
              <span className="ap-agenda-time">{hhmm(a.start_time)}<small>{hhmm(a.end_time)}</small></span>
              <div className="ap-visit-card">
                <div className="ap-visit-main">
                  <b>{a.patient_name}</b> <small>{a.patient_mrn}</small>
                  <span className="ap-visit-meta">{a.reason || "No reason given"}{!one && ` · ${a.doctor_name}`}</span>
                </div>
                <Badge s={a.status} />
                <ActionButtons a={a} staff ask={ask} onMove={onMove} />
              </div>
            </li>
          ))}
        </ol>
      )}
    </>
  );
}
