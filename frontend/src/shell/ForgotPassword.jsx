// Forgot password page. Allows patients, doctors, and staff to request a password reset email.
import { useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api.js";
import { Alert, AuthField, AuthLayout, SubmitButton, requestProblem } from "./AuthLayout.jsx";

export default function ForgotPassword() {
  const [email, setEmail] = useState("");
  const [sent, setSent] = useState(false);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    if (!email.trim()) return;
    setBusy(true);
    setError("");
    try {
      await api("/auth/forgot-password/", {
        method: "POST",
        body: { email: email.trim().toLowerCase() },
      });
      setSent(true);
    } catch (err) {
      setError(
        requestProblem(err) ||
        err?.data?.email?.[0] ||
        err?.data?.detail ||
        "Could not send reset link. Please check the email and try again."
      );
    } finally {
      setBusy(false);
    }
  };

  return (
    <AuthLayout title="Forgot Password">
      <header className="auth-head">
        <h2>Reset your password</h2>
        <p>Enter the email address linked to your account, and we will send you a reset link.</p>
      </header>

      {sent ? (
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
            <strong>Check your inbox!</strong>
            <p style={{ margin: "8px 0 0" }}>
              If an account exists for <b>{email}</b>, we have sent instructions to reset your password.
              The link is valid for 2 hours.
            </p>
          </div>
          <div style={{ marginTop: "16px" }}>
            <Link to="/" className="auth-secondary" style={{ display: "block", textAlign: "center" }}>
              Return to sign in
            </Link>
          </div>
        </div>
      ) : (
        <form className="auth-form" onSubmit={submit}>
          <Alert>{error}</Alert>
          <AuthField
            label="Email address"
            icon="mail"
            type="email"
            value={email}
            onChange={(e) => { setEmail(e.target.value); setError(""); }}
            autoComplete="email"
            autoFocus
            required
            placeholder="e.g. name@example.com"
          />
          <SubmitButton busy={busy} busyText="Sending link…">
            Send reset link
          </SubmitButton>
          <div className="auth-divider"><span>Remember your password?</span></div>
          <Link to="/" className="auth-secondary" style={{ display: "block", textAlign: "center" }}>
            Back to sign in
          </Link>
        </form>
      )}
    </AuthLayout>
  );
}
