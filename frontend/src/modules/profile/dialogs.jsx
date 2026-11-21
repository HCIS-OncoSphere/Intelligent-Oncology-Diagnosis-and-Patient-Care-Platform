// Edit-profile and change-photo popups (native <dialog>, so Esc and focus trapping work out of the box).
import { useEffect, useRef, useState } from "react";
import { api } from "../../api.js";
import { Icon } from "../../shared/Icon.jsx";
import { errorText } from "../../shared/ui.jsx";

const MAX_BYTES = 5 * 1024 * 1024;
const TYPES = ["image/jpeg", "image/png", "image/webp"];

function Dialog({ title, onClose, children, wide }) {
  const ref = useRef(null);
  useEffect(() => {
    const d = ref.current;
    d.showModal();
    return () => d.open && d.close();
  }, []);
  return (
    <dialog ref={ref} className={`pf-dialog ${wide ? "wide" : ""}`} onClose={onClose}
            onClick={(e) => e.target === ref.current && onClose()}>
      <div className="pf-dialog-head">
        <h2>{title}</h2>
        <button type="button" className="pf-x" onClick={onClose} aria-label="Close"><Icon name="x" /></button>
      </div>
      {children}
    </dialog>
  );
}

const Field = ({ label, hint, wide, ...input }) => (
  <label className={`pf-field ${wide ? "wide" : ""}`}>
    <span>{label}</span>
    {input.rows ? <textarea {...input} /> : <input {...input} />}
    {hint && <small>{hint}</small>}
  </label>
);

export function EditDialog({ p, onClose, onSaved }) {
  const isPatient = !!p.patient, isDoctor = !!p.doctor;
  const [f, setF] = useState({
    first_name: p.first_name, last_name: p.last_name, email: p.email,
    phone: (p.patient && p.patient.phone) || p.phone || "",
    ...(isPatient ? { address: p.patient.address, emergency_contact: p.patient.emergency_contact } : {}),
    ...(isDoctor ? {
      bio: p.doctor.bio, years_experience: p.doctor.years_experience ?? "", education: p.doctor.education,
      languages: p.doctor.languages, focus_areas: p.doctor.focus_areas,
    } : {}),
  });
  const [err, setErr] = useState(""), [busy, setBusy] = useState(false);
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });

  const save = async (e) => {
    e.preventDefault();
    setBusy(true); setErr("");
    const body = { ...f };
    if (isDoctor) body.years_experience = body.years_experience === "" ? null : Number(body.years_experience);
    try { onSaved(await api("/profile/", { method: "PATCH", body })); onClose(); }
    catch (ex) { setErr(errorText(ex)); setBusy(false); }
  };

  return (
    <Dialog title="Edit profile" onClose={onClose} wide>
      <form onSubmit={save} className="pf-form">
        <div className="pf-form-grid">
          <Field label="First name" value={f.first_name} onChange={set("first_name")} required autoComplete="given-name" />
          <Field label="Last name" value={f.last_name} onChange={set("last_name")} required autoComplete="family-name" />
          <Field label="Email" type="email" value={f.email} onChange={set("email")} required autoComplete="email" />
          <Field label="Phone" type="tel" value={f.phone} onChange={set("phone")} autoComplete="tel" />
          {isPatient && <>
            <Field label="Address" wide value={f.address} onChange={set("address")} autoComplete="street-address" />
            <Field label="Emergency contact" wide value={f.emergency_contact} onChange={set("emergency_contact")}
                   placeholder="Name, relation and phone" hint="Who we call if we can't reach you." />
          </>}
          {isDoctor && <>
            <Field label="About you" wide rows={4} value={f.bio} onChange={set("bio")} maxLength={2000}
                   placeholder="Your clinical focus and how you work with patients" />
            <Field label="Years of experience" type="number" min="0" max="80" value={f.years_experience} onChange={set("years_experience")} />
            <Field label="Education" value={f.education} onChange={set("education")} placeholder="MD, Cairo University" />
            <Field label="Languages" value={f.languages} onChange={set("languages")} placeholder="Arabic, English" hint="Separate with commas." />
            <Field label="Focus areas" value={f.focus_areas} onChange={set("focus_areas")} placeholder="Breast cancer, Lung cancer" hint="Separate with commas." />
          </>}
        </div>
        {isPatient && <p className="pf-note">Medical details such as diagnosis and blood type are updated by your care team.</p>}
        {err && <p className="pf-error" role="alert"><Icon name="x" /> {err}</p>}
        <div className="pf-dialog-actions">
          <button type="button" onClick={onClose}>Cancel</button>
          <button className="primary" disabled={busy}>{busy ? "Saving…" : "Save changes"}</button>
        </div>
      </form>
    </Dialog>
  );
}

export function PhotoDialog({ p, kind, onClose, onSaved }) {
  const isCover = kind === "cover";
  const current = isCover ? p.cover : p.avatar;
  const [file, setFile] = useState(null), [preview, setPreview] = useState(null);
  const [err, setErr] = useState(""), [busy, setBusy] = useState(false), [over, setOver] = useState(false);
  const input = useRef(null);

  useEffect(() => () => preview && URL.revokeObjectURL(preview), [preview]);

  const pick = (f) => {
    setErr("");
    if (!f) return;
    if (!TYPES.includes(f.type)) return setErr("Use a JPG, PNG or WebP picture.");
    if (f.size > MAX_BYTES) return setErr("That picture is larger than 5 MB.");
    setFile(f);
    setPreview(URL.createObjectURL(f));
  };

  const run = async (request) => {
    setBusy(true); setErr("");
    try { onSaved(await request()); onClose(); }
    catch (ex) { setErr(errorText(ex)); setBusy(false); }
  };
  const upload = () => {
    const form = new FormData();
    form.append("kind", kind);
    form.append("file", file);
    run(() => api("/profile/photo/", { method: "POST", body: form }));
  };
  const remove = () => run(() => api(`/profile/photo/?kind=${kind}`, { method: "DELETE" }));

  const shown = preview || current;
  return (
    <Dialog title={isCover ? "Cover image" : "Profile photo"} onClose={onClose}>
      <div className={`pf-preview ${isCover ? "is-cover" : "is-avatar"}`}>
        {shown ? <img src={shown} alt="Preview" /> : <span><Icon name={isCover ? "image" : "user"} /></span>}
      </div>
      <div className={`pf-drop ${over ? "over" : ""}`}
           onDragOver={(e) => { e.preventDefault(); setOver(true); }}
           onDragLeave={() => setOver(false)}
           onDrop={(e) => { e.preventDefault(); setOver(false); pick(e.dataTransfer.files[0]); }}>
        <Icon name="upload" />
        <span>Drop a picture here or{" "}
          <button type="button" className="pf-link" onClick={() => input.current.click()}>choose a file</button>
        </span>
        <small>JPG, PNG or WebP, up to 5 MB. {isCover ? "Wide pictures work best." : "It's cropped to a circle."}</small>
        <input ref={input} type="file" accept={TYPES.join(",")} hidden onChange={(e) => pick(e.target.files[0])} />
      </div>
      {err && <p className="pf-error" role="alert"><Icon name="x" /> {err}</p>}
      <div className="pf-dialog-actions">
        {current && !file
          ? <button type="button" className="danger" onClick={remove} disabled={busy}><Icon name="trash" /> Remove</button>
          : <span />}
        <span className="pf-actions-right">
          <button type="button" onClick={onClose}>Cancel</button>
          <button type="button" className="primary" onClick={upload} disabled={!file || busy}>{busy ? "Saving…" : "Save"}</button>
        </span>
      </div>
    </Dialog>
  );
}
