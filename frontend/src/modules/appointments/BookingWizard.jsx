// Booking: a narrow column of stacked choices on the left ((Patient, for admins) → Reason → Doctor), each a list of
// small rows that folds into one line once chosen; the free times fill the wide panel on the right. A popup confirms.
// The same component moves an existing appointment (moving=appointment): then only the time panel is used.
import { useEffect, useMemo, useRef, useState } from "react";
import { api } from "../../api.js";
import { Avatar } from "../../shared/Avatar.jsx";
import { ConfirmDialog } from "../../shared/ConfirmDialog.jsx";
import { Icon } from "../../shared/Icon.jsx";
import { errorText } from "../../shared/ui.jsx";
import { price } from "../billing/money.js";
import { REASONS, addDays, hhmm, isYmd, longDay, mondayOf, parseYmd, shortDay, todayYmd, when, ymd } from "./shared.jsx";

const PARTS = [["Morning", 0, 12], ["Afternoon", 12, 17], ["Evening", 17, 24]];

/** One choice of the booking column. Open: its rows slide down. Done: folds into one line; the up arrow (or a click
 *  on the line) opens it again. Later: just its title. The body stays mounted so it can animate closed; `inert`
 *  keeps a closed body out of the tab order. */
function StackSection({ steps, at, goTo, name, n, title, value, children }) {
  const i = steps.indexOf(name), open = i === at, done = i < at;
  const ref = useRef(null), mounted = useRef(false);
  // bring a section that just opened into view, after it has started to grow
  useEffect(() => {
    if (!mounted.current) { mounted.current = true; return; }
    if (!open) return;
    const calm = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const t = setTimeout(() => ref.current?.scrollIntoView({ block: "nearest", behavior: calm ? "auto" : "smooth" }), 180);
    return () => clearTimeout(t);
  }, [open]);
  const reopen = () => goTo(name);
  return (
    <section ref={ref} className={`ap-sec ${open ? "open" : ""} ${done ? "done" : ""}`}>
      <header onClick={done ? reopen : undefined}>
        <span className="ap-sec-n">{done ? <Icon name="checkCircle" /> : n}</span>
        <span className="ap-sec-title"><b>{title}</b>{done && value && <small key={value}>{value}</small>}</span>
        {done && (
          <button type="button" className="ap-sec-up" aria-label={`Change ${title.toLowerCase()}`} title="Change"
                  onClick={(e) => { e.stopPropagation(); reopen(); }}>
            <Icon name="chevronUp" />
          </button>
        )}
      </header>
      {/* React 18 sets unknown attributes from strings; on React 19 this becomes inert={!open} */}
      <div className="ap-sec-wrap" inert={open ? undefined : ""}>
        <div className="ap-sec-inner"><div className="ap-sec-body">{children}</div></div>
      </div>
    </section>
  );
}

