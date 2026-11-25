// A week at a glance: days as columns, hours as rows, each visit a block colored by status.
// Click a block to see it and act on it. Visits at the same time (all doctors) sit side by side.
import { useEffect, useMemo, useRef, useState } from "react";
import { Icon } from "../../shared/Icon.jsx";
import { Badge, useList } from "../../shared/ui.jsx";
import { useQueryState } from "../../shared/url.js";
import { ActionButtons, DoctorFilter, addDays, hhmm, isYmd, mondayOf, parseYmd, todayYmd, when, ymd } from "./shared.jsx";

const HOUR = 56; // px per hour

/** Give overlapping visits of one day their own lane: [{a, lane, lanes}] */
function layout(list) {
  const sorted = [...list].sort((x, y) => new Date(x.start_time) - new Date(y.start_time));
  const out = [];
  let group = [], groupEnd = 0;
  const flush = () => { const lanes = Math.max(...group.map((g) => g.lane)) + 1; group.forEach((g) => out.push({ ...g, lanes })); group = []; };
  for (const a of sorted) {
    const s = new Date(a.start_time).getTime(), e = new Date(a.end_time).getTime();
    if (group.length && s >= groupEnd) flush();
    const used = new Set(group.filter((g) => new Date(g.a.end_time).getTime() > s).map((g) => g.lane));
    let lane = 0; while (used.has(lane)) lane++;
    group.push({ a, lane }); groupEnd = Math.max(groupEnd, e);
  }
  if (group.length) flush();
  return out;
}

function VisitDialog({ a, staff, ask, onMove, onClose }) {
  const ref = useRef(null);
  useEffect(() => { ref.current.showModal(); return () => ref.current?.open && ref.current.close(); }, []);
  const act = (fn) => (...args) => { onClose(); fn(...args); };
  return (
    <dialog ref={ref} className="confirm ap-visit-dialog" onClose={onClose} onClick={(e) => e.target === ref.current && onClose()}>
      <h2>{a.patient_name}</h2>
      <p>{a.patient_mrn}</p>
      <ul>
        <li><Icon name="calendar" /> {when(a)}</li>
        <li><Icon name="stethoscope" /> {a.doctor_name}</li>
        <li><Icon name="clipboard" /> {a.reason || "No reason given"}</li>
        <li><Icon name="activity" /> <Badge s={a.status} /></li>
      </ul>
      <div className="ap-visit-dialog-actions">
        <ActionButtons a={a} staff={staff} ask={act(ask)} onMove={act(onMove)} />
        <button type="button" onClick={onClose}>Close</button>
      </div>
    </dialog>
  );
}

export function WeekCalendar({ doctors, doctor, setDoctor, staff, ask, onMove, version }) {
  const today = todayYmd();
  const [raw, setWeek] = useQueryState("week", mondayOf(today), { replace: true });
  const week = mondayOf(isYmd(raw) ? raw : today);
  const days = Array.from({ length: 7 }, (_, i) => addDays(week, i));
  const one = doctor !== "all";
  const [rows, load] = useList(`/appointments/?from=${days[0]}&to=${days[6]}${one ? `&doctor=${doctor}` : ""}`);
  useEffect(() => { if (version) load(); }, [version]);
  const [open, setOpen] = useState(null);

  // hours shown: 08:00–18:00, stretched to fit any visit outside them
  const [from, to] = useMemo(() => {
    let f = 8, t = 18;
    for (const a of rows) {
      const s = new Date(a.start_time), e = new Date(a.end_time);
      f = Math.min(f, s.getHours()); t = Math.max(t, e.getHours() + (e.getMinutes() ? 1 : 0));
    }
    return [f, Math.min(24, t)];
  }, [rows]);
  const byDay = useMemo(() => {
    const m = {};
    for (const a of rows) (m[ymd(new Date(a.start_time))] ||= []).push(a);
    return Object.fromEntries(Object.entries(m).map(([d, list]) => [d, layout(list)]));
  }, [rows]);
  const hours = Array.from({ length: to - from }, (_, i) => from + i);
  const nowLine = days.includes(today) ? (new Date().getHours() + new Date().getMinutes() / 60 - from) * HOUR : null;

  return (
    <>
      <div className="ap-toolbar">
        <div className="ap-daynav">
          <button className="icon-btn" onClick={() => setWeek(addDays(week, -7))} aria-label="Previous week">‹</button>
          <button className={week === mondayOf(today) ? "on" : ""} onClick={() => setWeek(mondayOf(today))}>This week</button>
          <button className="icon-btn" onClick={() => setWeek(addDays(week, 7))} aria-label="Next week">›</button>
        </div>
        <h2 className="ap-day-h">
          {parseYmd(days[0]).toLocaleDateString([], { day: "numeric", month: "short" })} – {parseYmd(days[6]).toLocaleDateString([], { day: "numeric", month: "short", year: "numeric" })}
        </h2>
        <span className="spacer" />
        <span className="ap-legend">
          <i className="s-scheduled" /> Scheduled <i className="s-completed" /> Completed <i className="s-no_show" /> No-show <i className="s-cancelled" /> Cancelled
        </span>
        <DoctorFilter doctors={doctors} value={doctor} onChange={setDoctor} />
      </div>

      <div className="ap-cal-wrap card">
        <div className="ap-cal" style={{ "--rows": hours.length }}>
          <div className="ap-cal-corner" />
          {days.map((d) => {
            const date = parseYmd(d), n = byDay[d]?.length || 0;
            return (
              <div key={d} className={`ap-cal-head ${d === today ? "today" : ""}`}>
                <small>{date.toLocaleDateString([], { weekday: "short" })}</small>
                <b>{date.getDate()}</b>
                <small>{n ? `${n} visit${n > 1 ? "s" : ""}` : " "}</small>
              </div>
            );
          })}
          <div className="ap-cal-hours">
            {hours.map((h) => <span key={h} style={{ height: HOUR }}>{String(h).padStart(2, "0")}:00</span>)}
          </div>
          {days.map((d) => (
            <div key={d} className={`ap-cal-col ${d === today ? "today" : ""}`} style={{ height: hours.length * HOUR }}>
              {d === today && nowLine > 0 && nowLine < hours.length * HOUR && <span className="ap-now" style={{ top: nowLine }} />}
              {(byDay[d] || []).map(({ a, lane, lanes }) => {
                const s = new Date(a.start_time), e = new Date(a.end_time);
                const top = (s.getHours() + s.getMinutes() / 60 - from) * HOUR;
                const height = Math.max(24, ((e - s) / 3600000) * HOUR - 3);
                return (
                  <button key={a.id} type="button" className={`ap-event s-${a.status}`} onClick={() => setOpen(a)}
                          style={{ top, height, left: `calc(${(lane / lanes) * 100}% + 2px)`, width: `calc(${100 / lanes}% - 4px)` }}
                          title={`${hhmm(a.start_time)} ${a.patient_name} · ${a.reason}`}>
                    <b>{hhmm(a.start_time)}</b> <span>{a.patient_name}</span>
                    {height > 40 && <small>{a.reason}{!one && ` · ${a.doctor_name}`}</small>}
                  </button>
                );
              })}
            </div>
          ))}
        </div>
      </div>
      {!rows.length && <p className="hint ap-count">No visits this week.</p>}
      {open && <VisitDialog a={open} staff={staff} ask={ask} onMove={onMove} onClose={() => setOpen(null)} />}
    </>
  );
}
