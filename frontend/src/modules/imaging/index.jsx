// Owner: Aliaa (Phase 3). Backend: imaging/
// TODO: replace the placeholder card with the Cornerstone3D / VTK.js viewer (zoom, pan, rotate, windowing, MPR, 3D, filters).
import { useState } from "react";
import { api } from "../../api.js";
import { Field, Msg, Table, errorText, useList } from "../../shared/ui.jsx";

const MODALITIES = [["CT", "CT"], ["MR", "MRI"], ["PT", "PET"], ["CR", "X-ray"], ["US", "Ultrasound"], ["OT", "Other"]];
const EMPTY = { patient: "", orthanc_study_uid: "", modality: "CT", body_part: "", study_date: "" };

/** Staff only: register a study that is already stored in Orthanc. */
function RegisterStudy({ onCreated }) {
  const [f, setF] = useState(EMPTY);
  const [msg, setMsg] = useState(null);
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });

  const create = async (e) => {
    e.preventDefault();
    try {
      await api("/imaging/studies/", { method: "POST", body: f });
      setMsg({ ok: true, text: "Study registered." });
      setF(EMPTY);
      onCreated();
    } catch (x) { setMsg({ ok: false, text: errorText(x) }); }
  };

  return (
    <form className="card" onSubmit={create}>
      <h3>Register study</h3>
      <Field label="Patient id" value={f.patient} onChange={set("patient")} size="4" required />
      <Field label="Orthanc study UID" value={f.orthanc_study_uid} onChange={set("orthanc_study_uid")} required />
      <label>Modality
        <select value={f.modality} onChange={set("modality")}>
          {MODALITIES.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
        </select>
      </label>
      <Field label="Body part" value={f.body_part} onChange={set("body_part")} />
      <Field label="Study date" type="date" value={f.study_date} onChange={set("study_date")} required />
      <button className="primary">Register</button>
      <Msg m={msg} />
    </form>
  );
}

function Imaging({ me }) {
  const [rows, load] = useList("/imaging/studies/");
  const [cfg, setCfg] = useState(null);
  const [msg, setMsg] = useState(null);

  const open = (s) => api(`/imaging/studies/${s.id}/viewer-config/`).then(setCfg).catch((x) => setMsg({ ok: false, text: errorText(x) }));

  return (
    <>
      {me.role !== "patient" && <RegisterStudy onCreated={load} />}
      <Msg m={msg} />
      <Table
        head={["Date", "Modality", "Body part", "Series", ""]}
        empty="No studies yet."
        rows={rows.map((s) => (
          <tr key={s.id}>
            <td>{s.study_date}</td><td>{s.modality}</td><td>{s.body_part}</td><td>{s.series.length}</td>
            <td><button onClick={() => open(s)}>Open</button></td>
          </tr>
        ))}
      />
      <div className="card">
        <h3>DICOM viewer</h3>
        {cfg
          ? <>{me.role === "patient" && <p className="hint">Read-only mode.</p>}<pre>{JSON.stringify(cfg, null, 2)}</pre></>
          : <p className="hint">The viewer will go here (Phase 3). Pick a study and press Open.</p>}
      </div>
    </>
  );
}

export default { id: "imaging", label: "Imaging", order: 50, roles: ["patient", "clinical", "admin"], Component: Imaging };
