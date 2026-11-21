// Sun/moon button that switches light and dark. The choice is remembered in this browser; until someone
// picks, the page follows the device setting (index.html sets the starting theme).
import { useEffect, useState } from "react";
import { Icon } from "./Icon.jsx";

const root = document.documentElement;
const current = () => (root.getAttribute("data-theme") === "dark" ? "dark" : "light");

function saved() {
  try { return localStorage.getItem("theme"); } catch { return null; }
}

export function ThemeToggle({ className = "" }) {
  const [theme, setTheme] = useState(current);

  // several toggles can be on screen; keep them in step, and follow the device until a choice is saved
  useEffect(() => {
    const sync = () => setTheme(current());
    const media = window.matchMedia("(prefers-color-scheme: dark)");
    const onDevice = (e) => {
      if (saved() === "light" || saved() === "dark") return;
      root.setAttribute("data-theme", e.matches ? "dark" : "light");
      window.dispatchEvent(new Event("oncosphere:theme"));
    };
    window.addEventListener("oncosphere:theme", sync);
    media.addEventListener("change", onDevice);
    return () => { window.removeEventListener("oncosphere:theme", sync); media.removeEventListener("change", onDevice); };
  }, []);

  const toggle = () => {
    const next = theme === "dark" ? "light" : "dark";
    root.setAttribute("data-theme", next);
    try { localStorage.setItem("theme", next); } catch { /* private mode: still switches for this visit */ }
    window.dispatchEvent(new Event("oncosphere:theme"));
  };

  const dark = theme === "dark";
  return (
    <button type="button" className={`theme-toggle ${className}`} onClick={toggle}
            aria-label={dark ? "Switch to light mode" : "Switch to dark mode"}
            title={dark ? "Light mode" : "Dark mode"}>
      <span className={`theme-icon ${dark ? "" : "on"}`}><Icon name="sun" /></span>
      <span className={`theme-icon ${dark ? "on" : ""}`}><Icon name="moon" /></span>
    </button>
  );
}
