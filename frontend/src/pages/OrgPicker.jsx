import React from "react";
import { api, setToken } from "../api.js";

export default function OrgPicker({ orgs, onPick, onBack }) {
  async function pick(o) {
    const data = await api("/auth/select-org", {
      method: "POST",
      body: JSON.stringify({ org_id: o.org_id }),
    });
    setToken(data.token);
    onPick(o);
  }

  return (
    <div className="card">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
        <h2 className="card-title" style={{ margin: 0 }}>Select Organization Workspace</h2>
        {onBack && (
          <button type="button" className="secondary" style={{ padding: "6px 12px", fontSize: "0.82rem" }} onClick={onBack}>
            ← Back to Login
          </button>
        )}
      </div>
      <p className="card-subtitle">
        Your account belongs to multiple workspaces. Select the organization you are acting on behalf of.
      </p>

      <div style={{ display: "flex", flexDirection: "column", gap: "12px", marginTop: "16px" }}>
        {orgs.map((o) => (
          <div
            key={o.org_id}
            onClick={() => pick(o)}
            className="option-card"
            style={{ justifyContent: "space-between", padding: "16px 20px" }}
          >
            <div>
              <div style={{ fontWeight: "700", fontSize: "1.05rem", color: "var(--text-primary)" }}>
                {o.org_name}
              </div>
              <div style={{ fontSize: "0.82rem", color: "var(--text-muted)", marginTop: "2px" }}>
                Workspace ID: #{o.org_id}
              </div>
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
              <span
                style={{
                  fontSize: "0.75rem",
                  fontWeight: "700",
                  textTransform: "uppercase",
                  padding: "3px 10px",
                  borderRadius: "9999px",
                  background: o.role === "admin" ? "var(--primary-light)" : "var(--surface-elevated)",
                  color: o.role === "admin" ? "#a5b4fc" : "var(--text-secondary)",
                  border: "1px solid var(--border-subtle)",
                }}
              >
                {o.role}
              </span>
              <span style={{ color: "var(--primary)", fontWeight: "bold" }}>➔</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
