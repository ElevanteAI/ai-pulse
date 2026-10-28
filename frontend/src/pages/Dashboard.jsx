import React, { useEffect, useState } from "react";
import { api } from "../api.js";

export default function Dashboard({ org, onBack }) {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api("/dashboard")
      .then(setData)
      .catch((err) => setError(err.message));
  }, []);

  function getBadgeClass(level) {
    switch (level?.toLowerCase()) {
      case "leader":
        return "badge-leader";
      case "practitioner":
        return "badge-practitioner";
      case "exploring":
        return "badge-exploring";
      default:
        return "badge-beginner";
    }
  }

  if (error) {
    return (
      <div className="card">
        <div className="error-banner">{error}</div>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="card" style={{ textAlign: "center", padding: "48px" }}>
        <p style={{ color: "var(--text-secondary)" }}>Loading enterprise dashboard…</p>
      </div>
    );
  }

  const totalCompleted = data.departments.reduce((acc, d) => acc + d.completed, 0);

  return (
    <div className="card">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "12px", marginBottom: "18px" }}>
        <div>
          <h2 className="card-title" style={{ margin: "0 0 4px" }}>
            {data.organization} • Leadership Dashboard
          </h2>
          <p style={{ color: "var(--text-muted)", fontSize: "0.88rem", margin: 0 }}>
            Enterprise AI adoption, maturity tiers, and aggregate risk trends.
          </p>
        </div>
        <span className="org-pill">
          <span>🛡️</span> Admin View
        </span>
      </div>

      {/* Privacy Notice Banner */}
      <div className="privacy-banner">
        <span style={{ fontSize: "1.2rem" }}>🔒</span>
        <div>
          <strong>K-Anonymity Privacy Guardrail Active</strong>
          <div style={{ fontSize: "0.82rem", opacity: 0.9, marginTop: "2px" }}>
            To protect individual employee privacy, departments with fewer than {data.minimum_group_size} completed diagnostics are suppressed. They are grouped under "Other teams" only when combined threshold reaches {data.minimum_group_size}.
          </div>
        </div>
      </div>

      {/* Summary Metrics */}
      <div className="metrics-grid">
        <div className="metric-card">
          <p className="metric-label">Reporting Teams</p>
          <p className="metric-value">{data.departments.length}</p>
        </div>
        <div className="metric-card">
          <p className="metric-label">Privacy-Safe Diagnostics</p>
          <p className="metric-value">{totalCompleted}</p>
        </div>
        <div className="metric-card">
          <p className="metric-label">High-Priority Risks</p>
          <p className="metric-value" style={{ color: data.top_risks.length ? "var(--rose)" : "var(--emerald)" }}>
            {data.top_risks.length}
          </p>
        </div>
      </div>

      {/* Department Breakdown */}
      <div style={{ marginTop: "28px" }}>
        <h3 style={{ fontSize: "1.1rem", margin: "0 0 12px" }}>Department AI Maturity Breakdown</h3>

        {data.departments.length === 0 ? (
          <div
            style={{
              padding: "36px 20px",
              textAlign: "center",
              background: "var(--surface-subtle)",
              borderRadius: "var(--radius-md)",
              border: "1px dashed var(--border-strong)",
            }}
          >
            <div style={{ fontSize: "2rem", marginBottom: "8px" }}>📊</div>
            <p style={{ fontWeight: "600", margin: "0 0 4px" }}>
              No privacy-safe team results are available yet.
            </p>
            <p style={{ fontSize: "0.85rem", color: "var(--text-muted)", maxWidth: "440px", margin: "0 auto" }}>
              At least {data.minimum_group_size} employees in a department must complete their diagnostic before aggregated scores and risks become visible to leadership.
            </p>
          </div>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Department / Team</th>
                <th>Completed</th>
                <th>Average Score</th>
                <th>Maturity Level</th>
              </tr>
            </thead>
            <tbody>
              {data.departments.map((team) => (
                <tr key={team.department}>
                  <td>
                    <strong>{team.department}</strong>
                    {team.department === "Other teams" && (
                      <span style={{ fontSize: "0.75rem", color: "var(--text-muted)", display: "block" }}>
                        Aggregated small teams (privacy-protected)
                      </span>
                    )}
                  </td>
                  <td>{team.completed}</td>
                  <td>
                    <strong>{team.average_score}</strong>{" "}
                    <span style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>/ 5.0</span>
                  </td>
                  <td>
                    <span className={`metric-badge ${getBadgeClass(team.level)}`}>
                      {team.level}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Top Risks */}
      <div style={{ marginTop: "32px" }}>
        <h3 style={{ fontSize: "1.1rem", margin: "0 0 12px" }}>Top Organizational AI Risks</h3>
        {data.top_risks.length === 0 ? (
          <p style={{ color: "var(--text-muted)", fontSize: "0.9rem" }}>
            No organizational risks flagged across reporting teams.
          </p>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
            {data.top_risks.map(([risk, count]) => (
              <div
                key={risk}
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  padding: "12px 16px",
                  background: "var(--surface-subtle)",
                  borderRadius: "var(--radius-sm)",
                  border: "1px solid var(--border-subtle)",
                }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                  <span style={{ color: "var(--rose)" }}>⚠️</span>
                  <span style={{ fontWeight: "600", textTransform: "capitalize", fontSize: "0.92rem" }}>
                    {risk.replaceAll("_", " ")}
                  </span>
                </div>
                <span
                  style={{
                    fontSize: "0.82rem",
                    fontWeight: "700",
                    padding: "3px 10px",
                    borderRadius: "9999px",
                    background: "var(--rose-subtle)",
                    color: "#fda4af",
                    border: "1px solid rgba(244, 63, 94, 0.25)",
                  }}
                >
                  {count} {count === 1 ? "occurrence" : "occurrences"}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
