// Reset password page. User lands here from the email link with ?token=...
import { useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { api } from "../api.js";
import { Alert, AuthLayout, PasswordField, SubmitButton, requestProblem } from "./AuthLayout.jsx";

export default function ResetPassword() {
  const [searchParams] = useSearchParams();
  const rawToken = searchParams.get("token") || "";
  let token = rawToken.trim().replace(/^['"]|['"]$/g, "").replace(/[.,;]+$/, "");
  // Clean Quoted-Printable artifacts if copied from console (e.g. leading 3D and internal =)
  if (/^3d/i.test(token) && token.length > 64) {
    token = token.slice(2);
  }
  token = token.replace(/=/g, "");

  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [done, setDone] = useState(false);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    if (!token) {
      setError("Reset token is missing. Please use the link sent to your email.");
      return;
    }
    if (password !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }
    setBusy(true);
    setError("");
    try {
      await api("/auth/reset-password/", {
        method: "POST",
        body: { token, new_password: password },
      });
      setDone(true);
    } catch (err) {
      const fieldErr = err?.data?.new_password?.[0] || err?.data?.token?.[0];
      setError(requestProblem(err) || fieldErr || err?.data?.detail || "Failed to reset password.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <AuthLayout title="Reset Password">
      <header className="auth-head">
        <h2>Choose a new password</h2>
        <p>Your new password must be secure and different from previous passwords.</p>
      </header>

      {!token ? (
        <div className="auth-form">
          <Alert>No reset token provided. Please click the link received in your email, or request a new one.</Alert>
          <div style={{ marginTop: "16px" }}>
            <Link to="/forgot-password" className="auth-secondary" style={{ display: "block", textAlign: "center" }}>
              Request new reset link
            </Link>
          </div>
        </div>
      ) : done ? (
        <div className="auth-form">
          <div style={{
            background: "var(--success-soft, #e6f7ed)",
            border: "1px solid var(--success, #16a34a)",
            borderRadius: "10px",
            padding: "16px",
            color: "var(--success-dark, #166534)",
            fontSize: "0.95rem",
            lineHeight: 1.5,
          }}>
            <strong>Password reset successful!</strong>
            <p style={{ margin: "8px 0 0" }}>
              Your password has been updated. You can now sign in using your new password.
            </p>
          </div>
          <div style={{ marginTop: "16px" }}>
            <Link to="/" className="primary auth-submit" style={{ display: "block", textAlign: "center", textDecoration: "none" }}>
              Sign in now
            </Link>
          </div>
        </div>
      ) : (
        <form className="auth-form" onSubmit={submit}>
          <Alert>{error}</Alert>
          <PasswordField
            label="New password"
            value={password}
            onChange={(e) => { setPassword(e.target.value); setError(""); }}
            autoComplete="new-password"
            autoFocus
            required
            hint="At least 8 characters, numbers & letters recommended."
          />
          <PasswordField
            label="Confirm new password"
            value={confirmPassword}
            onChange={(e) => { setConfirmPassword(e.target.value); setError(""); }}
            autoComplete="new-password"
            required
          />
          <SubmitButton busy={busy} busyText="Updating password…">
            Reset password
          </SubmitButton>
          <div className="auth-divider"><span>Changed your mind?</span></div>
          <Link to="/" className="auth-secondary" style={{ display: "block", textAlign: "center" }}>
            Back to sign in
          </Link>
        </form>
      )}
    </AuthLayout>
  );
}
