import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { createPortal } from "react-dom";
import { api } from "../../api.js";
import { Badge, Field, Msg, Table, errorText, useList } from "../../shared/ui.jsx";
import { BookingWizard } from "../appointments/BookingWizard.jsx";
import "./records.css";

const dateTime = value => new Date(value).toLocaleString([], { dateStyle: "medium", timeStyle: "short" });
const visitDate = record => record.appointment_start_time || record.created_at;
const diagnosesText = record => record.diagnoses.map(d => `${d.icd10_code} ${d.description}`).join(", ");
const prescriptionsText = record => record.prescriptions.map(p =>
  [p.medication, p.dosage, p.frequency, p.duration, p.instructions].filter(Boolean).join(" · ")).join(", ");

function HistoryTable({ records, empty, onBook }) {
  return <Table head={["Visit date", "Doctor", "Visit notes", "Diagnoses", "Prescriptions", "Follow-up"]} empty={empty}
    rows={records.map(record => {
      const booking = record.follow_up_appointment;
      return <tr key={record.id}>
        <td>{dateTime(visitDate(record))}{record.appointment && <small>Appointment #{record.appointment}</small>}</td>
        <td>{record.doctor_name}</td>
        <td>{record.notes || "—"}</td>
        <td>{diagnosesText(record) || "—"}</td>
        <td>{prescriptionsText(record) || "—"}</td>
        <td>{record.follow_up_recommendation || "—"}
          {booking && <small>#{booking.id} · {dateTime(booking.start_time)} <Badge s={booking.status} />
            {onBook && <Link to="/appointments?view=list">View my appointments</Link>}</small>}
          {onBook && record.follow_up_recommendation && (!booking || booking.status === "cancelled") &&
            <button type="button" onClick={() => onBook(record)}>Book follow-up</button>}</td>
      </tr>;
    })} />;
}

function PatientSummary({ name, records, plans, orders }) {
  return createPortal(<article className="records-print">
    <h1>OncoSphere Patient Summary</h1>
    <p>{name}</p>
    <h2>Medical history</h2>
    <HistoryTable records={records} empty="No visits recorded." />
    <h2>Treatment plans</h2>
    <Table head={["Type", "Description", "Dates", "Status"]} empty="No treatment plans recorded."
      rows={plans.map(p => <tr key={p.id}><td>{p.type}</td><td>{p.description}</td>
        <td>{p.start_date} – {p.end_date || "ongoing"}</td><td>{p.status}</td></tr>)} />
    <h2>Orders and results</h2>
    <Table head={["Type", "Description", "Status", "Results"]} empty="No orders recorded."
      rows={orders.map(o => <tr key={o.id}><td>{o.order_type}</td><td>{o.description}</td><td>{o.status}</td>
        <td>{o.results.map(r => <p key={r.id}>{r.result_text}</p>)}</td></tr>)} />
  </article>, document.body);
}

function FollowUpBooking({ me, record, onDone, onBack }) {
  const [prices] = useList("/services/visit-prices/");
  const [nextFree] = useList("/doctors/next-free/");
  return <div className="ap-book-wrap">
    <BookingWizard me={me} doctors={[{ id: record.doctor, name: record.doctor_name }]}
      nextFree={Object.fromEntries(nextFree.map(slot => [slot.doctor, slot]))}
      prices={Object.fromEntries(prices.map(item => [item.reason.toLowerCase(), item]))}
      followUp={record} onDone={onDone} onStopFollowUp={onBack} />
  </div>;
}

function Chart({ me, patient, clinician }) {
  const [data, setData] = useState(null);
  const [message, setMessage] = useState(null);
  const [revision, setRevision] = useState(0);
  const [busy, setBusy] = useState(false);
  const [appointments, setAppointments] = useState(null);
  const [filter, setFilter] = useState("all");
  const [followUp, setFollowUp] = useState(null);
  useEffect(() => {
    let active = true;
    const query = patient ? "?patient=" + patient : "";
    api("/records/chart/" + query).then(chart => {
      if (!active) return;
      if (chart.viewer !== me.id || (patient && String(chart.patient) !== String(patient))) {
        throw new Error("Your session changed. Sign in again to open this chart.");
      }
      setData(chart);
    })
      .catch(err => { if (active) { setData(null); setMessage({ ok: false, text: errorText(err) }); } });
    return () => { active = false; };
  }, [me.id, patient, revision]);

  useEffect(() => {
    if (!clinician) return;
    let active = true;
    api("/doctors/").then(doctors => {
      const doctor = doctors.find(d => d.is_me);
      return doctor ? api(`/appointments/?patient=${patient}&doctor=${doctor.id}&status=scheduled`) : [];
    }).then(rows => {
      if (active) setAppointments(rows.filter(a => new Date(a.start_time).getTime() <= Date.now()).reverse());
    }).catch(err => {
      if (active) {
        setAppointments(null);
        setMessage({ ok: false, text: `Could not load appointments. ${errorText(err)}` });
      }
    });
    return () => { active = false; };
  }, [patient, clinician, revision]);

  function submit(path, makeBody, method = "POST") {
    return async event => {
      event.preventDefault();
      if (busy) return;
      const form = event.currentTarget;
      const values = Object.fromEntries(new FormData(form));
      setBusy(true);
      try {
        await api(path, { method, body: makeBody(values) });
        form.reset();
        setMessage({ ok: true, text: "Saved." });
        setRevision(value => value + 1);
      } catch (err) { setMessage({ ok: false, text: errorText(err) }); }
      finally { setBusy(false); }
    };
  }
  function visit(v) {
    return { patient, notes: v.notes, appointment: v.appointment || null,
      follow_up_recommendation: v.follow_up_recommendation.trim(),
      diagnoses_in: v.code ? [{ icd10_code: v.code.trim(), is_primary: true }] : [],
      prescriptions_in: v.medication ? [{ medication: v.medication, dosage: v.dosage, frequency: v.frequency, duration: v.duration }] : [] };
  }
  const { visits: records = [], plans = [], orders = [] } = data || {};
  const visibleRecords = records.filter(record => {
    if (me.role === "patient" && filter !== "all") {
      const today = new Date();
      const start = new Date(today.getFullYear(), today.getMonth(), today.getDate());
      if (filter === "year") start.setMonth(0, 1);
      if (filter === "month") start.setDate(start.getDate() - 29);
      if (filter === "quarter") start.setDate(start.getDate() - 89);
      const date = new Date(visitDate(record));
      return date >= start && date <= today;
    }
    if (filter === "recommended") return Boolean(record.follow_up_recommendation);
    if (filter === "booked") return record.follow_up_appointment?.status === "scheduled";
    if (filter === "prescribed") return record.prescriptions.length > 0;
    return true;
  });

  if (followUp) return <FollowUpBooking me={me} record={followUp} onBack={() => setFollowUp(null)}
    onDone={text => {
      setFollowUp(null);
      setData(null);
      setMessage({ ok: true, text });
      setRevision(value => value + 1);
    }} />;

  return <>
    <Msg m={message} />
    {data && <p><strong>{data.name}</strong> · {data.mrn}</p>}
    {data && <div className="tiles records-summary">
      {[
        ["Visits", records.length],
        ["Active treatment plans", plans.filter(plan => plan.status === "active").length],
        ["Orders awaiting results", orders.filter(order => order.status === "ordered").length],
      ].map(([label, count], index) => <div className={index === 0 ? "tile accent" : "tile"} key={label}>
        <div className="label">{label}</div><div className="value">{count}</div>
      </div>)}
    </div>}
    {clinician && <fieldset disabled={busy}>
      <legend>Clinical entries</legend>
      <form onSubmit={submit("/records/", visit)}>
        <h3>New visit</h3><label>Visit notes<textarea name="notes" rows={2} required /></label>
        <Field label="Primary ICD-10 code" name="code" placeholder="C25.9" />
        <label className="records-appointment">Linked appointment (optional)
          <select name="appointment" aria-label="Linked appointment (optional)" disabled={!appointments?.length}>
            <option value="">{appointments?.length ? "No linked appointment" : "No eligible appointments"}</option>
            {appointments?.map(a => <option key={a.id} value={a.id}>{dateTime(a.start_time)} · {a.reason || "Visit"}</option>)}
          </select>
        </label>
        <label className="records-recommendation">Follow-up recommendation (optional)
          <textarea name="follow_up_recommendation" maxLength={500} rows={2} placeholder="e.g. Follow up in two weeks" />
        </label>
        <Field label="Medication" name="medication" /><Field label="Dose" name="dosage" />
        <Field label="Frequency" name="frequency" /><Field label="Duration" name="duration" />
        <button>Save visit</button>
      </form>
      <form onSubmit={submit("/treatment-plans/", v => ({ ...v, patient, end_date: v.end_date || null }))}>
        <h3>New treatment plan</h3><label>Type<select name="type">
          {["chemotherapy","radiotherapy","surgery","immunotherapy","other"].map(t => <option key={t}>{t}</option>)}
        </select></label>
        <Field label="Description" name="description" required />
        <Field label="Start date" name="start_date" type="date" required />
        <Field label="End date" name="end_date" type="date" /><button>Save plan</button>
      </form>
      <form onSubmit={submit("/orders/", v => ({ ...v, patient }))}>
        <h3>New order</h3><label>Order type<select name="order_type">
          <option value="lab">Lab test</option><option value="imaging">Imaging</option><option value="other">Other</option>
        </select></label>
        <Field label="Description" name="description" required /><button>Place order</button>
      </form>
    </fieldset>}
    {data && <>
      <div className="records-history-heading">
        <h3>Medical history</h3>
        <button type="button" onClick={() => window.print()}>Print / save as PDF</button>
      </div>
      <label>{me.role === "patient" ? "When was my visit?" : "Filter medical history"}
        <select value={filter} onChange={event => setFilter(event.target.value)}>
          {me.role === "patient" ? <>
            <option value="all">All dates</option>
            <option value="month">Last 30 days</option>
            <option value="quarter">Last 90 days</option>
            <option value="year">This year</option>
          </> : <>
            <option value="all">All visits</option>
            <option value="recommended">Follow-up recommended</option>
            <option value="booked">Follow-up scheduled</option>
            <option value="prescribed">With prescriptions</option>
          </>}
        </select>
      </label>
      <HistoryTable records={visibleRecords} empty={filter === "all" ? "No visits recorded." : "No visits match this filter."}
        onBook={me.role === "patient" ? setFollowUp : null} />
      <h3>Treatment plans</h3>
      <Table head={["Type","Description","Dates","Status"]} rows={plans.map(p =>
        <tr key={p.id}><td>{p.type}</td><td>{p.description}</td><td>{p.start_date} – {p.end_date || "ongoing"}</td>
          <td>{clinician ? <form onSubmit={submit("/treatment-plans/" + p.id + "/", v => v, "PATCH")}>
            <select aria-label="Plan status" name="status" key={p.status} defaultValue={p.status}>{["active","completed","cancelled"].map(s => <option key={s}>{s}</option>)}</select>
            <button disabled={busy}>Update</button></form> : p.status}</td></tr>)} />
      <h3>Orders and results</h3>
      <Table head={["Type","Description","Status","Results"]} rows={orders.map(o =>
        <tr key={o.id}><td>{o.order_type}</td><td>{o.description}</td><td>{o.status}</td>
          <td>{o.results.map(r => <p key={r.id}>{r.result_text}</p>)}{clinician && o.status === "ordered" &&
            <form onSubmit={submit("/orders/" + o.id + "/result/", v => v)}>
              <Field label="Result" name="result_text" required /><button disabled={busy}>Save result</button></form>}</td></tr>)} />
      <PatientSummary name={data.name + " · " + data.mrn} records={records} plans={plans} orders={orders} />
    </>}
  </>;
}

function StaffRecords({ me }) {
  const [patients, setPatients] = useState(null);
  const [error, setError] = useState("");
  const [attempt, setAttempt] = useState(0);
  const [query, setQuery] = useState("");
  const [selected, setSelected] = useState(null);

  useEffect(() => {
    let active = true;
    setError("");
    api("/patients/").then(rows => {
      if (active) setPatients(rows);
    }).catch(err => {
      if (active) setError(errorText(err));
    });
    return () => { active = false; };
  }, [attempt]);

  if (selected) return <>
    <button type="button" className="records-back" onClick={() => setSelected(null)}>
      &larr; Change patient
    </button>
    <Chart key={selected.id} me={me} patient={selected.id} clinician={me.role === "clinical"} />
  </>;

  const words = query.trim().toLowerCase().split(/\s+/).filter(Boolean);
  const matches = (patients || []).filter(p => {
    const identity = [p.name, p.mrn].join(" ").toLowerCase();
    return words.every(word => identity.includes(word));
  });

  return <section className="records-directory" aria-labelledby="patient-directory-title">
    <header>
      <h2 id="patient-directory-title">Patient directory</h2>
      <p>Choose a patient to open their medical record.</p>
    </header>

    <label className="records-directory-search">Find a patient
      <input type="search" placeholder="Patient name or MRN"
        value={query} onChange={event => setQuery(event.target.value)} />
    </label>

    {error ? <div role="alert">
      <p>{error}</p>
      <button type="button" onClick={() => setAttempt(n => n + 1)}>Try again</button>
    </div> : patients === null ? <p role="status">Loading patients?</p> : <>
      <p className="records-match-count" role="status">
        {matches.length} {matches.length === 1 ? "patient" : "patients"}
        {words.length > 0 ? " found" : ""}
      </p>
      {matches.length ? <ul className="records-patient-list">
        {matches.map(p => {
          const name = p.name?.trim() || "Name unavailable";
          const initials = name.split(/\s+/).slice(0, 2).map(word => word[0]).join("");
          return <li key={p.id}>
            <button type="button" onClick={() => setSelected(p)}>
              <span className="records-initials" aria-hidden="true">{initials}</span>
              <span className="records-person"><strong>{name}</strong><small>{p.mrn}</small></span>
              <span className="records-open">Open chart <span aria-hidden="true">&rarr;</span></span>
            </button>
          </li>;
        })}
      </ul> : <p>{patients.length ? "No matching patients. Try another name or MRN." : "No patients are registered yet."}</p>}
    </>}
  </section>;
}

function Records({ me }) {
  return <div className="records-page">
    {me.role === "patient" ? <Chart key={me.id} me={me} clinician={false} /> : <StaffRecords key={me.id} me={me} />}
  </div>;
}

export default { id: "records", label: "Records", order: 30, roles: ["clinical","admin","patient"], Component: Records };
