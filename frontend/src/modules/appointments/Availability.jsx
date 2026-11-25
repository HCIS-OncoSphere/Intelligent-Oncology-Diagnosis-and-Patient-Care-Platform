// Weekly working hours. Admins set any doctor's hours; each doctor sets only their own.
import { useState } from "react";
import { api } from "../../api.js";
import { Msg, Table, errorText, useList } from "../../shared/ui.jsx";
import { DAYS } from "./shared.jsx";

export function Availability({ me, doctors, reloadDoctors }) {
  const admin = me.role === "admin";
  const own = doctors.find((d) => d.is_me);
  const [picked, setDoctor] = useState(doctors[0]?.id || "");
  const doctor = admin ? picked || doctors[0]?.id || "" : own?.id || "";
  const [rows, load] = useList(doctor ? `/availability/?doctor=${doctor}` : "/availability/?doctor=0");
  const [f, setF] = useState({ day_of_week: "0", start_time: "09:00", end_time: "17:00" }), [msg, setMsg] = useState({});
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });
  const done = (text) => { setMsg({ ok: true, text }); load(); reloadDoctors(); };
  const add = () => api("/availability/", { method: "POST", body: { ...f, doctor } }).then(() => done("Window added.")).catch((e) => setMsg({ text: errorText(e) }));
  const del = (w) => api(`/availability/${w.id}/`, { method: "DELETE" }).then(() => done("Window removed.")).catch((e) => setMsg({ text: errorText(e) }));
  if (!admin && !own) {
    return <p className="hint">{doctors.length ? "Your account has no doctor profile, so there are no working hours to set. Ask an admin." : "Loading…"}</p>;
  }
  return (
    <>
      <fieldset>
        <legend>{admin ? "Add a working window" : "My working hours"}</legend>
        <div className="form-row">
          <label>Doctor<select value={doctor} disabled={!admin} onChange={(e) => setDoctor(e.target.value)}>{doctors.map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}</select></label>
          <label>Day<select value={f.day_of_week} onChange={set("day_of_week")}>{DAYS.map((d, i) => <option key={d} value={i}>{d}</option>)}</select></label>
          <label>From<input type="time" value={f.start_time} onChange={set("start_time")} /></label>
          <label>To<input type="time" value={f.end_time} onChange={set("end_time")} /></label>
          <button className="primary" onClick={add} disabled={!doctor}>Add window</button>
        </div>
        <Msg m={msg} />
      </fieldset>
      <Table head={["Day", "From", "To", ""]} empty="No windows yet: this doctor can be booked at any time."
        rows={rows.map((w) => <tr key={w.id}><td>{DAYS[w.day_of_week]}</td><td>{w.start_time.slice(0, 5)}</td><td>{w.end_time.slice(0, 5)}</td>
          <td><button className="danger" onClick={() => del(w)}>Remove</button></td></tr>)} />
    </>
  );
}