/** Doctor's free slots for one week (one request), grouped by day, with a strip of days to pick from. */
function TimeStep({ doctor, firstFree, onPick, reload }) {
  const today = todayYmd();
  const startDay = firstFree?.start_time ? ymd(new Date(firstFree.start_time)) : today;
  const [week, setWeek] = useState(() => (mondayOf(startDay) < today ? today : mondayOf(startDay)));
  const [day, setDay] = useState(startDay);
  const [slots, setSlots] = useState(null), [err, setErr] = useState("");

  useEffect(() => {
    setSlots(null); setErr("");
    api(`/doctors/${doctor.id}/slots/?date=${week}&days=7`).then((r) => setSlots(r.slots))
      .catch((e) => { setSlots([]); setErr(errorText(e)); });
  }, [doctor.id, week, reload]);

  const byDay = useMemo(() => {
    const m = {};
    for (const s of slots || []) (m[ymd(new Date(s.start_time))] ||= []).push(s);
    return m;
  }, [slots]);
  const days = Array.from({ length: 7 }, (_, i) => addDays(week, i));
  // when the chosen day has nothing free, move to the first day of the week that has
  useEffect(() => {
    if (slots && !byDay[day]) { const first = days.find((d) => byDay[d]); if (first) setDay(first); }
  }, [slots]);
  const goWeek = (n) => { const w = addDays(week, n * 7); const s = w < today ? today : w; setWeek(s); setDay(s); };
  const daySlots = byDay[day] || [];

  return (
    <div className="ap-time">
      {firstFree?.start_time && (
        <button type="button" className="ap-first-free" onClick={() => onPick(firstFree)}>
          <Icon name="clock" />
          <span><b>First free time</b> {shortDay(firstFree.start_time)} · {hhmm(firstFree.start_time)}</span>
          <span className="ap-first-free-go">Book it <Icon name="arrowRight" /></span>
        </button>
      )}
      <div className="ap-week-nav">
        <button type="button" className="icon-btn" onClick={() => goWeek(-1)} disabled={week <= today} aria-label="Previous week">‹</button>
        <b>{parseYmd(days[0]).toLocaleDateString([], { day: "numeric", month: "short" })} – {parseYmd(days[6]).toLocaleDateString([], { day: "numeric", month: "short", year: "numeric" })}</b>
        <button type="button" className="icon-btn" onClick={() => goWeek(1)} aria-label="Next week">›</button>
        <label className="ap-jump">Go to day
          <input type="date" min={today} value={day} onChange={(e) => { const v = e.target.value; if (isYmd(v) && v >= today) { setWeek(mondayOf(v) < today ? today : mondayOf(v)); setDay(v); } }} />
        </label>
      </div>
      <div className="ap-days" role="tablist" aria-label="Day">
        {days.map((d) => {
          const n = byDay[d]?.length || 0, date = parseYmd(d);
          return (
            <button type="button" role="tab" key={d} aria-selected={d === day} disabled={slots !== null && !n}
                    className={`${d === day ? "on" : ""} ${d === today ? "today" : ""}`} onClick={() => setDay(d)}>
              <small>{date.toLocaleDateString([], { weekday: "short" })}</small>
              <b>{date.getDate()}</b>
              <small className="ap-free-n">{slots === null ? "…" : n ? `${n} free` : "—"}</small>
            </button>
          );
        })}
      </div>
      {slots === null ? <p className="hint">Loading free times…</p>
        : err ? <p className="msg err">{err}</p>
        : !daySlots.length ? <p className="ap-empty"><Icon name="calendar" /> No free times this week. Try the next week.</p>
        : (
          <div className="ap-parts">
            <p className="ap-day-title">{longDay(daySlots[0].start_time)}</p>
            {PARTS.map(([name, from, to]) => {
              const list = daySlots.filter((s) => { const h = new Date(s.start_time).getHours(); return h >= from && h < to; });
              return list.length ? (
                <div key={name} className="ap-part">
                  <span className="ap-part-name">{name}</span>
                  <div className="ap-slots">
                    {list.map((s) => <button type="button" key={s.start_time} onClick={() => onPick(s)}>{hhmm(s.start_time)}</button>)}
                  </div>
                </div>
              ) : null;
            })}
          </div>
        )}
    </div>
  );
}

