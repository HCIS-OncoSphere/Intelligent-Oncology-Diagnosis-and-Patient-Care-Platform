// Sign-in page. Shown at whatever URL was opened while signed out, so a shared link lands on its page afterwards.
import { useState } from "react";
import { Link } from "react-router-dom";
import { login } from "../api.js";
import { Alert, AuthField, AuthLayout, PasswordField, SubmitButton, requestProblem } from "./AuthLayout.jsx";
import { GoogleSignInButton } from "./GoogleSignIn.jsx";

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
      // a doctor waiting for approval (or rejected) gets the server's own explanation
      const known = /registration/i.test(err?.data?.detail || "") ? err.data.detail : "";
      setError(requestProblem(err) || known || "That username or email and password don't match an active account.");
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

      <GoogleSignInButton onDone={onDone} onError={setError} mode="signin" />
      <p className="auth-divider"><span>Or sign in with your password</span></p>

      <form className="auth-form" onSubmit={submit}>
        <Alert>{error}</Alert>
        <AuthField label="Username or email" icon="user" value={cred.username} onChange={set("username")}
                   autoComplete="username" autoCapitalize="none" spellCheck={false} autoFocus required />
        <PasswordField label="Password" value={cred.password} onChange={set("password")}
                       autoComplete="current-password" required />
        <div style={{ display: "flex", justifyContent: "flex-end", marginTop: "-6px" }}>
          <Link to="/forgot-password" style={{ fontSize: "0.85rem", color: "var(--primary)", textDecoration: "none" }}>
            Forgot password?
          </Link>
        </div>
        <SubmitButton busy={busy} busyText="Signing in…">Sign in</SubmitButton>
      </form>

      <div className="auth-divider"><span>New to OncoSphere?</span></div>
      <Link to="/register" className="auth-secondary">Create account</Link>
      <p className="auth-fine">Doctor registrations are reviewed by an administrator.</p>
    </AuthLayout>
  );
}
