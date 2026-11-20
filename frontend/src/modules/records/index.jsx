import { useEffect, useState } from "react";
import { api } from "../../api.js";
import { Field, Msg, Table, errorText, useList } from "../../shared/ui.jsx";

function Chart({ patient, clinician }) {
  const [data, setData] = useState(null);
  const [message, setMessage] = useState(null);
  const [revision, setRevision] = useState(0);
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    let active = true;
    const query = patient ? "?patient=" + patient : "";
    Promise.all(["/records/", "/treatment-plans/", "/orders/"].map(path => api(path + query)))
      .then(rows => { if (active) setData(rows); })
      .catch(err => { if (active) setMessage({ ok: false, text: errorText(err) }); });
    return () => { active = false; };
  }, [patient, revision]);

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
    return { patient, notes: v.notes,
      diagnoses_in: v.code ? [{ icd10_code: v.code.trim(), is_primary: true }] : [],
      prescriptions_in: v.medication ? [{ medication: v.medication, dosage: v.dosage, frequency: v.frequency, duration: v.duration }] : [] };
  }
  const [records, plans, orders] = data || [[], [], []];
  return <>
    <Msg m={message} />
    {clinician && <fieldset disabled={busy}>
      <legend>Clinical entries</legend>
      <form onSubmit={submit("/records/", visit)}>
        <h3>New visit</h3><Field label="Visit notes" name="notes" required />
        <Field label="Primary ICD-10 code" name="code" placeholder="C25.9" />
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
      <h3>Medical history</h3>
      <Table head={["Date","Visit notes","Diagnoses","Prescriptions"]} rows={records.map(r =>
        <tr key={r.id}><td>{new Date(r.created_at).toLocaleDateString()}</td><td>{r.notes}</td>
          <td>{r.diagnoses.map(d => d.icd10_code + " " + d.description).join(", ")}</td>
          <td>{r.prescriptions.map(p => [p.medication,p.dosage,p.frequency,p.duration,p.instructions].filter(Boolean).join(" · ")).join(", ")}</td></tr>)} />
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
    </>}
  </>;
}

function StaffRecords({ me }) {
  const [patients] = useList("/patients/");
  const [selected, setSelected] = useState("");
  return <><label>Patient<select value={selected} onChange={e => setSelected(e.target.value)}>
    <option value="">Choose a patient</option>
    {patients.map(p => <option key={p.id} value={p.id}>{p.name} · {p.mrn}</option>)}
  </select></label>
    {selected && <Chart key={selected} patient={selected} clinician={me.role === "clinical"} />}</>;
}

function Records({ me }) {
  return me.role === "patient" ? <Chart clinician={false} /> : <StaffRecords me={me} />;
}

export default { id: "records", label: "Records", order: 30, roles: ["clinical","admin","patient"], Component: Records };
