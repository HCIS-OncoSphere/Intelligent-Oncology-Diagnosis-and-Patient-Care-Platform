// Sign-in page.
import { useState } from "react";
import { login } from "../api.js";
import { Field, Logo, Msg } from "../shared/ui.jsx";

export default function Login({ onDone }) {
  const [cred, setCred] = useState({ username: "", password: "" });
  const [msg, setMsg] = useState({}), [busy, setBusy] = useState(false);
  const set = (k) => (e) => setCred({ ...cred, [k]: e.target.value });

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    try { onDone(await login(cred.username, cred.password)); }
    catch { setMsg({ text: "Wrong username or password." }); }
    finally { setBusy(false); }
  };

  return (
    <div className="login-page">
      <form className="login-card stack" onSubmit={submit}>
        <div className="brand"><Logo /> OncoSphere</div>
        <p className="tagline">Intelligent oncology diagnosis and patient care</p>
        <h2>Sign in to your account</h2>
        <Field label="Username" value={cred.username} onChange={set("username")} autoComplete="username" required />
        <Field label="Password" type="password" value={cred.password} onChange={set("password")} autoComplete="current-password" required />
        <button className="primary" disabled={busy}>{busy ? "Please wait…" : "Sign in"}</button>
        <Msg m={msg} />
      </form>
    </div>
  );
}
