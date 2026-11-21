// Owner: Sarah. Backend: integration/ (+ hl7_service/)
import { api } from "../../api.js";
import { Table, useList } from "../../shared/ui.jsx";

function Hl7Log() {
  const [rows, load] = useList("/hl7/messages/");
  return (
    <>
      <button onClick={load}>Refresh</button>
      <Table head={["Time", "Type", "Status", "ACK"]} rows={rows.map((m) => (
        <tr key={m.id}><td>{new Date(m.created_at).toLocaleString()}</td><td>{m.message_type}^{m.trigger_event}</td><td>{m.status}</td>
          <td>{(m.acks || []).map((a) => a.ack_code + (a.error_text ? ` (${a.error_text})` : "")).join(", ")}
            {["queued", "failed"].includes(m.status) && <button onClick={() => api(`/hl7/messages/${m.id}/resend/`, { method: "POST" }).then(load).catch((e) => alert(e?.message || e?.detail || "Cannot resend message"))}>Resend</button>}</td></tr>))} />
    </>
  );
}

export default { id: "hl7", label: "HL7 log", order: 70, roles: ["clinical", "admin"], Component: Hl7Log };