// Doctor self-registration. The account stays switched off until an administrator approves the request.
import { useState } from "react";
import { Link } from "react-router-dom";
import { registerDoctor } from "../api.js";
import { Alert, AuthField, AuthLayout, AuthTextArea, Icon, PasswordField, SubmitButton, requestProblem } from "./AuthLayout.jsx";

const EMPTY = {
  first_name: "", last_name: "", email: "", phone: "",
  specialty: "", license_no: "", years_experience: "", education: "", languages: "", focus_areas: "", bio: "",
  password: "", confirm: "",
};
const EMAIL = /^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$/;
const MAX_FILE = 5 * 1024 * 1024;
const FILE_TYPES = ["pdf", "jpg", "jpeg", "png"];

function check(f, file) {
  const e = {};
  const need = (k, msg) => { if (!String(f[k]).trim()) e[k] = msg; };
  need("first_name", "Enter your first name.");
  need("last_name", "Enter your last name.");
  need("email", "Enter your email address.");
  need("phone", "Enter a phone number.");
  need("specialty", "Enter your specialty, e.g. Medical oncology.");
  need("license_no", "Enter your medical licence number.");
  if (f.email.trim() && !EMAIL.test(f.email.trim())) e.email = "Enter a valid email address in English letters, like name@example.com.";
  if (f.years_experience !== "" && !(Number(f.years_experience) >= 0 && Number(f.years_experience) <= 70)) e.years_experience = "Enter a number from 0 to 70.";
  if (!file) e.license_document = "Attach a photo or PDF of your licence.";
  else if (!FILE_TYPES.includes(file.name.split(".").pop().toLowerCase())) e.license_document = "Use a PDF, JPG or PNG file.";
  else if (file.size > MAX_FILE) e.license_document = "The file is larger than 5 MB.";
  if (f.password.length < 8) e.password = "Use at least 8 characters.";
  else if (/^\d+$/.test(f.password)) e.password = "Mix in letters, not only numbers.";
  if (!f.confirm) e.confirm = "Type your password again.";
  else if (f.confirm !== f.password) e.confirm = "Passwords don't match.";
  return e;
}

const serverErrors = (data) =>
  !data || typeof data !== "object" ? {} : Object.fromEntries(Object.entries(data).map(([k, v]) => [k, [].concat(v).join(" ")]));

