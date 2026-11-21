// "Are you sure?" popup. Native <dialog>: Esc or a click outside cancels, and focus stays inside while open.
import { useEffect, useRef } from "react";
import { Icon } from "./Icon.jsx";

export function ConfirmDialog({ icon = "logOut", tone = "danger", title, message, confirmLabel, onConfirm, onCancel }) {
  const ref = useRef(null);
  useEffect(() => {
    const d = ref.current;
    d.showModal();
    d.querySelector("[data-cancel]")?.focus(); // the safe choice has focus, so Enter doesn't confirm by accident
    return () => d.open && d.close();
  }, []);
  return (
    <dialog ref={ref} className="confirm" aria-labelledby="confirm-title" aria-describedby="confirm-text"
            onClose={onCancel} onClick={(e) => e.target === ref.current && onCancel()}>
      <span className={`confirm-icon ${tone}`}><Icon name={icon} /></span>
      <h2 id="confirm-title">{title}</h2>
      {message && <p id="confirm-text">{message}</p>}
      <div className="confirm-actions">
        <button type="button" data-cancel onClick={onCancel}>Cancel</button>
        <button type="button" className={tone === "danger" ? "confirm-danger" : "primary"} onClick={onConfirm}>{confirmLabel}</button>
      </div>
    </dialog>
  );
}
