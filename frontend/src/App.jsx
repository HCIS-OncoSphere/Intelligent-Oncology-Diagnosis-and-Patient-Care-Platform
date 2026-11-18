import { useState } from "react";

const box = { maxWidth: 900, margin: "2rem auto", fontFamily: "system-ui, sans-serif", padding: "0 1.5rem" };
const card = { border: "1px solid #e2e8f0", borderRadius: "8px", padding: "1.25rem", marginBottom: "1rem", background: "#f8fafc" };
const badge = { display: "inline-block", padding: "2px 8px", borderRadius: "4px", fontSize: "12px", background: "#e2e8f0", fontWeight: "bold" };

export default function App() {
  const modules = [
    { member: "Member 1", name: "Authentication & RBAC", branch: "feature/auth-rbac", desc: "User model, JWT tokens, login & role permissions" },
    { member: "Member 2", name: "Patients Management", branch: "feature/patient-management", desc: "MRN generation, demographics & patient profiles" },
    { member: "Member 3", name: "Appointments Scheduling", branch: "feature/appointments-scheduling", desc: "Doctor availability, double-booking check & cancellations" },
    { member: "Member 4", name: "Medical Records & ICD-10", branch: "feature/medical-records", desc: "Encounters, ICD-10 diagnosis, prescriptions & treatment plans" },
    { member: "Member 5", name: "Billing & Invoices", branch: "feature/billing-system", desc: "Service catalog, invoices & payment processing" },
    { member: "Member 6", name: "Analytics & HL7 Service", branch: "feature/reports-hl7", desc: "Aggregated reports, audit logs & HL7 MLLP messaging" },
  ];

  return (
    <div style={box}>
      <header style={{ borderBottom: "2px solid #2b6cb0", paddingBottom: "1rem", marginBottom: "1.5rem" }}>
        <h1 style={{ color: "#2b6cb0", margin: "0 0 0.5rem 0" }}>OncoSphere Platform</h1>
        <p style={{ margin: 0, color: "#4a5568" }}>
          Intelligent Oncology Diagnosis and Patient Care Platform — Team Base Scaffold
        </p>
      </header>

      <section style={{ marginBottom: "2rem" }}>
        <h3>🚀 Project Setup Status: Ready</h3>
        <p style={{ color: "#718096" }}>
          The base repository scaffold has been initialized. Team members can branch out, implement their assigned modules, and submit PRs to merge into <code>main</code>.
        </p>
      </section>

      <section>
        <h3>📋 Team Module Assignments</h3>
        {modules.map((m) => (
          <div key={m.member} style={card}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.5rem" }}>
              <strong>{m.name}</strong>
              <span style={badge}>{m.member}</span>
            </div>
            <p style={{ margin: "0 0 0.5rem 0", color: "#4a5568", fontSize: "14px" }}>{m.desc}</p>
            <code style={{ fontSize: "12px", color: "#2b6cb0" }}>git checkout -b {m.branch}</code>
          </div>
        ))}
      </section>
    </div>
  );
}
