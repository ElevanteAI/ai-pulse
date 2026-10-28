import React, { useEffect, useState } from "react";
import { api } from "../api.js";

export default function Report() {
  const [report, setReport] = useState(null);
  const [error, setError] = useState("");
  const [deleted, setDeleted] = useState(false);

  useEffect(() => {
    api("/reports/me").then(setReport).catch((err) => setError(err.message));
  }, []);

  async function deleteData() {
    if (!window.confirm("Delete all of your diagnostic answers and report for this organization? This cannot be undone.")) return;
    try {
      await api("/reports/me", { method: "DELETE" });
      setDeleted(true);
    } catch (err) {
      setError(err.message);
    }
  }

  if (error) return <div className="card"><p className="error">{error}</p></div>;
  if (deleted) return <div className="card"><h2>Your diagnostic data was deleted</h2><p>Your answers and report no longer contribute to dashboards.</p></div>;
  if (!report) return <p>Loading…</p>;
  return (
    <div className="card">
      <h2>{report.name}: {report.level}</h2>
      <p>Average score: {report.average_score}</p>
      <h3>Risks</h3>
      {report.risks.length ? <ul>{report.risks.map((r) => <li key={r}>{r.replaceAll("_", " ")}</li>)}</ul> : <p>No risks were identified.</p>}
      <h3>Next steps</h3>
      <ul>{report.next_steps.map((s) => <li key={s}>{s}</li>)}</ul>
      {report.coaching.length > 0 && <><h3>Your safe-use coaching</h3>{report.coaching.map((item) => <div className="coaching" key={item.risk}><b>{item.title}</b><p>{item.action}</p></div>)}</>}
      <hr />
      <h3>Delete my diagnostic data</h3>
      <p className="muted">This permanently deletes your answers and report for {report.organization}.</p>
      <button className="danger" onClick={deleteData}>Delete my data</button>
    </div>
  );
}
