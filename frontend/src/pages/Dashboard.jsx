import React, { useEffect, useState } from "react";
import { api } from "../api.js";

// TODO: this is a placeholder. Leadership needs a real dashboard.
export default function Dashboard({ org }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    api(`/dashboard?org_id=${org.org_id}`)
      .then(setData)
      .catch((err) => {
        setError(err.message || "Failed to load dashboard");
      })
      .finally(() => setLoading(false));
  }, [org]);

  if (loading) {
    return (
      <div className="card">
        <h2>Dashboard</h2>
        <p>Loading...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="card" style={{ borderLeft: "3px solid var(--warning)" }}>
        <h2>Dashboard</h2>
        <p style={{ color: "var(--muted)" }}>Error: {error}</p>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="card">
        <h2>Dashboard</h2>
        <p>No data available</p>
      </div>
    );
  }

  const responseRates = data.response_rates || [];
  const overall = data.overall || { completed: 0, invited: 0 };
  const hiddenTeamCount = data.hidden_team_count || 0;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
      <div className="card">
        <h2>{data.organization}</h2>
        <p style={{ color: "var(--muted)", marginBottom: "1rem" }}>
          Overall: <strong>{overall.completed} / {overall.invited}</strong> completed
        </p>

        {/* Response Rates Section */}
        {responseRates.length > 0 ? (
          <div style={{ marginBottom: "1.5rem" }}>
            <h3 style={{ marginTop: 0, marginBottom: "1rem", fontSize: "1rem", color: "var(--text)" }}>
              Response Rates
            </h3>
            {responseRates.map((team, idx) => {
              const percentage = team.invited > 0 ? (team.completed / team.invited) * 100 : 0;
              return (
                <div
                  key={idx}
                  style={{
                    marginBottom: "0.75rem",
                    padding: "0.75rem",
                    backgroundColor: "var(--surface)",
                    border: "1px solid var(--line)",
                    borderRadius: "0.25rem",
                  }}
                >
                  <div
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      marginBottom: "0.5rem",
                      fontSize: "0.9rem",
                    }}
                  >
                    <span style={{ fontWeight: "500", color: "var(--text)" }}>{team.team_name}</span>
                    <span style={{ color: "var(--muted)" }}>
                      {team.completed} / {team.invited}
                    </span>
                  </div>
                  <div
                    style={{
                      height: "8px",
                      backgroundColor: "var(--g1)",
                      borderRadius: "4px",
                      overflow: "hidden",
                    }}
                  >
                    <div
                      style={{
                        height: "100%",
                        width: `${percentage}%`,
                        backgroundColor: "var(--g)",
                        transition: "width 0.3s ease",
                      }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        ) : (
          <p style={{ color: "var(--muted)", marginBottom: "1rem" }}>
            No team has enough responses to display yet.
          </p>
        )}

        {/* Hidden Teams Card */}
        {hiddenTeamCount > 0 && (
          <div
            style={{
              padding: "1rem",
              backgroundColor: "var(--surface)",
              border: "1px solid var(--line)",
              borderLeft: "3px solid var(--med)",
              borderRadius: "0.25rem",
              marginTop: "1rem",
              fontSize: "0.9rem",
              color: "var(--text)",
            }}
          >
            <strong>{hiddenTeamCount} team{hiddenTeamCount !== 1 ? "s" : ""} hidden:</strong> fewer than 5 responses.
            Their results are not shown to protect anonymity.
          </div>
        )}

        {/* Raw Data for Reference */}
        <details style={{ marginTop: "1.5rem", color: "var(--muted)", fontSize: "0.85rem" }}>
          <summary style={{ cursor: "pointer", userSelect: "none" }}>Raw Data</summary>
          <pre style={{ marginTop: "0.5rem", overflow: "auto", maxHeight: "300px" }}>
            {JSON.stringify(data, null, 2)}
          </pre>
        </details>
      </div>
    </div>
  );
}
