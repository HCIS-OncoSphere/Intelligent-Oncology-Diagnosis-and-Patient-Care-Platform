// Booking in short steps: (Patient, for admins) → Reason → Doctor → Time, then a popup to confirm.
// A summary on the side fills in as you go; click any filled line to go back and change it.
// The same component moves an existing appointment (moving=appointment): then only the Time step shows.
import { useEffect, useMemo, useState } from "react";
import { api } from "../../api.js";
import { Avatar } from "../../shared/Avatar.jsx";
import { ConfirmDialog } from "../../shared/ConfirmDialog.jsx";
import { Icon } from "../../shared/Icon.jsx";
import { errorText } from "../../shared/ui.jsx";
import { price } from "../billing/money.js";
import { REASONS, addDays, hhmm, isYmd, longDay, mondayOf, parseYmd, shortDay, todayYmd, when, ymd } from "./shared.jsx";

const PARTS = [["Morning", 0, 12], ["Afternoon", 12, 17], ["Evening", 17, 24]];

function Stepper({ steps, at, go }) {
  return (
    <ol className="ap-stepper">
      {steps.map((s, i) => (
        <li key={s} className={i < at ? "done" : i === at ? "now" : ""}>
          <button type="button" disabled={i > at} onClick={() => go(i)} aria-current={i === at ? "step" : undefined}>
            <span className="ap-step-dot">{i < at ? <Icon name="checkCircle" /> : i + 1}</span>
            <span className="ap-step-label">{s}</span>
          </button>
        </li>
      ))}
    </ol>
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

export function BookingWizard({ me, doctors, nextFree, patients, prices = {}, moving, onDone, onStopMoving }) {
  const admin = me.role === "admin";
  const steps = moving ? ["Time"] : admin ? ["Patient", "Reason", "Doctor", "Time"] : ["Reason", "Doctor", "Time"];
  const [at, setAt] = useState(0);
  const [patient, setPatient] = useState(null), [search, setSearch] = useState("");
  const [reason, setReason] = useState(""), [other, setOther] = useState("");
  const [doctorId, setDoctorId] = useState(moving ? String(moving.doctor) : "");
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
    const req = moving
      ? api(`/appointments/${moving.id}/reschedule/`, { method: "POST", body: slot })
      : api("/appointments/", { method: "POST", body: { doctor: doctor.id, ...slot, reason: reasonText, ...(admin ? { patient: patient.id } : {}) } });
    req.then((a) => {
      setPicked(null);
      const bill = a?.bill?.status === "pending" ? ` Invoice ${a.bill.number} (${price(a.bill.total)}) is ready: pay online or at the reception desk.` : "";
      onDone(moving ? `Moved to ${shortDay(slot.start_time)}, ${hhmm(slot.start_time)}.` : `Booked ${shortDay(slot.start_time)}, ${hhmm(slot.start_time)} with ${doctor.name}.${bill}`);
      if (!moving) reset();
    }).catch((e) => { setPicked(null); setErr(errorText(e)); setReload((n) => n + 1); }).finally(() => setBusy(false));
  };

  const Line = ({ name, icon, label, value }) => {
    const reachable = steps.includes(name) && steps.indexOf(name) <= at;
    return (
      <li className={value ? "set" : ""}>
        <span className="ap-sum-icon"><Icon name={icon} /></span>
        <span><small>{label}</small>{value || <i>Not chosen yet</i>}</span>
        {value && reachable && !moving && <button type="button" className="ghost sm" onClick={() => goTo(name)}>Change</button>}
      </li>
    );
  };

  if (!doctors.length) return <p className="hint">No doctors yet. An admin creates a clinical user with a license number.</p>;

  return (
    <div className="ap-wizard">
      <section className="ap-wiz-main card">
        {moving ? (
          <header className="ap-wiz-head">
            <h2>Move your appointment</h2>
            <p className="hint">Now: {when(moving)} with {moving.doctor_name}. Pick a new time below.</p>
          </header>
        ) : <Stepper steps={steps} at={at} go={setAt} />}

        {err && <p className="msg err">{err}</p>}

        {step === "Patient" && (
          <div>
            <h3 className="ap-q">Who is the visit for?</h3>
            <input className="ap-search" type="search" placeholder="Search by name or MRN" value={search} autoFocus
                   onChange={(e) => setSearch(e.target.value)} />
            <div className="ap-pick-list">
              {found.map((p) => (
                <button type="button" key={p.id} className={patient?.id === p.id ? "on" : ""} onClick={() => { setPatient(p); next(); }}>
                  <Avatar name={p.name} seed={p.id} size={36} />
                  <span><b>{p.name || "(no name)"}</b><small>{p.mrn}</small></span>
                </button>
              ))}
              {!found.length && <p className="hint">No patient matches “{search}”.</p>}
            </div>
          </div>
        )}

        {step === "Reason" && (
          <div>
            <h3 className="ap-q">What is the visit for?</h3>
            <div className="ap-cards">
              {REASONS.map((r) => (
                <button type="button" key={r.label} className={reason === r.label ? "on" : ""}
                        onClick={() => { setReason(r.label); if (r.label !== "Other") next(); }}>
                  <span className="ap-card-icon"><Icon name={r.icon} /></span>
                  <b>{r.label}</b><small>{r.text}</small>
                  {prices[r.label.toLowerCase()] && <span className="ap-price">{price(prices[r.label.toLowerCase()].price)}</span>}
                </button>
              ))}
            </div>
            {reason === "Other" && (
              <div className="ap-other">
                <input value={other} maxLength={200} autoFocus placeholder="e.g. new symptom since my last session"
                       onChange={(e) => setOther(e.target.value)} onKeyDown={(e) => e.key === "Enter" && next()} />
                <button type="button" className="primary" onClick={next}>Next</button>
              </div>
            )}
          </div>
        )}

        {step === "Doctor" && (
          <div>
            <h3 className="ap-q">Which doctor?</h3>
            <div className="ap-cards ap-doctors">
              {doctors.map((d) => {
                const f = nextFree?.[d.id];
                return (
                  <button type="button" key={d.id} className={String(doctorId) === String(d.id) ? "on" : ""}
                          onClick={() => { setDoctorId(String(d.id)); next(); }}>
                    <Avatar name={d.name} seed={d.id} size={44} />
                    <span className="ap-doc-text">
                      <b>{d.name}</b><small>{d.specialty}</small>
                      <span className={`ap-next ${f && !f.start_time ? "full" : ""}`}>
                        <Icon name="clock" />
                        {!nextFree ? "Checking…" : f?.start_time ? `First free: ${relDayOr(f.start_time)} · ${hhmm(f.start_time)}` : "Fully booked for 60 days"}
                      </span>
                    </span>
                  </button>
                );
              })}
            </div>
          </div>
        )}

        {step === "Time" && doctor && (
          <div>
            {!moving && <h3 className="ap-q">When suits you?</h3>}
            <TimeStep key={doctor.id} doctor={doctor} firstFree={moving ? null : nextFree?.[doctor.id]} onPick={setPicked} reload={reload} />
          </div>
        )}

        <footer className="ap-wiz-foot">
          {moving ? <button type="button" onClick={onStopMoving}>Keep the current time</button>
            : at > 0 ? <button type="button" onClick={() => setAt(at - 1)}>← Back</button> : <span />}
        </footer>
      </section>

      <aside className="ap-summary card" aria-label="Summary">
        <h3>{moving ? "Moving" : "Your visit"}</h3>
        <ul>
          {admin && !moving && <Line name="Patient" icon="user" label="Patient" value={patient && `${patient.name} · ${patient.mrn}`} />}
          <Line name="Reason" icon="clipboard" label="Reason" value={moving ? moving.reason || "—" : reason && reasonText} />
          <Line name="Doctor" icon="stethoscope" label="Doctor" value={doctor?.name} />
          <Line name="Time" icon="calendar" label="Time" value={moving ? `Now ${when(moving)}` : null} />
        </ul>
        {!moving && reason && (
          <div className={`ap-cost ${cost ? "" : "none"}`}>
            <span><small>Estimated cost</small><b>{cost ? price(cost.price) : "Priced at the clinic"}</b></span>
            <p>{cost ? "An invoice is created when you book. Pay online or at the reception desk." : "There is no set price for this reason. The clinic adds the bill after the visit."}</p>
          </div>
        )}
        <p className="ap-sum-note"><Icon name="clock" /> Visits are 30 minutes. You can reschedule or cancel later{cost ? "; an unpaid bill is cancelled with the visit" : ""}.</p>
      </aside>

      {picked && (
        <ConfirmDialog tone="primary" icon="calendar" cancelLabel="Pick another time" confirmLabel={busy ? "Booking…" : moving ? "Move appointment" : "Book visit"}
          title={moving ? "Move to this time?" : "Book this visit?"}
          message={`${longDay(picked.start_time)}, ${hhmm(picked.start_time)}–${hhmm(picked.end_time)} with ${doctor.name}` +
            (moving ? "." : ` · ${reasonText}${admin && patient ? ` · for ${patient.name}` : ""}.` +
              (cost ? ` Estimated cost ${price(cost.price)}, paid after booking.` : ""))}
          onCancel={() => !busy && setPicked(null)} onConfirm={() => !busy && confirm()} />
      )}
    </div>
  );
}

function relDayOr(iso) {
  const d = ymd(new Date(iso)), t = todayYmd();
  return d === t ? "today" : d === addDays(t, 1) ? "tomorrow" : shortDay(iso);
}
