// Patient / doctor self-registration. Staff and admin accounts are created by an administrator, not here.
// Use the toggle to switch between "Patient" (instant account) and "Doctor" (awaits admin approval).
import { useState, useEffect } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { login, register, registerDoctor } from "../api.js";
import { Alert, AuthField, AuthLayout, AuthSelect, AuthTextArea, Icon, PasswordField, SubmitButton, requestProblem } from "./AuthLayout.jsx";
import { GoogleSignInButton } from "./GoogleSignIn.jsx";

// ---------------------------------------------------------------------------
// Shared
// ---------------------------------------------------------------------------

const EMAIL = /^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$/;
const MAX_FILE = 5 * 1024 * 1024;
const FILE_TYPES = ["pdf", "jpg", "jpeg", "png"];

function serverErrors(data) {
  if (!data || typeof data !== "object") return {};
  return Object.fromEntries(Object.entries(data).map(([k, v]) => [k, [].concat(v).join(" ")]));
}

/** 0–4 score with a label, for the meter under the password field. */
function strength(pw) {
  if (!pw) return { score: 0, label: "" };
  let s = 0;
  if (pw.length >= 8) s++;
  if (pw.length >= 12) s++;
  if (/[a-z]/.test(pw) && /[A-Z]/.test(pw)) s++;
  if (/\d/.test(pw) && /[^A-Za-z0-9]/.test(pw)) s++;
  if (pw.length < 8 || /^\d+$/.test(pw)) s = Math.min(s, 1);
  return { score: s, label: ["Too weak", "Weak", "Fair", "Good", "Strong"][s] };
}

// Local calendar date as YYYY-MM-DD.
const today = () => {
  const d = new Date();
  d.setMinutes(d.getMinutes() - d.getTimezoneOffset());
  return d.toISOString().slice(0, 10);
};

// ---------------------------------------------------------------------------
// Patient form
// ---------------------------------------------------------------------------

const PATIENT_EMPTY = {
  first_name: "", last_name: "", date_of_birth: "", gender: "",
  email: "", phone: "", address: "", blood_type: "", national_id: "",
  emergency_contact: "", emergency_contact_phone: "", password: "", confirm: "",
};
const BLOOD = ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"].map((b) => [b, b]);
const GENDERS = [["F", "Female"], ["M", "Male"], ["O", "Other"]];

function patientCheck(f) {
  const e = {};
  const need = (k, msg) => { if (!String(f[k]).trim()) e[k] = msg; };
  need("first_name", "Enter your first name.");
  need("last_name", "Enter your last name.");
  need("date_of_birth", "Enter your date of birth.");
  need("gender", "Choose one.");
  need("email", "Enter your email address.");
  need("phone", "Enter a phone number we can reach you on.");
  need("address", "Enter your address.");
  need("emergency_contact", "Enter the name of someone we can call in an emergency.");
  need("emergency_contact_phone", "Enter their phone number.");
  if (f.national_id.trim() && !/^\d{14}$/.test(f.national_id.trim())) e.national_id = "National ID is 14 digits.";
  if (f.date_of_birth && f.date_of_birth > today()) e.date_of_birth = "Date of birth can't be in the future.";
  if (f.email.trim() && !EMAIL.test(f.email.trim())) {
    e.email = /[^\x00-\x7F]/.test(f.email)
      ? "Write the email in English letters, like name@example.com."
      : "Enter a valid email address, like name@example.com.";
  }
  if (f.password.length < 8) e.password = "Use at least 8 characters.";
  else if (/^\d+$/.test(f.password)) e.password = "Mix in letters, not only numbers.";
  if (!f.confirm) e.confirm = "Type your password again.";
  else if (f.confirm !== f.password) e.confirm = "Passwords don't match.";
  return e;
}

