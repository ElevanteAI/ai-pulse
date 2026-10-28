import React, { useEffect, useState } from "react";
import { api } from "../api.js";

// TODO: this is a placeholder. Leadership needs a real dashboard.
export default function Dashboard({ org }) {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api("/dashboard").then(setData).catch((err) => setError(err.message));
  }, []);

  if (error) return <div className="card"><p className="error">{error}</p></div>;
  if (!data) return <div className="card"><p>Loading dashboard…</p></div>;

  return (
    <div className="card">
      <h2>{data.organization} AI Pulse</h2>
      <p className="muted">Department results appear only when at least {data.minimum_group_size} people completed the diagnostic.</p>
      {data.departments.length === 0 ? <p>No privacy-safe team results are available yet.</p> : (
        <table><thead><tr><th>Team</th><th>Completed</th><th>Average</th><th>Level</th></tr></thead>
          <tbody>{data.departments.map((team) => <tr key={team.department}><td>{team.department}</td><td>{team.completed}</td><td>{team.average_score}</td><td>{team.level}</td></tr>)}</tbody>
        </table>
      )}
      <h3>Top risks</h3>
      {data.top_risks.length ? <ul>{data.top_risks.map(([risk, count]) => <li key={risk}>{risk.replaceAll("_", " ")}: {count}</li>)}</ul> : <p>No privacy-safe risk trends are available yet.</p>}
    </div>
  );
}