export default function DoctorRegister() {
  const [f, setF] = useState(EMPTY);
  const [file, setFile] = useState(null);
  const [errors, setErrors] = useState({});
  const [alert, setAlert] = useState("");
  const [busy, setBusy] = useState(false);
  const [sent, setSent] = useState(false);

  const set = (k) => (e) => {
    setF({ ...f, [k]: e.target.value });
    if (errors[k]) setErrors({ ...errors, [k]: undefined });
  };
  const err = (k) => errors[k];

  const submit = async (e) => {
    e.preventDefault();
    setAlert("");
    const found = check(f, file);
    setErrors(found);
    if (Object.keys(found).length) {
      setAlert("Please fix the highlighted fields.");
      document.querySelector(".auth-field.has-error input, .auth-field.has-error textarea")?.focus();
      return;
    }
    const body = new FormData();
    const { confirm, ...fields } = f;
    Object.entries(fields).forEach(([k, v]) => { if (String(v).trim() !== "") body.append(k, String(v).trim()); });
    body.append("license_document", file);
    setBusy(true);
    try {
      await registerDoctor(body);
      setSent(true);
    } catch (ex) {
      const net = requestProblem(ex);
      if (net) setAlert(net);
      else {
        const fieldErrs = serverErrors(ex.data);
        setErrors(fieldErrs);
        setAlert(fieldErrs.detail || fieldErrs.non_field_errors || "Please fix the highlighted fields.");
      }
    } finally {
      setBusy(false);
    }
  };

  if (sent) {
    return (
      <AuthLayout title="Request sent">
        <div className="auth-done">
          <h2>Your request was sent</h2>
          <p>An administrator will review your details and licence. You'll get an email when the decision is made,
            and you can sign in once your account is approved.</p>
          <Link to="/login" className="auth-secondary">Back to sign in</Link>
        </div>
      </AuthLayout>
    );
  }

  return (
    <AuthLayout title="Doctor registration">
      <header className="auth-head">
        <h2>Register as a doctor</h2>
        <p>An administrator checks your licence before your account is switched on.</p>
      </header>

      <form className="auth-form" onSubmit={submit} noValidate>
        <Alert>{alert}</Alert>

        <section className="auth-section" aria-labelledby="d-about">
          <h3 className="auth-section-title" id="d-about">About you</h3>
          <div className="auth-row">
            <AuthField label="First name" value={f.first_name} onChange={set("first_name")} dir="auto"
                       autoComplete="given-name" error={err("first_name")} autoFocus />
            <AuthField label="Last name" value={f.last_name} onChange={set("last_name")} dir="auto"
                       autoComplete="family-name" error={err("last_name")} />
          </div>
          <div className="auth-row">
            <AuthField label="Email" type="email" icon="mail" value={f.email} onChange={set("email")} dir="ltr"
                       autoComplete="email" autoCapitalize="none" spellCheck={false} error={err("email")}
                       placeholder="name@example.com" hint="You'll sign in with this email." />
            <AuthField label="Phone" type="tel" icon="phone" value={f.phone} onChange={set("phone")}
                       autoComplete="tel" error={err("phone")} placeholder="01X XXXX XXXX" />
          </div>
        </section>

        <section className="auth-section" aria-labelledby="d-work">
          <h3 className="auth-section-title" id="d-work">Profession and licence</h3>
          <div className="auth-row">
            <AuthField label="Specialty" value={f.specialty} onChange={set("specialty")} error={err("specialty")}
                       placeholder="e.g. Medical oncology" />
            <AuthField label="Licence number" value={f.license_no} onChange={set("license_no")} dir="ltr"
                       error={err("license_no")} />
          </div>
          <div className="auth-row">
            <AuthField label="Years of experience (optional)" type="number" min="0" max="70" value={f.years_experience}
                       onChange={set("years_experience")} error={err("years_experience")} />
            <AuthField label="Education (optional)" value={f.education} onChange={set("education")} dir="auto"
                       error={err("education")} placeholder="e.g. MD, Cairo University" />
          </div>
          <div className="auth-row">
            <AuthField label="Languages (optional)" value={f.languages} onChange={set("languages")}
                       error={err("languages")} placeholder="Arabic, English" />
            <AuthField label="Focus areas (optional)" value={f.focus_areas} onChange={set("focus_areas")} dir="auto"
                       error={err("focus_areas")} placeholder="Breast cancer, Lung cancer" />
          </div>
          <AuthTextArea label="Short bio (optional)" value={f.bio} onChange={set("bio")} maxLength={2000} dir="auto"
                        error={err("bio")} />
          <div className={`auth-field ${err("license_document") ? "has-error" : ""}`}>
            <label htmlFor="d-file">Licence document</label>
            <input id="d-file" className="auth-file" type="file" accept=".pdf,.jpg,.jpeg,.png"
                   onChange={(e) => { setFile(e.target.files?.[0] || null); setErrors({ ...errors, license_document: undefined }); }} />
            {err("license_document")
              ? <p className="auth-error"><Icon name="alert" /> {err("license_document")}</p>
              : <p className="auth-hint">A photo or PDF, up to 5 MB. Only administrators can open it.</p>}
          </div>
        </section>

        <section className="auth-section" aria-labelledby="d-pw">
          <h3 className="auth-section-title" id="d-pw">Password</h3>
          <div className="auth-row">
            <PasswordField label="Password" value={f.password} onChange={set("password")}
                           autoComplete="new-password" error={err("password")} />
            <PasswordField label="Confirm password" value={f.confirm} onChange={set("confirm")}
                           autoComplete="new-password" error={err("confirm")} />
          </div>
        </section>

        <SubmitButton busy={busy} busyText="Sending your request…">Send registration request</SubmitButton>
      </form>

      <p className="auth-switch">Already approved? <Link to="/login">Sign in</Link> · Patient? <Link to="/register">Create account</Link></p>
    </AuthLayout>
  );
}
