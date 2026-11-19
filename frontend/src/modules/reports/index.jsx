// reports/ (summary + CSV export). Feature F7.
import { useEffect, useState } from "react";
import { api } from "../../api.js";
import { Bars, Msg, errorText } from "../../shared/ui.jsx";
import { useQueryState } from "../../shared/url.js";

const PERIODS = [7, 30, 90, 365];

const Tile = ({ label, value, accent }) => <div className={`tile${accent ? " accent" : ""}`}><div className="label">{label}</div><div className="value">{value}</div></div>;
const pairs = (o) => Object.entries(o || {}).map(([label, value]) => ({ label: label.replace("_", "-"), value }));
const money = (v) => Number(v || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const DownloadIcon = () => (
  <svg className="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
    <path d="M12 4v11M7 10l5 5 5-5M5 20h14" />
  </svg>
);
const RefreshIcon = () => (
  <svg className="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
    <path d="M20 11a8 8 0 0 0-14.9-3M4 4v4h4M4 13a8 8 0 0 0 14.9 3M20 20v-4h-4" />
  </svg>
);
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
  const [rawDays, setDays] = useQueryState("days", "30"); // /reports?days=90
  const days = PERIODS.includes(Number(rawDays)) ? Number(rawDays) : 30;
  const [s, setS] = useState(null), [msg, setMsg] = useState({}), [busy, setBusy] = useState(false);
  const load = () => {
    setMsg({}); setBusy(true);
    api(`/reports/summary/?days=${days}`).then(setS).catch((e) => setMsg({ text: errorText(e) })).finally(() => setBusy(false));
  };
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
            {PERIODS.map((d) => <option key={d} value={d}>Last {d} days</option>)}
          </select>
        </label>
        <button className={`icon-btn${busy ? " spinning" : ""}`} onClick={load} disabled={busy} title="Refresh the numbers" aria-label="Refresh">
          <RefreshIcon />
        </button>
        <div className="spacer" />
        <div className="export-row">
          {["appointments", "patients", "invoices"].map((t) => (
            <button key={t} className="with-icon" onClick={() => download(t)} disabled={t === "invoices" && !billing} title={`Download ${t} as CSV`}>
              <DownloadIcon /> {t[0].toUpperCase() + t.slice(1)} CSV
            </button>
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
