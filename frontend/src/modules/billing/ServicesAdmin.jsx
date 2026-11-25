// Admin only: the price list. Add a service, change its price or the booking reason it is charged for,
// and switch it off or on (services are never deleted, because old invoices still point at them).
// The "visit reason" is what ties a service to the reasons patients pick when booking (appointments):
// booking with that reason shows this price and opens a pending invoice for it.
import { useState } from "react";
import { api } from "../../api.js";
import { Badge, Msg, Table, errorText } from "../../shared/ui.jsx";
import { REASONS } from "../appointments/shared.jsx";
import { money } from "./money.js";

const BOOKING_REASONS = REASONS.map((r) => r.label).filter((l) => l !== "Other");
const EMPTY = { name: "", price: "", visit_reason: "" };

function ReasonInput({ value, onChange, ...p }) {
  return (
    <>
      <input list="bl-reasons" value={value} maxLength={100} onChange={(e) => onChange(e.target.value)} {...p} />
      <datalist id="bl-reasons">{BOOKING_REASONS.map((r) => <option key={r} value={r} />)}</datalist>
    </>
  );
}

export function ServicesAdmin({ rows, reload }) {
  const [form, setForm] = useState(EMPTY);
  const [edit, setEdit] = useState(null); // { id, price, visit_reason } while a row is being edited
  const [msg, setMsg] = useState(null), [busy, setBusy] = useState(false);

  const run = async (fn, okText) => {
    setBusy(true);
    try { await fn(); setMsg({ ok: true, text: okText }); await reload(); return true; }
    catch (x) { setMsg({ ok: false, text: errorText(x) }); return false; }
    finally { setBusy(false); }
  };

  const add = async (e) => {
    e.preventDefault();
    const body = { name: form.name.trim(), price: form.price, visit_reason: form.visit_reason.trim() };
    if (await run(() => api("/services/", { method: "POST", body }), `${body.name} added.`)) setForm(EMPTY);
  };
  const save = async (s) => {
    const body = { price: edit.price, visit_reason: edit.visit_reason.trim() };
    if (await run(() => api(`/services/${s.id}/`, { method: "PATCH", body }), `${s.name} updated.`)) setEdit(null);
  };
  const toggle = (s) => run(() => api(`/services/${s.id}/`, { method: "PATCH", body: { is_active: !s.is_active } }),
    s.is_active ? `${s.name} switched off. It no longer shows for booking or new invoices.` : `${s.name} is back on.`);

  return (
    <>
      <Msg m={msg} />
      <form className="card form-row" onSubmit={add}>
        <label>Service name
          <input value={form.name} maxLength={150} required onChange={(e) => setForm({ ...form, name: e.target.value })} />
        </label>
        <label>Price
          <input type="number" min="0" step="0.01" size="8" required value={form.price}
                 onChange={(e) => setForm({ ...form, price: e.target.value })} />
        </label>
        <label>Visit reason <small>(optional)</small>
          <ReasonInput value={form.visit_reason} onChange={(v) => setForm({ ...form, visit_reason: v })} placeholder="e.g. Chemotherapy session" />
        </label>
        <button className="primary" disabled={busy}>Add service</button>
      </form>
      <p className="hint">A visit reason links the service to booking: patients see its price when they pick that reason, and the invoice is opened for them. Leave it empty for services that are only billed by hand.</p>
      <Table
        head={["Service", "Price", "Visit reason", "Status", ""]}
        empty="No services yet."
        rows={rows.map((s) => {
          const editing = edit?.id === s.id;
          return (
            <tr key={s.id} style={s.is_active ? undefined : { opacity: 0.65 }}>
              <td><b>{s.name}</b>{s.icd10_code && <><br /><small>{s.icd10_code}</small></>}</td>
              <td>{editing
                ? <input type="number" min="0" step="0.01" size="8" value={edit.price} onChange={(e) => setEdit({ ...edit, price: e.target.value })} />
                : money(s.price)}</td>
              <td>{editing
                ? <ReasonInput value={edit.visit_reason} onChange={(v) => setEdit({ ...edit, visit_reason: v })} />
                : s.visit_reason || "—"}</td>
              <td><Badge s={s.is_active ? "active" : "cancelled"} />{!s.is_active && <> <small>off</small></>}</td>
              <td>
                {editing ? (
                  <>
                    <button className="primary" disabled={busy || edit.price === ""} onClick={() => save(s)}>Save</button>
                    <button disabled={busy} onClick={() => setEdit(null)}>Cancel</button>
                  </>
                ) : (
                  <>
                    <button disabled={busy} onClick={() => setEdit({ id: s.id, price: s.price, visit_reason: s.visit_reason })}>Edit</button>
                    <button disabled={busy} onClick={() => toggle(s)}>{s.is_active ? "Switch off" : "Switch on"}</button>
                  </>
                )}
              </td>
            </tr>
          );
        })}
      />
    </>
  );
}
