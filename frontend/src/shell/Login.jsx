// Sign-in page. Shown at whatever URL was opened while signed out, so a shared link lands on its page afterwards.
import { useState } from "react";
import { Link } from "react-router-dom";
import { login } from "../api.js";
import { Alert, AuthField, AuthLayout, PasswordField, SubmitButton, requestProblem } from "./AuthLayout.jsx";

export default function Login({ onDone }) {
  const [cred, setCred] = useState({ username: "", password: "" });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const set = (k) => (e) => { setCred({ ...cred, [k]: e.target.value }); setError(""); };

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      onDone(await login(cred.username.trim(), cred.password));
    } catch (err) {
      setError(requestProblem(err) || "That username or email and password don't match an active account.");
      setCred((c) => ({ ...c, password: "" }));
    } finally {
      setBusy(false);
    }
  };

  return (
    <AuthLayout title="Sign in">
      <header className="auth-head">
        <h2>Welcome back</h2>
        <p>Sign in to continue to your OncoSphere workspace.</p>
      </header>

      <form className="auth-form" onSubmit={submit}>
        <Alert>{error}</Alert>
        <AuthField label="Username or email" icon="user" value={cred.username} onChange={set("username")}
                   autoComplete="username" autoCapitalize="none" spellCheck={false} autoFocus required />
        <PasswordField label="Password" value={cred.password} onChange={set("password")}
                       autoComplete="current-password" required />
        <p className="auth-note">Forgot your password? Ask your clinic's administrator to reset it.</p>
        <SubmitButton busy={busy} busyText="Signing in…">Sign in</SubmitButton>
      </form>

      <div className="auth-divider"><span>New to OncoSphere?</span></div>
      <Link to="/register" className="auth-secondary">Create a patient account</Link>
      <p className="auth-fine">Doctors, nurses and staff: your account is set up by an administrator.</p>
    </AuthLayout>
  );
}