function PatientForm({ f, setF, errors, setErrors, alert, setAlert, setBusy, busy, onDone }) {
  const set = (k) => (e) => {
    setF({ ...f, [k]: e.target.value });
    if (errors[k]) setErrors({ ...errors, [k]: undefined });
  };
  const err = (k) => errors[k];
  const pw = strength(f.password);

  const submit = async (e) => {
    e.preventDefault();
    setAlert("");
    const found = patientCheck(f);
    setErrors(found);
    if (Object.keys(found).length) {
      setAlert("Please fix the highlighted fields.");
      document.querySelector(".auth-field.has-error input, .auth-field.has-error button")?.focus();
      return;
    }
    setBusy(true);
    const { confirm, ...body } = f;
    body.email = body.email.trim();
    body.first_name = body.first_name.trim();
    body.last_name = body.last_name.trim();
    for (const k of ["phone", "address", "national_id", "emergency_contact", "emergency_contact_phone"]) body[k] = body[k].trim();
    try {
      await register(body);
    } catch (ex) {
      setBusy(false);
      const net = requestProblem(ex);
      if (net) return setAlert(net);
      const fieldErrs = serverErrors(ex.data);
      setErrors(fieldErrs);
      const general = fieldErrs.detail || fieldErrs.non_field_errors;
      setAlert(general || "Please fix the highlighted fields.");
      return;
    }
    try {
      onDone(await login(body.email, body.password));
    } catch {
      setBusy(false);
      setAlert("Your account was created, but signing in failed. Go to Sign in and try again.");
    }
  };

  return (
    <form className="auth-form" onSubmit={submit} noValidate>
      <Alert>{alert}</Alert>

      <section className="auth-section" aria-labelledby="sec-about">
        <h3 className="auth-section-title" id="sec-about">About you</h3>
        <div className="auth-row">
          <AuthField label="First name" value={f.first_name} onChange={set("first_name")}
                     autoComplete="given-name" dir="auto" error={err("first_name")} autoFocus />
          <AuthField label="Last name" value={f.last_name} onChange={set("last_name")}
                     autoComplete="family-name" dir="auto" error={err("last_name")} />
        </div>
        <div className="auth-row">
          <AuthField label="Date of birth" type="date" icon="calendar" value={f.date_of_birth}
                     onChange={set("date_of_birth")} max={today()} min="1900-01-01"
                     autoComplete="bday" error={err("date_of_birth")} />
          <div className={`auth-field ${err("gender") ? "has-error" : ""}`}>
            <span className="auth-label" id="gender-label">Gender</span>
            <div className="auth-choice" role="radiogroup" aria-labelledby="gender-label">
              {GENDERS.map(([v, label]) => (
                <button key={v} type="button" role="radio" aria-checked={f.gender === v}
                        className={f.gender === v ? "on" : ""}
                        onClick={() => set("gender")({ target: { value: v } })}>
                  {label}
                </button>
              ))}
            </div>
            {err("gender") && <p className="auth-error"><Icon name="alert" /> {err("gender")}</p>}
          </div>
        </div>
      </section>

      <section className="auth-section" aria-labelledby="sec-contact">
        <h3 className="auth-section-title" id="sec-contact">Contact</h3>
        <div className="auth-row">
          <AuthField label="Email" type="email" icon="mail" value={f.email} onChange={set("email")}
                     autoComplete="email" autoCapitalize="none" spellCheck={false} error={err("email")}
                     placeholder="name@example.com" dir="ltr"
                     hint="You'll sign in with this email. English letters only." />
          <AuthField label="Phone" type="tel" icon="phone" value={f.phone} onChange={set("phone")}
                     autoComplete="tel" error={err("phone")} placeholder="01X XXXX XXXX" />
        </div>
        <AuthField label="Address" value={f.address} onChange={set("address")} autoComplete="street-address"
                   dir="auto" error={err("address")} placeholder="Street, area, city" />
      </section>

      <section className="auth-section" aria-labelledby="sec-health">
        <h3 className="auth-section-title" id="sec-health">Health and emergency contact</h3>
        <div className="auth-row">
          <AuthSelect label="Blood type (optional)" value={f.blood_type} onChange={set("blood_type")}
                      options={BLOOD} placeholder="Don't know" error={err("blood_type")} />
          <AuthField label="National ID (optional)" inputMode="numeric" maxLength={14} value={f.national_id}
                     onChange={set("national_id")} error={err("national_id")} placeholder="14 digits" dir="ltr" />
        </div>
        <div className="auth-row">
          <AuthField label="Emergency contact" value={f.emergency_contact} onChange={set("emergency_contact")}
                     dir="auto" error={err("emergency_contact")} placeholder="Name and relation, e.g. Ali (husband)" />
          <AuthField label="Their phone" type="tel" icon="phone" value={f.emergency_contact_phone}
                     onChange={set("emergency_contact_phone")} error={err("emergency_contact_phone")} />
        </div>
      </section>

      <section className="auth-section" aria-labelledby="sec-signin">
        <h3 className="auth-section-title" id="sec-signin">Password</h3>
        <div className="auth-row">
          <PasswordField label="Password" value={f.password} onChange={set("password")}
                         autoComplete="new-password" error={err("password")} />
          <PasswordField label="Confirm password" value={f.confirm} onChange={set("confirm")}
                         autoComplete="new-password" error={err("confirm")} />
        </div>
        {f.password && (
          <div className={`auth-meter s${pw.score}`} aria-live="polite">
            <div className="auth-meter-bars">{[1, 2, 3, 4].map((i) => <span key={i} />)}</div>
            <span>{pw.label}</span>
          </div>
        )}
        <ul className="auth-rules">
          <li className={f.password.length >= 8 ? "met" : ""}><Icon name="check" /> At least 8 characters</li>
          <li className={f.password && !/^\d+$/.test(f.password) ? "met" : ""}><Icon name="check" /> Not only numbers</li>
          <li className={f.confirm && f.confirm === f.password ? "met" : ""}><Icon name="check" /> Both passwords match</li>
        </ul>
      </section>

      <SubmitButton busy={busy} busyText="Creating your account…">Create account</SubmitButton>
    </form>
  );
}

