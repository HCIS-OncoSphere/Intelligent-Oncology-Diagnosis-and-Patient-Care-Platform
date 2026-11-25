// Shown instead of the app when an administrator created the account with a temporary password.
import { useState } from "react";
import { api, changePassword, logout } from "../api.js";
import { Alert, AuthField, AuthLayout, PasswordField, SubmitButton } from "./AuthLayout.jsx";
import { errorText } from "../shared/ui.jsx";

export default function ForcePassword({ onDone, onSignOut }) {
  const [f, setF] = useState({ current: "", next: "", again: "" });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const set = (k) => (e) => { setF({ ...f, [k]: e.target.value }); setError(""); };

  const submit = async (e) => {
    e.preventDefault();
    if (f.next.length < 8 || /^\d+$/.test(f.next)) return setError("Use at least 8 characters, not only numbers.");
    if (f.next !== f.again) return setError("The new passwords don't match.");
    setBusy(true);
    try {
      await changePassword(f.current, f.next);
      onDone(await api("/auth/me/"));
    } catch (ex) {
      setError(errorText(ex));
      setBusy(false);
    }
  };

  return (
    <AuthLayout title="Choose a new password">
      <header className="auth-head">
        <h2>Choose your own password</h2>
        <p>Your account was set up with a temporary password. Pick a new one to continue.</p>
      </header>
      <form className="auth-form" onSubmit={submit}>
        <Alert>{error}</Alert>
        <PasswordField label="Temporary password" value={f.current} onChange={set("current")}
                       autoComplete="current-password" required autoFocus />
        <PasswordField label="New password" value={f.next} onChange={set("next")} autoComplete="new-password" required />
        <PasswordField label="New password again" value={f.again} onChange={set("again")} autoComplete="new-password" required />
        <SubmitButton busy={busy} busyText="Saving…">Save and continue</SubmitButton>
      </form>
      <p className="auth-fine"><button type="button" className="sm" onClick={() => { logout(); onSignOut(); }}>Sign out</button></p>
    </AuthLayout>
  );
}
