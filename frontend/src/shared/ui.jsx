// Shared UI helpers. Look and feel lives in src/styles.css. Change only through a pull request the team reviews.
import { useEffect, useState } from "react";
import { api } from "../api.js";

// Kept for older pages that still pass them as inline styles; the stylesheet now does the real work.
export const box = {};
export const tableStyle = {};

export function useList(path) {
  const [rows, setRows] = useState([]);
  const load = () => api(path).then(setRows).catch(() => setRows([]));
  useEffect(() => { load(); }, [path]);
  return [rows, load];
}

export const Table = ({ head, rows, empty = "Nothing here yet." }) => (
  <div className="table-wrap">
    <table>
      <thead><tr>{head.map((h, i) => <th key={h + i}>{h}</th>)}</tr></thead>
      <tbody>{rows.length ? rows : <tr><td colSpan={head.length} className="empty">{empty}</td></tr>}</tbody>
    </table>
  </div>
);

export const Field = ({ label, ...p }) => (
  <label>{label}<input {...p} /></label>
);

export const Logo = () => (
  <span className="brand-mark" aria-hidden="true">
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 5v14M5 12h14" />
    </svg>
  </span>
);

/** Coloured pill for any status word, e.g. scheduled, paid, failed. */
export const Badge = ({ s }) => <span className={`badge ${s}`}>{String(s).replace("_", "-")}</span>;

/** Green (ok) or red message line. Pass { ok, text }. Renders nothing when there is no text.
 *  A success message fades away after 5 seconds; every message has a close button. */
export function Msg({ m }) {
  const [hidden, setHidden] = useState(false);
  useEffect(() => {
    setHidden(false);
    if (m?.text && m.ok) { const t = setTimeout(() => setHidden(true), 5000); return () => clearTimeout(t); }
  }, [m]);
  if (!m || !m.text || hidden) return null;
  return (
    <div className={`msg ${m.ok ? "ok" : "err"}`} role="status">
      <span>{m.text}</span>
      <button type="button" className="msg-close" aria-label="Dismiss" onClick={() => setHidden(true)}>×</button>
    </div>
  );
}

export function Bars({ data }) {
  const max = Math.max(1, ...data.map((d) => d.value));
  return data.map((d) => (
    <div key={d.label} className="bar-row">
      <span className="bar-label" title={d.label}>{d.label}</span>
      <div className="bar-track"><div className="bar-fill" style={{ width: `${(d.value / max) * 100}%` }} /></div>
      <span className="bar-value">{d.value}</span>
    </div>
  ));
}

/** Turn any error thrown by api() into one readable line. */
export function errorText(e) {
  const d = e?.data ?? e;
  if (!d) return "Request failed.";
  if (typeof d === "string") return d;
  if (d instanceof Error) return d.message;
  if (Array.isArray(d)) return d.join(" ");
  return Object.entries(d)
    .map(([k, v]) => `${k === "detail" || k === "non_field_errors" ? "" : k + ": "}${[].concat(v).join(" ")}`)
    .join(" · ");
}
