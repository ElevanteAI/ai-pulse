import React, { useEffect, useState } from "react";
import { api } from "../api.js";

export default function Report({ onRetake }) {
  const [report, setReport] = useState(null);
  const [confirming, setConfirming] = useState(false);
  const [deleted, setDeleted] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    api("/reports/me").then(setReport);
  }, []);

  async function deleteMyData() {
    try {
      await api("/reports/me", { method: "DELETE" });
      setDeleted(true);
    } catch (err) { 
      setError(err.message);
    }
  }

  if (deleted) {
    return (
      <div className="card">
        <h2>Your data has been deleted</h2>
        <p>All your answers and your report were removed. They no longer appear on any dashboard.</p>
        <button onClick={onRetake}>Take the diagnostic again</button>
      </div>
    );
  }

  if (!report) return <p>Loading…</p>;
  return (
    <div className="card">
      <h2>{report.name}: {report.level}</h2>
      <p>Average score: {report.average_score ?? "Not assessed"}</p>
      <h3>Risks</h3>
      <ul>{report.risks.map((r) => <li key={r}>{r}</li>)}</ul>
      <h3>Next steps</h3>
      <ul>{report.next_steps.map((s) => <li key={s}>{s}</li>)}</ul>

      <h3>Your data</h3>
      {error && <p className="error">{error}</p>}
      {!confirming ? (
        <button onClick={() => setConfirming(true)}>Delete my answers and report</button>
      ) : (
        <p>
          This permanently removes all your answers and your report. This cannot be undone.{" "}
          <button onClick={deleteMyData}>Yes, delete everything</button>{" "}
          <button onClick={() => setConfirming(false)}>Cancel</button>
        </p>
      )}
    </div>
  );
}
