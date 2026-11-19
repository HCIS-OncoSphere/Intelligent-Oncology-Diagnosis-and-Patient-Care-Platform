// Sign in + patient self-registration.
import { useState } from "react";
import { api, login } from "../api.js";
import { Field, Logo, Msg, errorText } from "../shared/ui.jsx";

export default function Login({ onDone }) {
  const [mode, setMode] = useState("login");
  const [f, setF] = useState({ username: "", password: "", email: "", first_name: "", last_name: "", date_of_birth: "", gender: "F" });
  const [msg, setMsg] = useState({}), [busy, setBusy] = useState(false);
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });
  const signup = mode === "register";

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      if (!signup) return onDone(await login(f.username, f.password));
      await api("/auth/register/", { method: "POST", body: f });
      setMsg({ ok: true, text: "Account created. You can sign in now." });
      setMode("login");
    } catch (x) {
      setMsg({ text: signup ? errorText(x) : "Wrong username or password." });
    } finally { setBusy(false); }
  };

  return (
    <div className="login-page">
      <form className="login-card stack" onSubmit={submit}>
        <div className="brand"><Logo /> OncoSphere</div>
        <p className="tagline">Intelligent oncology diagnosis and patient care</p>
        <h2 style={{ fontSize: "1.1rem" }}>{signup ? "Create a patient account" : "Sign in to your account"}</h2>

        <Field label="Username" value={f.username} onChange={set("username")} autoComplete="username" required />
        <Field label="Password" type="password" value={f.password} onChange={set("password")} autoComplete={signup ? "new-password" : "current-password"} required />
        {signup && (
          <>
            <div className="grid-2">
              <Field label="First name" value={f.first_name} onChange={set("first_name")} required />
              <Field label="Last name" value={f.last_name} onChange={set("last_name")} required />
            </div>
            <Field label="Email" type="email" value={f.email} onChange={set("email")} required />
            <div className="grid-2">
              <Field label="Date of birth" type="date" value={f.date_of_birth} onChange={set("date_of_birth")} required />
              <label>Gender
                <select value={f.gender} onChange={set("gender")}><option value="F">Female</option><option value="M">Male</option><option value="O">Other</option></select>
              </label>
            </div>
          </>
        )}
        <button className="primary" disabled={busy}>{busy ? "Please wait…" : signup ? "Create account" : "Sign in"}</button>
        <Msg m={msg} />
        <div className="login-switch">
          {signup ? "Already registered?" : "New patient?"}{" "}
          <button type="button" onClick={() => { setMode(signup ? "login" : "register"); setMsg({}); }}>{signup ? "Sign in" : "Create an account"}</button>
        </div>
      </form>
    </div>
  );
}
