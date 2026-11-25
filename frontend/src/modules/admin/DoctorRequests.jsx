// Admin: doctors who registered themselves and wait for a decision.
import { useState } from "react";
import { api } from "../../api.js";
import { Badge, Msg, errorText, useList } from "../../shared/ui.jsx";

const FILTERS = [["pending", "Waiting"], ["approved", "Approved"], ["rejected", "Rejected"], ["", "All"]];
const when = (v) => new Date(v).toLocaleString([], { day: "numeric", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" });

/** The licence needs the sign-in token, so it is fetched and opened as a blob instead of linked. */
async function openLicense(url, setMsg) {
  try {
    const res = await fetch(url, { headers: { Authorization: `Bearer ${localStorage.getItem("access")}` } });
    if (!res.ok) throw new Error();
    window.open(URL.createObjectURL(await res.blob()), "_blank", "noopener");
  } catch {
    setMsg({ ok: false, text: "Could not open the licence file." });
  }
}

function Request({ r, onChanged, setMsg }) {
  const [rejecting, setRejecting] = useState(false);
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  const d = r.doctor || {};

  const decide = async (what, body) => {
    setBusy(true);
    try {
      await api(`/admin/doctor-requests/${r.id}/${what}/`, { method: "POST", body: body || {} });
      setMsg({ ok: true, text: what === "approve" ? `${r.name} was approved and notified.` : `${r.name}'s request was rejected.` });
      setRejecting(false);
      onChanged();
    } catch (x) {
      setMsg({ ok: false, text: errorText(x) });
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="card">
      <div className="form-row" style={{ justifyContent: "space-between", marginBottom: 0 }}>
        <div><b>Dr. {r.name}</b> <Badge s={r.status} /><br /><small>Sent {when(r.submitted_at)}</small></div>
        {r.license_url && <button className="sm" onClick={() => openLicense(r.license_url, setMsg)}>View licence</button>}
      </div>
      <dl className="rq-detail">
        <div><dt>Email</dt><dd>{r.email}</dd></div>
        <div><dt>Phone</dt><dd>{r.phone || "—"}</dd></div>
        <div><dt>Specialty</dt><dd>{d.specialty || "—"}</dd></div>
        <div><dt>Licence number</dt><dd>{d.license_no || "—"}</dd></div>
        <div><dt>Experience</dt><dd>{d.years_experience != null ? `${d.years_experience} years` : "—"}</dd></div>
        <div><dt>Education</dt><dd>{d.education || "—"}</dd></div>
        <div><dt>Languages</dt><dd>{d.languages || "—"}</dd></div>
        <div><dt>Focus areas</dt><dd>{d.focus_areas || "—"}</dd></div>
        {d.bio && <div style={{ gridColumn: "1 / -1" }}><dt>Bio</dt><dd>{d.bio}</dd></div>}
        {r.status === "rejected" && <div style={{ gridColumn: "1 / -1" }}><dt>Rejected by {r.reviewed_by_name || "an admin"}</dt><dd>{r.rejection_reason}</dd></div>}
        {r.status === "approved" && <div><dt>Approved by</dt><dd>{r.reviewed_by_name || "—"} · {r.reviewed_at && when(r.reviewed_at)}</dd></div>}
      </dl>
      {r.status === "pending" && (rejecting ? (
        <form className="rq-actions" onSubmit={(e) => { e.preventDefault(); decide("reject", { reason }); }}>
          <label style={{ flex: 1 }}>Reason (the doctor will see it)
            <input value={reason} maxLength={500} onChange={(e) => setReason(e.target.value)} autoFocus required />
          </label>
          <button className="danger" disabled={busy || !reason.trim()}>Reject request</button>
          <button type="button" className="ghost" onClick={() => setRejecting(false)}>Cancel</button>
        </form>
      ) : (
        <div className="rq-actions">
          <button className="primary" disabled={busy} onClick={() => decide("approve")}>Approve</button>
          <button className="danger" disabled={busy} onClick={() => setRejecting(true)}>Reject…</button>
        </div>
      ))}
    </div>
  );
}

export function DoctorRequests({ onChanged }) {
  const [filter, setFilter] = useState("pending");
  const [rows, load] = useList(`/admin/doctor-requests/${filter ? `?status=${filter}` : ""}`);
  const [msg, setMsg] = useState(null);
  return (
    <>
      <div className="bl-filters" role="tablist">
        {FILTERS.map(([v, label]) => (
          <button key={v || "all"} className={filter === v ? "on" : ""} aria-pressed={filter === v} onClick={() => setFilter(v)}>{label}</button>
        ))}
      </div>
      <Msg m={msg} />
      {rows.length === 0 && <p className="hint">{filter === "pending" ? "No requests are waiting." : "Nothing here."}</p>}
      {rows.map((r) => <Request key={r.id} r={r} setMsg={setMsg} onChanged={() => { load(); onChanged?.(); }} />)}
    </>
  );
}
