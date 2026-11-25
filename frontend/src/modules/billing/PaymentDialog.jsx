// Pay an invoice. Patients pay by card; staff at the desk record cash, card or insurance.
// Used by the Invoices tab and by the appointments screens.
import { useEffect, useRef, useState } from "react";
import { api } from "../../api.js";
import { Icon } from "../../shared/Icon.jsx";
import { errorText } from "../../shared/ui.jsx";
import { METHODS, money } from "./money.js";

/** invoice: {id, number, total, paid} (either an invoice row or an appointment's `bill`). */
export function PaymentDialog({ invoice, staff, onDone, onClose }) {
  const ref = useRef(null);
  const left = Math.max(0, Number(invoice.total) - Number(invoice.paid));
  const [amount, setAmount] = useState(left.toFixed(2));
  const [method, setMethod] = useState(staff ? "cash" : "card");
  const [txn, setTxn] = useState(""), [busy, setBusy] = useState(false), [err, setErr] = useState("");
  useEffect(() => { ref.current.showModal(); return () => ref.current?.open && ref.current.close(); }, []);

  const submit = (e) => {
    e.preventDefault();
    setBusy(true); setErr("");
    api(`/invoices/${invoice.id}/pay/`, { method: "POST", body: { amount, method, ...(txn.trim() ? { transaction_ref: txn.trim() } : {}) } })
      .then((inv) => onDone(inv)).catch((x) => { setErr(errorText(x)); setBusy(false); });
  };

  return (
    <dialog ref={ref} className="confirm pay-dialog" aria-labelledby="pay-title" onClose={() => !busy && onClose()}
            onClick={(e) => e.target === ref.current && !busy && onClose()}>
      <span className="confirm-icon ok"><Icon name="receipt" /></span>
      <h2 id="pay-title">{staff ? "Record a payment" : "Pay your bill"}</h2>
      <p>{invoice.number} · {money(left)} left to pay</p>
      <form onSubmit={submit} className="pay-form">
        {staff ? (
          <div className="pay-methods" role="radiogroup" aria-label="Method">
            {Object.entries(METHODS).map(([k, label]) => (
              <button type="button" key={k} role="radio" aria-checked={method === k} className={method === k ? "on" : ""}
                      onClick={() => setMethod(k)}>{label}</button>
            ))}
          </div>
        ) : <p className="hint pay-note"><Icon name="shield" /> Paying by card. Cash and insurance are taken at the reception desk.</p>}
        <label>Amount
          <input type="number" min="0.01" step="0.01" max={left.toFixed(2)} value={amount} onChange={(e) => setAmount(e.target.value)} required />
        </label>
        {method !== "cash" && (
          <label>{method === "insurance" ? "Insurance approval number" : "Card transaction reference"} <small>(optional)</small>
            <input value={txn} maxLength={60} onChange={(e) => setTxn(e.target.value)} />
          </label>
        )}
        {err && <p className="msg err">{err}</p>}
        <div className="confirm-actions">
          <button type="button" data-cancel onClick={onClose} disabled={busy}>Not now</button>
          <button className="primary" disabled={busy || !(Number(amount) > 0)}>{busy ? "Saving…" : staff ? "Record payment" : `Pay ${money(amount)}`}</button>
        </div>
      </form>
    </dialog>
  );
}