export function BookingWizard({ me, doctors, nextFree, patients, prices = {}, moving, followUp, onDone, onStopMoving, onStopFollowUp }) {
  const admin = me.role === "admin";
  const steps = moving || followUp ? ["Time"] : admin ? ["Patient", "Reason", "Doctor", "Time"] : ["Reason", "Doctor", "Time"];
  const [at, setAt] = useState(0);
  const [patient, setPatient] = useState(null), [search, setSearch] = useState("");
  const [reason, setReason] = useState(followUp ? "Follow-up visit" : ""), [other, setOther] = useState("");
  const [doctorId, setDoctorId] = useState(String(moving?.doctor ?? followUp?.doctor ?? ""));
  const [picked, setPicked] = useState(null), [busy, setBusy] = useState(false), [err, setErr] = useState(""), [reload, setReload] = useState(0);

  const step = steps[at];
  const doctor = doctors.find((d) => String(d.id) === String(doctorId));
  const reasonText = reason === "Other" ? other.trim() || "Other" : reason;
  const cost = reason ? prices[reasonText.toLowerCase()] : null; // {price, service} when this reason has a price
  const next = () => setAt((i) => Math.min(i + 1, steps.length - 1));
  const goTo = (name) => { const i = steps.indexOf(name); if (i >= 0 && i <= at) setAt(i); };
  const reset = () => { setAt(0); setPatient(null); setSearch(""); setReason(""); setOther(""); setDoctorId(""); };

  const found = useMemo(() => {
    const q = search.trim().toLowerCase();
    return (patients || []).filter((p) => !q || `${p.name} ${p.mrn}`.toLowerCase().includes(q)).slice(0, 8);
  }, [patients, search]);

  const confirm = () => {
    const slot = { start_time: picked.start_time, end_time: picked.end_time };
    setBusy(true); setErr("");
    const path = moving ? `/appointments/${moving.id}/reschedule/`
      : followUp ? `/records/${followUp.id}/book-follow-up/` : "/appointments/";
    const body = moving || followUp ? slot
      : { doctor: doctor.id, ...slot, reason: reasonText, ...(admin ? { patient: patient.id } : {}) };
    const req = api(path, { method: "POST", body });
    req.then((a) => {
      setPicked(null);
      const bill = a?.bill?.status === "pending" ? ` Invoice ${a.bill.number} (${price(a.bill.total)}) is ready: pay online or at the reception desk.` : "";
      onDone(moving ? `Moved to ${shortDay(slot.start_time)}, ${hhmm(slot.start_time)}.` : `Booked ${shortDay(slot.start_time)}, ${hhmm(slot.start_time)} with ${doctor.name}.${bill}`);
      if (!moving && !followUp) reset();
    }).catch((e) => { setPicked(null); setErr(errorText(e)); setReload((n) => n + 1); }).finally(() => setBusy(false));
  };

  if (!doctors.length) return <p className="hint">No doctors yet. An admin creates a clinical user with a license number.</p>;

  const sec = { steps, at, goTo };

  return (
    <div className="ap-book card">
        {moving ? (
          <div className="ap-moving">
            <small>Moving</small>
            <b>{moving.reason || "Visit"}</b>
            <span>Now {when(moving)}</span>
            <span>{moving.doctor_name}</span>
            <button type="button" onClick={onStopMoving}>Keep the current time</button>
          </div>
        ) : followUp ? (
          <div className="ap-moving">
            <small>Follow-up visit</small>
            <b>{doctor?.name}</b>
            <span>{followUp.follow_up_recommendation}</span>
            <button type="button" onClick={onStopFollowUp}>Back to records</button>
          </div>
        ) : (
          <>
            {admin && (
              <StackSection {...sec} name="Patient" n={1} title="Patient" value={patient && `${patient.name} · ${patient.mrn}`}>
                <input className="ap-search" type="search" placeholder="Search by name or MRN" value={search} autoFocus
                       onChange={(e) => setSearch(e.target.value)} />
                <div className="ap-rows">
                  {found.map((p) => (
                    <button type="button" key={p.id} className={patient?.id === p.id ? "on" : ""} onClick={() => { setPatient(p); next(); }}>
                      <Avatar name={p.name} seed={p.id} size={26} />
                      <span className="ap-row-text"><b>{p.name || "(no name)"}</b><small>{p.mrn}</small></span>
                    </button>
                  ))}
                  {!found.length && <p className="hint">No patient matches “{search}”.</p>}
                </div>
              </StackSection>
            )}

            <StackSection {...sec} name="Reason" n={admin ? 2 : 1} title="Reason for the visit" value={reason && reasonText}>
              <div className="ap-rows">
                {REASONS.map((r) => {
                  const p = prices[r.label.toLowerCase()];
                  return (
                    <button type="button" key={r.label} className={reason === r.label ? "on" : ""}
                            onClick={() => { setReason(r.label); if (r.label !== "Other") next(); }}>
                      <span className="ap-row-icon"><Icon name={r.icon} /></span>
                      <span className="ap-row-text"><b>{r.label}</b><small>{r.text}</small></span>
                      {p && <span className="ap-row-end">{price(p.price)}</span>}
                    </button>
                  );
                })}
              </div>
              {reason === "Other" && (
                <div className="ap-other">
                  <input value={other} maxLength={200} autoFocus placeholder="e.g. new symptom since my last session"
                         onChange={(e) => setOther(e.target.value)} onKeyDown={(e) => e.key === "Enter" && next()} />
                  <button type="button" className="primary" onClick={next}>Next</button>
                </div>
              )}
            </StackSection>

            <StackSection {...sec} name="Doctor" n={admin ? 3 : 2} title="Doctor" value={doctor?.name}>
              <div className="ap-rows">
                {doctors.map((d) => {
                  const f = nextFree?.[d.id];
                  return (
                    <button type="button" key={d.id} className={String(doctorId) === String(d.id) ? "on" : ""}
                            onClick={() => { setDoctorId(String(d.id)); next(); }}>
                      <Avatar name={d.name} seed={d.id} size={30} />
                      <span className="ap-row-text"><b>{d.name}</b><small>{d.specialty}</small></span>
                      <span className={`ap-next-wrap ${f && !f.start_time ? "full" : ""}`}>
                        {!nextFree ? "…" : f?.start_time
                          ? <>Next free: <strong>{relDayOr(f.start_time)} {hhmm(f.start_time)}</strong></>
                          : "No availability"}
                      </span>
                    </button>
                  );
                })}
              </div>
            </StackSection>
          </>
        )}

        <StackSection {...sec} name="Time" n={steps.length} title={moving ? "New time" : "Time"}>
          {err && <p className="msg err">{err}</p>}
          {doctor && <TimeStep key={doctor.id} doctor={doctor} firstFree={moving ? null : nextFree?.[doctor.id]} onPick={setPicked} reload={reload} />}
          <p className="ap-sum-note"><Icon name="clock" /> {doctor?.name} · 30-minute visit. You can reschedule or cancel later{cost ? "; an unpaid bill is cancelled with the visit" : ""}.</p>
        </StackSection>

      {picked && (
        <ConfirmDialog tone="primary" icon="calendar" cancelLabel="Pick another time" confirmLabel={busy ? "Booking…" : moving ? "Move appointment" : "Book visit"}
          title={moving ? "Move to this time?" : "Book this visit?"}
          message={moving ? `From ${when(moving)}.` : "Check the details before you book."}
          onCancel={() => !busy && setPicked(null)} onConfirm={() => !busy && confirm()}>
          {/* the whole booking, seen once, right before it is made */}
          <ul className="ap-confirm-sum">
            {admin && patient && !moving && <li><Icon name="user" /><small>Patient</small><b>{patient.name} · {patient.mrn}</b></li>}
            <li><Icon name="clipboard" /><small>Reason</small><b>{moving ? moving.reason || "—" : reasonText}</b></li>
            <li><Icon name="stethoscope" /><small>Doctor</small><b>{doctor.name}</b></li>
            <li><Icon name="calendar" /><small>When</small><b>{longDay(picked.start_time)}, {hhmm(picked.start_time)}–{hhmm(picked.end_time)}</b></li>
            {!moving && <li className="cost"><Icon name="receipt" /><small>Cost</small><b>{cost ? price(cost.price) : "Priced at the clinic"}</b></li>}
          </ul>
          {!moving && <p className="ap-confirm-note">{cost ? "An invoice is created when you book. Pay online or at the reception desk." : "There is no set price for this reason; the clinic adds the bill after the visit."}</p>}
        </ConfirmDialog>
      )}
    </div>
  );
}

function relDayOr(iso) {
  const d = ymd(new Date(iso)), t = todayYmd();
  return d === t ? "today" : d === addDays(t, 1) ? "tomorrow" : shortDay(iso);
}
