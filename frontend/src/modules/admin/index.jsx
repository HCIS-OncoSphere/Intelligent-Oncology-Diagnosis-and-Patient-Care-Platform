// Administration module (owner: Aya). Feature F8 (Settings, Audit Log).
import { useState } from "react";
import { api } from "../../api.js";
import { Badge, Msg, Table, errorText, useList } from "../../shared/ui.jsx";
import { useQueryState } from "../../shared/url.js";

const RefreshIcon = () => (
  <svg
    className="icon"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
    aria-hidden="true"
    style={{ width: 16, height: 16 }}
  >
    <path d="M20 11a8 8 0 0 0-14.9-3M4 4v4h4M4 13a8 8 0 0 0 14.9 3M20 20v-4h-4" />
  </svg>
);

function SettingsTab() {
  const [settings, reloadSettings] = useList("/settings/");
  const [editingId, setEditingId] = useState(null);
  const [form, setForm] = useState({ key: "", value: "", description: "" });
  const [msg, setMsg] = useState({});
  const [busy, setBusy] = useState(false);

  const setField = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  const resetForm = () => {
    setEditingId(null);
    setForm({ key: "", value: "", description: "" });
  };

  const startEdit = (s) => {
    setEditingId(s.id);
    setForm({ key: s.key, value: s.value, description: s.description || "" });
    setMsg({});
  };

  const saveSetting = async (e) => {
    e.preventDefault();
    if (!form.key.trim()) {
      setMsg({ text: "Setting key is required." });
      return;
    }
    setBusy(true);
    setMsg({});
    try {
      if (editingId) {
        await api(`/settings/${editingId}/`, {
          method: "PATCH",
          body: { key: form.key, value: form.value, description: form.description },
        });
        setMsg({ ok: true, text: `Setting "${form.key}" updated.` });
      } else {
        await api("/settings/", {
          method: "POST",
          body: { key: form.key, value: form.value, description: form.description },
        });
        setMsg({ ok: true, text: `Setting "${form.key}" added.` });
      }
      resetForm();
      reloadSettings();
    } catch (err) {
      setMsg({ text: errorText(err) });
    } finally {
      setBusy(false);
    }
  };

  const deleteSetting = async (s) => {
    if (!window.confirm(`Are you sure you want to delete setting "${s.key}"?`)) return;
    setMsg({});
    try {
      await api(`/settings/${s.id}/`, { method: "DELETE" });
      setMsg({ ok: true, text: `Setting "${s.key}" removed.` });
      if (editingId === s.id) resetForm();
      reloadSettings();
    } catch (err) {
      setMsg({ text: errorText(err) });
    }
  };

  return (
    <>
      <fieldset>
        <legend>{editingId ? "Edit System Setting" : "Add System Setting"}</legend>
        <form onSubmit={saveSetting}>
          <div className="form-row">
            <label>
              Key
              <input
                type="text"
                placeholder="e.g. clinic_name"
                value={form.key}
                onChange={setField("key")}
                required
              />
            </label>
            <label>
              Value
              <input
                type="text"
                placeholder="e.g. OncoSphere Cairo"
                value={form.value}
                onChange={setField("value")}
              />
            </label>
            <label style={{ flex: 1 }}>
              Description
              <input
                type="text"
                placeholder="Brief explanation of this setting"
                value={form.description}
                onChange={setField("description")}
              />
            </label>
            <button type="submit" className="primary" disabled={busy}>
              {editingId ? "Update Setting" : "Save Setting"}
            </button>
            {editingId && (
              <button type="button" className="ghost sm" onClick={resetForm}>
                Cancel
              </button>
            )}
          </div>
        </form>
        <Msg m={msg} />
      </fieldset>

      <Table
        head={["Key", "Value", "Description", "Last Updated", "Actions"]}
        empty="No system settings configured yet."
        rows={settings.map((s) => (
          <tr key={s.id}>
            <td>
              <code>{s.key}</code>
            </td>
            <td>
              <strong>{s.value || "—"}</strong>
            </td>
            <td>{s.description || <span className="muted">—</span>}</td>
            <td>{new Date(s.updated_at).toLocaleString()}</td>
            <td>
              <button className="sm" onClick={() => startEdit(s)}>
                Edit
              </button>
              <button className="sm danger" onClick={() => deleteSetting(s)}>
                Delete
              </button>
            </td>
          </tr>
        ))}
      />
    </>
  );
}

function AuditTab() {
  const [logs, reloadLogs] = useList("/audit/");
  const [method, setMethod] = useState("");
  const [query, setQuery] = useState("");
  const [busy, setBusy] = useState(false);

  const refresh = async () => {
    setBusy(true);
    try {
      await reloadLogs();
    } finally {
      setBusy(false);
    }
  };

  const filtered = logs.filter((item) => {
    if (method && item.action !== method) return false;
    if (query) {
      const q = query.toLowerCase();
      const matchPath = item.path?.toLowerCase().includes(q);
      const matchUser = item.user?.toLowerCase().includes(q);
      const matchStatus = String(item.status_code).includes(q);
      if (!matchPath && !matchUser && !matchStatus) return false;
    }
    return true;
  });

  const getStatusBadgeClass = (status) => {
    if (status >= 200 && status < 300) return "scheduled";
    if (status >= 300 && status < 400) return "info";
    return "cancelled";
  };

  return (
    <>
      <div className="form-row">
        <label>
          Filter by Method
          <select value={method} onChange={(e) => setMethod(e.target.value)}>
            <option value="">All Methods</option>
            <option value="POST">POST (Create)</option>
            <option value="PUT">PUT (Replace)</option>
            <option value="PATCH">PATCH (Update)</option>
            <option value="DELETE">DELETE (Remove)</option>
          </select>
        </label>
        <label style={{ flex: 1 }}>
          Search Path / User
          <input
            type="search"
            placeholder="Filter by user or endpoint path..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
        </label>
        <button
          className={`icon-btn${busy ? " spinning" : ""}`}
          onClick={refresh}
          disabled={busy}
          title="Refresh audit logs"
          aria-label="Refresh"
        >
          <RefreshIcon />
        </button>
      </div>

      <p className="hint">
        Showing {filtered.length} of {logs.length} logged API write events.
      </p>

      <Table
        head={["Timestamp", "User", "Action", "Path / Endpoint", "Status", "IP Address"]}
        empty="No audit log entries recorded yet."
        rows={filtered.map((a) => (
          <tr key={a.id}>
            <td>{new Date(a.created_at).toLocaleString()}</td>
            <td>
              <b>{a.user || "Anonymous"}</b>
            </td>
            <td>
              <Badge s={a.action.toLowerCase()} />
            </td>
            <td>
              <code>{a.path}</code>
            </td>
            <td>
              <span className={`badge ${getStatusBadgeClass(a.status_code)}`}>
                {a.status_code}
              </span>
            </td>
            <td>{a.ip_address || "—"}</td>
          </tr>
        ))}
      />
    </>
  );
}

function Admin() {
  const [tab, setTab] = useQueryState("tab", "settings");

  return (
    <>
      <div className="segmented">
        <button
          className={tab === "settings" ? "active" : ""}
          onClick={() => setTab("settings")}
        >
          System Settings
        </button>
        <button
          className={tab === "audit" ? "active" : ""}
          onClick={() => setTab("audit")}
        >
          Audit Log
        </button>
      </div>

      {tab === "audit" ? <AuditTab /> : <SettingsTab />}
    </>
  );
}

export default {
  id: "admin",
  label: "Administration",
  order: 91,
  roles: ["admin"],
  Component: Admin,
};
