// Owner: Aliaa. Backend: billing/ (invoices, payments, ICD-10 catalog, services)
import { useState } from "react";
import { api } from "../../api.js";
import { Badge, Field, Msg, Table, errorText, useList } from "../../shared/ui.jsx";

const money = (v) => Number(v).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });

/** Staff only: create an invoice with one service line. Totals and ICD-10 codes are worked out by the server. */
function NewInvoice({ onCreated }) {
  const [services] = useList("/services/");
  const [patient, setPatient] = useState("");
  const [service, setService] = useState("");
  const [qty, setQty] = useState(1);
  const [msg, setMsg] = useState(null);

  const create = async (e) => {
    e.preventDefault();
    try {
      await api("/invoices/", {
        method: "POST",
        body: { patient, items_in: [{ service: service || services[0]?.id, quantity: Number(qty) }] },
      });
      setMsg({ ok: true, text: "Invoice created." });
      onCreated();
    } catch (x) { setMsg({ ok: false, text: errorText(x) }); }
  };

  return (
    <form className="card" onSubmit={create}>
      <h3>New invoice</h3>
      <Field label="Patient id" value={patient} onChange={(e) => setPatient(e.target.value)} size="4" required />
      <label>Service
        <select value={service} onChange={(e) => setService(e.target.value)}>
          {services.map((s) => <option key={s.id} value={s.id}>{s.name} ({money(s.price)})</option>)}
        </select>
      </label>
      <Field label="Quantity" type="number" min="1" value={qty} onChange={(e) => setQty(e.target.value)} />
      <button className="primary">Create invoice</button>
      <Msg m={msg} />
    </form>
  );
}

function Invoices({ me }) {
  const [rows, load] = useList("/invoices/");
  const [msg, setMsg] = useState(null);
  const staff = me.role !== "patient";

  const pay = async (i) => {
    const due = (Number(i.total_amount) - Number(i.paid_amount)).toFixed(2);
    if (!window.confirm(`Pay ${money(due)} for ${i.invoice_number}?`)) return;
    try {
      await api(`/invoices/${i.id}/pay/`, { method: "POST", body: { amount: due, method: "card" } });
      setMsg({ ok: true, text: `Payment of ${money(due)} recorded.` });
      load();
    } catch (x) { setMsg({ ok: false, text: errorText(x) }); }
  };

  return (
    <>
      {staff && <NewInvoice onCreated={load} />}
      <Msg m={msg} />
      <Table
        head={["Invoice", "Items (ICD-10)", "Total", "Paid", "Status", ""]}
        empty="No invoices yet."
        rows={rows.map((i) => (
          <tr key={i.id}>
            <td>{i.invoice_number}</td>
            <td>{i.items.map((x) => `${x.quantity}× service #${x.service}${x.icd10_code ? ` [${x.icd10_code}]` : ""}`).join(", ")}</td>
            <td>{money(i.total_amount)}</td>
            <td>{money(i.paid_amount)}</td>
            <td><Badge s={i.status} /></td>
            <td>{i.status === "pending" && <button onClick={() => pay(i)}>Pay</button>}</td>
          </tr>
        ))}
      />
    </>
  );
}

export default { id: "billing", label: "Invoices", order: 40, roles: ["patient", "clinical", "admin"], Component: Invoices };
