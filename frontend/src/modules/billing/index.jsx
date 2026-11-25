// Owner: Aliaa. Backend: billing/ (invoices, payments, ICD-10 catalog, services)
// Visits bill themselves: booking opens a pending invoice (billing/signals.py). Patients pay by card here;
// staff record cash / card / insurance at the desk. Every invoice opens as a printable receipt (?receipt=<id>).
import { useEffect, useState } from "react";
import { api } from "../../api.js";
import { Badge, Msg, Table, errorText, useList } from "../../shared/ui.jsx";
import { useQueryState } from "../../shared/url.js";
import { PaymentDialog } from "./PaymentDialog.jsx";
import { Receipt } from "./Receipt.jsx";
import { ServicesAdmin } from "./ServicesAdmin.jsx";
import { money } from "./money.js";
import "./billing.css";

const FILTERS = [["", "All"], ["pending", "To pay"], ["paid", "Paid"], ["cancelled", "Cancelled"]];
const shortDate = (v) => new Date(v).toLocaleDateString([], { day: "numeric", month: "short", year: "numeric" });

/** Staff: an invoice for something that was not booked as a visit (extra scan, medicine...). */
function NewInvoice({ onCreated }) {
  const [services] = useList("/services/");
  const [patients] = useList("/patients/");
  const [patient, setPatient] = useState(""), [service, setService] = useState(""), [qty, setQty] = useState(1);
  const [msg, setMsg] = useState(null);

  const create = async (e) => {
    e.preventDefault();
    try {
      const inv = await api("/invoices/", { method: "POST", body: { patient, items_in: [{ service: service || services[0]?.id, quantity: Number(qty) }] } });
      setMsg({ ok: true, text: `Invoice ${inv.invoice_number} created.` });
      onCreated();
    } catch (x) { setMsg({ ok: false, text: errorText(x) }); }
  };

  return (
    <details className="card bl-new">
      <summary>New invoice for something not booked as a visit</summary>
      <form className="form-row" onSubmit={create}>
        <label>Patient
          <select value={patient} onChange={(e) => setPatient(e.target.value)} required>
            <option value="">Choose a patient…</option>
            {patients.map((p) => <option key={p.id} value={p.id}>{p.name || "(no name)"} · {p.mrn}</option>)}
          </select>
        </label>
        <label>Service
          <select value={service} onChange={(e) => setService(e.target.value)}>
            {services.map((s) => <option key={s.id} value={s.id}>{s.name} ({money(s.price)})</option>)}
          </select>
        </label>
        <label>Quantity<input type="number" min="1" value={qty} onChange={(e) => setQty(e.target.value)} size="4" /></label>
        <button className="primary">Create invoice</button>
      </form>
      <Msg m={msg} />
    </details>
  );
}

function Invoices({ me }) {
  const staff = me.role !== "patient";
  const desk = me.role === "admin"; // billing staff take payments; doctors don't handle money
  const [rows, load] = useList("/invoices/");
  const [msg, setMsg] = useState(null), [paying, setPaying] = useState(null);
  const [receipt, setReceipt] = useQueryState("receipt", "");
  const [filter, setFilter] = useQueryState("status", "", { replace: true });
  const [after, setAfter] = useState(null); // what to re-read once a payment is saved

  const pay = (inv, reload) => {
    setPaying({ id: inv.id, number: inv.invoice_number, total: inv.total_amount, paid: inv.paid_amount });
    setAfter(() => reload || load);
  };
  const paid = (inv) => {
    setPaying(null); after?.(); load();
    setMsg({ ok: true, text: inv.status === "paid" ? `${inv.invoice_number} is paid in full.` : `Payment saved. ${money(Number(inv.total_amount) - Number(inv.paid_amount))} left on ${inv.invoice_number}.` });
  };
  const canPay = (i) => i.status === "pending" && (desk || !staff);
  const list = rows.filter((i) => !filter || i.status === filter);
  const owed = rows.filter((i) => i.status === "pending").reduce((s, i) => s + Number(i.total_amount) - Number(i.paid_amount), 0);
  useEffect(() => { setMsg(null); }, [receipt]);

  const dialog = paying && <PaymentDialog invoice={paying} staff={staff} onDone={paid} onClose={() => setPaying(null)} />;
  if (/^\d+$/.test(receipt)) {
    return <><Msg m={msg} /><Receipt id={receipt} onBack={() => setReceipt("")} onPay={rows.some((i) => String(i.id) === receipt && canPay(i)) ? pay : null} />{dialog}</>;
  }

  return (
    <>
      <Msg m={msg} />
      {!staff && owed > 0 && (
        <div className="bl-owed card"><b>{money(owed)}</b> to pay on {rows.filter((i) => i.status === "pending").length} invoice(s). Pay online here, or at the reception desk.</div>
      )}
      {desk && <NewInvoice onCreated={load} />}
      <div className="bl-filters">
        {FILTERS.map(([v, label]) => (
          <button key={v || "all"} className={filter === v ? "on" : ""} aria-pressed={filter === v} onClick={() => setFilter(v)}>{label}</button>
        ))}
      </div>
      <Table
        head={["Invoice", ...(staff ? ["Patient"] : []), "For", "Total", "Left to pay", "Status", ""]}
        empty={filter ? "No invoices here." : "No invoices yet. Booking a visit creates one."}
        rows={list.map((i) => {
          const left = Number(i.total_amount) - Number(i.paid_amount);
          return (
            <tr key={i.id}>
              <td><b>{i.invoice_number}</b><br /><small>{shortDate(i.issue_date)}</small></td>
              {staff && <td>{i.patient_name}<br /><small>{i.patient_mrn}</small></td>}
              <td>{i.items.map((x) => x.quantity > 1 ? `${x.quantity}× ${x.service_name}` : x.service_name).join(", ")}
                {i.visit && <><br /><small>Visit {shortDate(i.visit.start_time)} · {i.visit.doctor_name}</small></>}</td>
              <td>{money(i.total_amount)}</td>
              <td>{i.status === "pending" ? <b>{money(left)}</b> : "—"}</td>
              <td><Badge s={i.status} /></td>
              <td>
                {canPay(i) && <button className="primary" onClick={() => pay(i)}>{staff ? "Record payment" : "Pay"}</button>}
                <button onClick={() => setReceipt(String(i.id))}>{i.status === "paid" ? "Receipt" : "View"}</button>
              </td>
            </tr>
          );
        })}
      />
      {dialog}
    </>
  );
}

/** Billing staff (admins) get a second tab for the price list. Its services are only fetched for them. */
function AdminBilling({ me }) {
  const [tab, setTab] = useQueryState("tab", "invoices", { replace: true });
  const [receipt] = useQueryState("receipt", "");
  const [services, loadServices] = useList("/services/?all=1");
  const viewingReceipt = /^\d+$/.test(receipt);
  return (
    <>
      {!viewingReceipt && (
        <div className="bl-filters" role="tablist">
          {[["invoices", "Invoices"], ["services", "Price list"]].map(([v, label]) => (
            <button key={v} role="tab" aria-selected={tab === v} className={tab === v ? "on" : ""} onClick={() => setTab(v)}>{label}</button>
          ))}
        </div>
      )}
      {tab === "services" && !viewingReceipt ? <ServicesAdmin rows={services} reload={loadServices} /> : <Invoices me={me} />}
    </>
  );
}

function Billing({ me }) {
  return me.role === "admin" ? <AdminBilling me={me} /> : <Invoices me={me} />;
}

export default { id: "billing", label: "Invoices", order: 40, roles: ["patient", "clinical", "admin"], Component: Billing };
