// The notification bell in the header: unread count, and a small list that opens on click.
import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api.js";

const when = new Intl.DateTimeFormat(undefined, { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });

export function Bell() {
  const [data, setData] = useState({ unread: 0, results: [] });
  const [open, setOpen] = useState(false);
  const box = useRef(null);
  const go = useNavigate();

  const load = () => api("/notifications/").then(setData).catch(() => {});
  useEffect(() => {
    load();
    const t = setInterval(load, 60000);
    return () => clearInterval(t);
  }, []);
  useEffect(() => {
    if (!open) return;
    const close = (e) => { if (!box.current?.contains(e.target)) setOpen(false); };
    document.addEventListener("mousedown", close);
    return () => document.removeEventListener("mousedown", close);
  }, [open]);

  const toggle = () => {
    const next = !open;
    setOpen(next);
    if (next && data.unread) api("/notifications/", { method: "POST", body: {} }).then(load).catch(() => {});
  };

  return (
    <div className="bell" ref={box}>
      <button type="button" className="icon-btn" onClick={toggle} aria-label={`Notifications${data.unread ? `, ${data.unread} unread` : ""}`}
              aria-expanded={open}>
        <svg className="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"
             strokeLinejoin="round" aria-hidden="true" style={{ width: 18, height: 18 }}>
          <path d="M18 8a6 6 0 0 0-12 0c0 7-3 9-3 9h18s-3-2-3-9M13.7 21a2 2 0 0 1-3.4 0" />
        </svg>
        {data.unread > 0 && <span className="bell-count">{data.unread > 9 ? "9+" : data.unread}</span>}
      </button>
      {open && (
        <div className="bell-panel card" role="dialog" aria-label="Notifications">
          {data.results.length === 0 && <p className="hint" style={{ margin: 0 }}>No notifications.</p>}
          {data.results.map((n) => (
            <button key={n.id} type="button" className={`bell-item${n.is_read ? "" : " new"}`}
                    onClick={() => { setOpen(false); if (n.link) go(n.link); }}>
              <b>{n.title}</b>
              {n.message && <span>{n.message}</span>}
              <small>{when.format(new Date(n.created_at))}</small>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
