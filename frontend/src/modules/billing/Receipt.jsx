// One invoice as a printable page: "Receipt" once paid, "Invoice" while money is still due.
import { useEffect, useState } from "react";
import { api } from "../../api.js";
import { Icon } from "../../shared/Icon.jsx";
import { Badge, Logo, errorText } from "../../shared/ui.jsx";
import { METHODS, money } from "./money.js";

const date = (v) => new Date(v).toLocaleDateString([], { day: "numeric", month: "long", year: "numeric" });
const dateTime = (v) => new Date(v).toLocaleString([], { day: "numeric", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" });

export function Receipt({ id, onBack, onPay }) {
  const [inv, setInv] = useState(null), [err, setErr] = useState("");
  const load = () => api(`/invoices/${id}/`).then(setInv).catch((e) => setErr(errorText(e)));
  useEffect(() => { load(); }, [id]);
  useEffect(() => { if (inv) document.title = `${inv.invoice_number} · OncoSphere`; }, [inv]);

  if (err) return <p className="msg err">{err}</p>;
  if (!inv) return <p className="hint">Loading…</p>;
  const left = Number(inv.total_amount) - Number(inv.paid_amount);
  const paid = inv.status === "paid";

  return (
    <>
      <div className="rc-actions">
        <button className="with-icon" onClick={onBack}>← All invoices</button>
        <span className="spacer" />
        {inv.status === "pending" && onPay && <button className="primary with-icon" onClick={() => onPay(inv, load)}><Icon name="receipt" /> Pay {money(left)}</button>}
        <button className="with-icon" onClick={() => window.print()}><Icon name="upload" /> Print / save as PDF</button>
      </div>

      <article className={`receipt ${paid ? "is-paid" : ""}`}>
        <header className="rc-head">
          <div className="rc-brand"><Logo /> <span><b>OncoSphere</b><small>Oncology care, connected</small></span></div>
          <div className="rc-title">
            <h2>{paid ? "Payment receipt" : "Invoice"}</h2>
            <b>{inv.invoice_number}</b>
            <Badge s={inv.status} />
          </div>
        </header>

        <section className="rc-grid">
          <div><small>Billed to</small><b>{inv.patient_name}</b><span>{inv.patient_mrn}</span></div>
          <div><small>Issued</small><b>{date(inv.issue_date)}</b><span>Due {date(inv.due_date)}</span></div>
          {inv.visit && (
            <div><small>Visit</small><b>{inv.visit.reason || "Visit"}</b>
              <span>{dateTime(inv.visit.start_time)} · {inv.visit.doctor_name}</span></div>
          )}
        </section>

        <table className="rc-table">
          <thead><tr><th>Service</th><th>ICD-10</th><th className="num">Qty</th><th className="num">Unit price</th><th className="num">Amount</th></tr></thead>
          <tbody>
            {inv.items.map((x) => (
              <tr key={x.id}><td>{x.service_name}</td><td>{x.icd10_code || "—"}</td><td className="num">{x.quantity}</td>
                <td className="num">{money(x.unit_price)}</td><td className="num">{money(x.line_total)}</td></tr>
            ))}
          </tbody>
        </table>

        <div className="rc-bottom">
          <div className="rc-payments">
            <small>Payments</small>
            {inv.payments.length ? inv.payments.map((p) => (
              <p key={p.id}><b>{money(p.amount)}</b> · {METHODS[p.method] || p.method} · {dateTime(p.paid_at)}
                {p.transaction_ref && <> · ref {p.transaction_ref}</>}{p.recorded_by_name && <> · by {p.recorded_by_name}</>}</p>
            )) : <p className="hint">No payments yet. Pay online, or at the reception desk before the visit.</p>}
          </div>
          <dl className="rc-totals">
            <dt>Total</dt><dd>{money(inv.total_amount)}</dd>
            <dt>Paid</dt><dd>{money(inv.paid_amount)}</dd>
            <dt className="rc-due">Left to pay</dt><dd className="rc-due">{money(left)}</dd>
          </dl>
        </div>
        {paid && <div className="rc-stamp" aria-hidden="true">PAID</div>}
        <footer className="rc-foot">Thank you. Keep this {paid ? "receipt" : "invoice"} for your records.</footer>
      </article>
    </>
  );
}
