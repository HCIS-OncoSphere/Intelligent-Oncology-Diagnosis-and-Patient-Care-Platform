// "Continue with Google" button for patient sign-up / sign-in.
// Uses Google Identity Services: the user picks their Google account, we get an
// ID token (credential), post it to /api/auth/google/, and on success store the
// JWT tokens and hand the profile back via onDone (same shape as login()).
import { useEffect, useRef, useCallback } from "react";
import { googleLogin } from "../api.js";

const CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID || "";

/** Load the Google Identity Services script once, then run every queued callback. */
let readyCbs = [];
let loaded = false;
let loading = false;
function onGisReady(fn) {
  if (loaded) {
    fn();
    return;
  }
  readyCbs.push(fn);
  if (loading) return;
  loading = true;
  const s = document.createElement("script");
  s.src = "https://accounts.google.com/gsi/client";
  s.async = true;
  s.defer = true;
  s.onload = () => {
    loaded = true;
    const cbs = readyCbs;
    readyCbs = [];
    cbs.forEach((c) => c());
  };
  document.head.appendChild(s);
}

export function GoogleSignInButton({ onDone, onError, label = "Continue with Google" }) {
  const ref = useRef(null);

  const handleCredential = useCallback(async (credential) => {
    try {
      const me = await googleLogin(credential);
      if (onDone) onDone(me);
    } catch (ex) {
      const msg =
        ex?.data?.detail ||
        ex?.data?.credential ||
        "Google sign-in failed. Try again.";
      if (onError) onError(msg);
    }
  }, [onDone, onError]);

  useEffect(() => {
    if (!CLIENT_ID) return;
    onGisReady(() => {
      window.google.accounts.id.initialize({
        client_id: CLIENT_ID,
        // Google calls this with {credential, select_by, ...}; the ID token is the `credential` string inside it
        callback: (response) => handleCredential(response.credential),
      });
      window.google.accounts.id.renderButton(ref.current, {
        theme: "outline",
        size: "large",
        width: "100%",
        logo_alignment: "center",
        text: "continue_with",
      });
    });
  }, [handleCredential, CLIENT_ID]);

  if (!CLIENT_ID) {
    return (
      <button className="google-btn" disabled>
        Google sign-in not configured — set VITE_GOOGLE_CLIENT_ID
      </button>
    );
  }
  return <div className="google-btn-wrap" ref={ref} />;
}
