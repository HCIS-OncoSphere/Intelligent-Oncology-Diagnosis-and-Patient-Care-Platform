// reports/ (summary + CSV export). Feature F7.
import { useEffect, useState } from "react";
import { api } from "../../api.js";
import { Bars, Msg, errorText } from "../../shared/ui.jsx";

const Tile = ({ label, value, accent }) => <div className={`tile${accent ? " accent" : ""}`}><div className="label">{label}</div><div className="value">{value}</div></div>;
const pairs = (o) => Object.entries(o || {}).map(([label, value]) => ({ label: label.replace("_", "-"), value }));
const money = (v) => Number(v || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const GENDER = { M: "Male", F: "Female", O: "Other" };

function Chart({ title, data, note = "No data yet." }) {
  return (
    <div className="card">
      <h3>{title}</h3>
      {data.length ? <Bars data={data} /> : <p className="hint">{note}</p>}
    </div>
  );
}

function Reports() {
  const [days, setDays] = useState(30), [s, setS] = useState(null), [msg, setMsg] = useState({});
  const load = () => { setMsg({}); api(`/reports/summary/?days=${days}`).then(setS).catch((e) => setMsg({ text: errorText(e) })); };
  useEffect(load, [days]);

  const download = async (type) => {
    setMsg({});
    const res = await fetch(`/api/reports/export/?type=${type}`, { headers: { Authorization: `Bearer ${localStorage.getItem("access")}` } });
    if (!res.ok) return setMsg({ text: errorText(await res.json().catch(() => res.statusText)) });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(await res.blob());
    a.download = `${type}_${new Date().toLocaleDateString("en-CA")}.csv`;
    a.click();
    URL.revokeObjectURL(a.href);
    setMsg({ ok: true, text: `Downloaded ${type}.csv` });
  };

  if (!s) return msg.text ? <Msg m={msg} /> : <p className="hint">Loading…</p>;
  const billing = s.modules?.billing, records = s.modules?.records;
  return (
    <>
      <div className="form-row">
        <label>Period
          <select value={days} onChange={(e) => setDays(Number(e.target.value))}>
            {[7, 30, 90, 365].map((d) => <option key={d} value={d}>Last {d} days</option>)}
          </select>
        </label>
        <button onClick={load}>Refresh</button>
        <div className="spacer" />
        <div className="export-row">
          {["appointments", "patients", "invoices"].map((t) => (
            <button key={t} onClick={() => download(t)} disabled={t === "invoices" && !billing} title={`Download ${t} as CSV`}>↓ {t} CSV</button>
          ))}
        </div>
      </div>
      <Msg m={msg} />

      <div className="tiles">
        <Tile accent label="Patients" value={s.patients_total} />
        <Tile accent label="Appointments" value={s.appointments_total} />
        <Tile label="Upcoming" value={s.upcoming_appointments} />
        <Tile label="No-show rate" value={`${Math.round((s.no_show_rate || 0) * 100)}%`} />
        {billing && <Tile label="Collected" value={money(s.revenue_collected)} />}
        {billing && <Tile label="Outstanding" value={money(s.revenue_outstanding)} />}
      </div>

      <div className="charts">
        <Chart title="Appointments by status" data={pairs(s.appointments_by_status)} />
        <Chart title={`Appointments per day (last ${s.period_days} days)`} data={s.appointments_per_day.map((d) => ({ label: d.date, value: d.count }))} />
        <Chart title="Appointments by doctor" data={s.appointments_by_doctor.map((d) => ({ label: d.name, value: d.count }))} />
        <Chart title="Patients by gender" data={pairs(s.patients_by_gender).map((d) => ({ ...d, label: GENDER[d.label] || d.label }))} />
        <Chart title="Patients by cancer type" data={pairs(s.patients_by_cancer_type)} />
        <Chart title="Top diagnoses (ICD-10)" data={s.top_diagnoses.map((d) => ({ label: `${d.code} ${d.description || ""}`.trim(), value: d.count }))}
          note={records ? "No diagnoses recorded yet." : "Available when the records module is merged."} />
        <Chart title="Invoices by status" data={pairs(s.invoices_by_status)} note={billing ? "No invoices yet." : "Available when the billing module is merged."} />
        {billing && <Chart title="Revenue by month" data={s.revenue_by_month.map((r) => ({ label: r.month, value: Number(r.total) }))} />}
      </div>
    </>
  );
}

export default { id: "reports", label: "Reports", order: 60, roles: ["clinical", "admin"], Component: Reports };