// ---------------------------------------------------------------------------
// Doctor form
// ---------------------------------------------------------------------------

const DOCTOR_EMPTY = {
  first_name: "", last_name: "", email: "", phone: "",
  specialty: "", license_no: "", years_experience: "", education: "", languages: "", focus_areas: "", bio: "",
  password: "", confirm: "",
};

function doctorCheck(f, file) {
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

function DoctorForm({ f, setF, errors, setErrors, alert, setAlert, setBusy, busy, file, setFile }) {
  const set = (k) => (e) => {
    setF({ ...f, [k]: e.target.value });
    if (errors[k]) setErrors({ ...errors, [k]: undefined });
  };
  const err = (k) => errors[k];

  const submit = async (e) => {
    e.preventDefault();
    setAlert("");
    const found = doctorCheck(f, file);
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
      // Doctor accounts await admin approval; no auto sign-in.
      setBusy(false);
      setAlert("Your request was sent. An administrator will review your licence and switch your account on.");
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

  return (
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
  );
}

// ---------------------------------------------------------------------------
// Register page with role toggle
// ---------------------------------------------------------------------------

export default function Register({ onDone }) {
  const [searchParams] = useSearchParams();
  const [role, setRole] = useState(searchParams.get("role") === "doctor" ? "doctor" : "patient");

  // Patient state
  const [pf, setPf] = useState(PATIENT_EMPTY);
  const [perrs, setPerrs] = useState({});
  // Doctor state
  const [df, setDf] = useState(DOCTOR_EMPTY);
  const [ders, setDers] = useState({});
  const [dfile, setDfile] = useState(null);

  const [alert, setAlert] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    setAlert("");
  }, [role]);

  return (
    <AuthLayout title="Create account">
      <header className="auth-head">
        <h2>Create your account</h2>
        <p>See your appointments, treatment plan and results in one place.</p>
      </header>

      {/* Role toggle */}
      <div className="auth-role-toggle">
        <button
          type="button"
          className={role === "patient" ? "on" : ""}
          onClick={() => setRole("patient")}
        >
          <Icon name="user" /> Patient
        </button>
        <button
          type="button"
          className={role === "doctor" ? "on" : ""}
          onClick={() => setRole("doctor")}
        >
          <Icon name="stethoscope" /> Doctor
        </button>
      </div>

      {role === "patient" && (
        <>
          <GoogleSignInButton onDone={onDone} onError={setAlert} mode="signup" />
          <p className="auth-divider"><span>Or create your account manually</span></p>
          <PatientForm
            f={pf} setF={setPf} errors={perrs} setErrors={setPerrs}
            alert={alert} setAlert={setAlert} setBusy={setBusy} busy={busy} onDone={onDone}
          />
        </>
      )}

      {role === "doctor" && (
        <DoctorForm
          f={df} setF={setDf} errors={ders} setErrors={setDers}
          alert={alert} setAlert={setAlert} setBusy={setBusy} busy={busy}
          file={dfile} setFile={setDfile}
        />
      )}

      <p className="auth-switch">Already have an account? <Link to="/login">Sign in</Link></p>
    </AuthLayout>
  );
}
