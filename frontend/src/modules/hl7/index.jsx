// Owner: Sarah. Backend: integration/ (+ hl7_service/)
import { useState } from "react";
import { api } from "../../api.js";
import { Table, useList } from "../../shared/ui.jsx";

function Hl7Log() {
  const [rows, load] = useList("/hl7/messages/");
  const [statusFilter, setStatusFilter] = useState("all");
  const [selected, setSelected] = useState(null);
  const [msg, setMsg] = useState({ text: "", isError: false });

  const refresh = () => {
    setMsg({ text: "", isError: false });
    load();
  };

  const resend = (e, id) => {
    e.stopPropagation(); // prevent opening/closing row details when clicking Resend
    setMsg({ text: "", isError: false });
    api(`/hl7/messages/${id}/resend/`, { method: "POST" })
      .then((updated) => {
        setMsg({
          text: `Message resent (status: ${updated?.status || "sent"}).`,
          isError: false,
        });
        if (selected?.id === id && updated) setSelected(updated);
        load();
      })
      .catch((err) => {
        setMsg({
          text: err?.message || err?.detail || "Cannot resend message",
          isError: true,
        });
      });
  };

  const filtered =
    statusFilter === "all" ? rows : rows.filter((m) => m.status === statusFilter);

  return (
    <>
      <div
        style={{
          display: "flex",
          flexWrap: "wrap",
          alignItems: "center",
          gap: 12,
          marginBottom: 12,
        }}
      >
        <button onClick={refresh}>Refresh</button>

        <label style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>
          <span>Status:</span>
          <select
            value={statusFilter}
            onChange={(e) => {
              setStatusFilter(e.target.value);
              setMsg({ text: "", isError: false });
            }}
          >
            <option value="all">All ({rows.length})</option>
            <option value="acked">Sent (acked)</option>
            <option value="failed">Failed</option>
            <option value="queued">Queued</option>
            <option value="nacked">Nacked</option>
          </select>
        </label>

        {msg.text && (
          <span
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: 8,
              color: msg.isError ? "#dc2626" : "#15803d",
              background: msg.isError ? "#fef2f2" : "#f0fdf4",
              border: `1px solid ${msg.isError ? "#fecaca" : "#bbf7d0"}`,
              padding: "4px 10px",
              borderRadius: 6,
              fontSize: 13,
            }}
          >
            <span>{msg.text}</span>
            <button
              type="button"
              onClick={() => setMsg({ text: "", isError: false })}
              style={{
                border: "none",
                background: "transparent",
                cursor: "pointer",
                fontWeight: "bold",
                padding: 0,
                color: "inherit",
              }}
              title="Dismiss message"
            >
              ×
            </button>
          </span>
        )}
      </div>

      <Table
        head={["Time", "Type", "Status", "ACK"]}
        rows={filtered.map((m) => {
          const isSelected = selected?.id === m.id;
          return (
            <tr
              key={m.id}
              onClick={() => setSelected(isSelected ? null : m)}
              title="Click row to inspect Raw HL7 message"
              style={{
                cursor: "pointer",
                backgroundColor: isSelected ? "rgba(99, 102, 241, 0.08)" : undefined,
              }}
            >
              <td>{new Date(m.created_at).toLocaleString()}</td>
              <td>
                {m.message_type}^{m.trigger_event}
              </td>
              <td>{m.status}</td>
              <td>
                {(m.acks || [])
                  .map((a) => a.ack_code + (a.error_text ? ` (${a.error_text})` : ""))
                  .join(", ")}{" "}
                {["queued", "failed"].includes(m.status) && (
                  <button onClick={(e) => resend(e, m.id)}>Resend</button>
                )}
              </td>
            </tr>
          );
        })}
        empty="No HL7 messages match this filter."
      />

      {selected && (
        <div
          style={{
            marginTop: 16,
            padding: 14,
            borderRadius: 8,
            border: "1px solid #cbd5e1",
            background: "#f8fafc",
            color: "#0f172a",
          }}
        >
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              marginBottom: 8,
            }}
          >
            <div>
              <strong>
                Raw HL7 — {selected.message_type}^{selected.trigger_event}
              </strong>{" "}
              <small style={{ color: "#475569" }}>
                (Control ID: {selected.control_id} · Status: {selected.status})
              </small>
            </div>
            <button onClick={() => setSelected(null)}>Close</button>
          </div>

          {(selected.acks || []).some((a) => a.error_text) && (
            <p style={{ color: "#dc2626", margin: "0 0 8px", fontSize: 13 }}>
              <strong>ACK Error:</strong>{" "}
              {selected.acks
                .filter((a) => a.error_text)
                .map((a) => `${a.ack_code}: ${a.error_text}`)
                .join(" | ")}
            </p>
          )}

          <pre
            style={{
              margin: 0,
              padding: 10,
              borderRadius: 6,
              background: "#ffffff",
              border: "1px solid #e2e8f0",
              whiteSpace: "pre-wrap",
              wordBreak: "break-all",
              fontFamily: "monospace",
              fontSize: 13,
              lineHeight: 1.5,
            }}
          >
            {(selected.raw_text || selected.raw_message || "(No raw HL7 text recorded)").replace(
              /\r/g,
              "\n"
            )}
          </pre>
        </div>
      )}
    </>
  );
}

export default { id: "hl7", label: "HL7 log", order: 70, roles: ["clinical", "admin"], Component: Hl7Log };