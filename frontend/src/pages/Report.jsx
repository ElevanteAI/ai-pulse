import React, { useEffect, useState } from "react";
import { api } from "../api.js";
import Badge from "../Badge.jsx";

export default function Report({ onRetake }) {
  const [report, setReport] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api("/reports/me").then(setReport).catch((e) => setError(e.message));
  }, []);

  async function deleteMyData() {
    const ok = window.confirm(
      "Delete all your answers and your report?\n\nThis removes you from every dashboard straight away and cannot be undone."
    );
    if (!ok) return;
    try {
      await api("/diagnostic/me", { method: "DELETE" });
      setReport(await api("/reports/me"));
    } catch (e) {
      setError(e.message);
    }
  }

  if (!report) return <p>{error || "Loading…"}</p>;

  const empty = report.answered === 0;

  return (
    <>
      <div className="card">
        <h2>{report.name}</h2>
        {empty ? (
          <p>You have no answers on file. Take the diagnostic to get your report.</p>
        ) : (
          <div className="score-row">
            <div>
              <div className="big">{report.average_score}</div>
              <div className="muted">average score (1–5)</div>
            </div>
            <Badge level={report.level} />
          </div>
        )}
        <div className="actions">
          <button onClick={onRetake}>{empty ? "Take the diagnostic" : "Retake diagnostic"}</button>
        </div>
      </div>

      {!empty && (
        <>
          <div className="card">
            <h3>Risks</h3>
            {report.risks.length === 0 ? (
              <p className="muted">No risks flagged.</p>
            ) : (
              <div className="chips">
                {report.risks.map((r) => <span key={r} className="badge badge-risk">{r.replaceAll("_", " ")}</span>)}
              </div>
            )}
            {report.remediation.map((r) => (
              <div key={r.risk}>
                <h4>How to fix: {r.title}</h4>
                <ul>{r.tips.map((t) => <li key={t}>{t}</li>)}</ul>
              </div>
            ))}
          </div>

          <div className="card">
            <h3>Next steps</h3>
            <ul>{report.next_steps.map((s) => <li key={s}>{s}</li>)}</ul>
          </div>

          <div className="card danger-zone">
            <h3>Your data</h3>
            <p>You can delete everything you submitted. It disappears from every dashboard immediately.</p>
            <button className="danger" onClick={deleteMyData}>Delete My Data</button>
          </div>
        </>
      )}
      {error && <p className="error">{error}</p>}
    </>
  );
}
