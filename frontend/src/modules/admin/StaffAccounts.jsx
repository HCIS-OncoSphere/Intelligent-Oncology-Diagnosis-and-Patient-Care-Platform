// Admin: create a doctor account directly. The new person gets a temporary password
// (shown here once, and e-mailed) and must choose their own at the first sign-in.
import { useState } from "react";
import { api } from "../../api.js";
import { Msg, errorText } from "../../shared/ui.jsx";

const PERSON = { first_name: "", last_name: "", email: "", phone: "" };
const DOCTOR = { ...PERSON, specialty: "", license_no: "", years_experience: "", education: "", languages: "", focus_areas: "", bio: "" };

function Created({ made, onClose }) {
  return (
    <div className="secret-box" role="status">
      <b>Account created for {made.email}.</b>
      {made.temporary_password ? (
        <p>Temporary password: <code>{made.temporary_password}</code><br />
          <small>{made.emailed ? "It was also e-mailed to them." : "No e-mail was sent (mail isn't set up), so give it to them yourself."} It is not shown again.</small></p>
      ) : <p><small>They sign in with the password you set and must change it at first sign-in.</small></p>}
      <button className="sm" onClick={onClose}>Done</button>
    </div>
  );
}

function AccountForm() {
  const [f, setF] = useState(DOCTOR);
  const [file, setFile] = useState(null);
  const [msg, setMsg] = useState(null), [made, setMade] = useState(null), [busy, setBusy] = useState(false);
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true); setMsg(null);
    const body = new FormData();
    Object.entries(f).forEach(([k, v]) => { if (String(v).trim() !== "") body.append(k, String(v).trim()); });
    if (file) body.append("license_document", file);
    try {
      setMade(await api("/admin/doctors/", { method: "POST", body }));
      setF(DOCTOR); setFile(null); e.target.reset();
    } catch (x) {
      setMsg({ ok: false, text: errorText(x) });
    } finally {
      setBusy(false);
    }
  };

  return (
    <fieldset>
      <legend>Add a doctor</legend>
      <form onSubmit={submit}>
        <div className="form-row">
          <label>First name<input value={f.first_name} onChange={set("first_name")} required /></label>
          <label>Last name<input value={f.last_name} onChange={set("last_name")} required /></label>
          <label>Email<input type="email" value={f.email} onChange={set("email")} required /></label>
          <label>Phone<input type="tel" value={f.phone} onChange={set("phone")} /></label>
        </div>
        {(
          <>
            <div className="form-row">
              <label>Specialty<input value={f.specialty} onChange={set("specialty")} required /></label>
              <label>Licence number<input value={f.license_no} onChange={set("license_no")} required /></label>
              <label>Years of experience<input type="number" min="0" max="70" value={f.years_experience} onChange={set("years_experience")} /></label>
              <label>Education<input value={f.education} onChange={set("education")} /></label>
            </div>
            <div className="form-row">
              <label>Languages<input value={f.languages} onChange={set("languages")} placeholder="Arabic, English" /></label>
              <label>Focus areas<input value={f.focus_areas} onChange={set("focus_areas")} /></label>
              <label>Licence file (optional)<input type="file" accept=".pdf,.jpg,.jpeg,.png" onChange={(e) => setFile(e.target.files?.[0] || null)} /></label>
            </div>
          </>
        )}
        <button className="primary" disabled={busy}>{busy ? "Creating…" : "Create doctor account"}</button>
      </form>
      <Msg m={msg} />
      {made && <Created made={made} onClose={() => setMade(null)} />}
    </fieldset>
  );
}

export function StaffAccounts() {
  return (
    <>
      <p className="hint">The account is active straight away. The person is asked to replace the temporary password when they first sign in.</p>
      <AccountForm />
    </>
  );
}
