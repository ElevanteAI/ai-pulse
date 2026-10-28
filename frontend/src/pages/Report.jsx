import React, { useEffect, useState } from "react";
import { api, RISK_LABELS } from "../api.js";

const POLICY_TONE = { consistent: "ok", gap: "warn", risky: "warn", unaware: "warn", not_enough_data: "" };

export default function Report({ onTake }) {
  const [report, setReport] = useState(null);
  const [error, setError] = useState("");
  const [deleted, setDeleted] = useState(null);

  function load() {
    api("/reports/me").then(setReport).catch((e) => setError(e.message));
  }
  useEffect(load, []);

  async function deleteMyData() {
    const ok = window.confirm(
      `Delete all your answers and your report for ${report.organization}?\n\n` +
      "This can't be undone. You'll be removed from every dashboard immediately. You can take the diagnostic again later."
    );
    if (!ok) return;
    try {
      const r = await api("/reports/me", { method: "DELETE" });
      setDeleted(r.deleted_answers);
      load();
    } catch (err) {
      setError(err.message);
    }
  }

  if (error) return <div className="card"><p className="error">{error}</p></div>;
  if (!report) return <div className="card"><p>Loading…</p></div>;

  if (report.answered === 0) {
    return (
      <div className="card">
        {deleted !== null && (
          <p className="notice ok">Deleted {deleted} answers. Nothing of yours remains in the results for {report.organization}.</p>
        )}
        <h2>Welcome, {report.name}</h2>
        <p>You haven't taken the AI diagnostic for {report.organization} yet. It takes about 5 minutes.</p>
        <button onClick={onTake}>Start the diagnostic</button>
      </div>
    );
  }

  const pc = report.policy_check;
  return (
    <>
      <div className="card">
        <h2>{report.name}: {report.level}</h2>
        <p className="muted">
          Average score {report.average_score ?? "n/a"} out of 5, from {report.answered} answers · {report.organization}
        </p>

        <div className={`notice ${POLICY_TONE[pc.status]}`}>
          <b>Policy reality check.</b> {pc.message}
          {pc.evidence.length > 0 && <ul>{pc.evidence.map((e) => <li key={e}>{e}</li>)}</ul>}
          <p className="small muted">Only you can see this. Leadership sees team totals, never individual answers.</p>
        </div>

        <h3>Risks</h3>
        {report.risks.length
          ? <ul>{report.risks.map((r) => <li key={r}>{RISK_LABELS[r] || r}</li>)}</ul>
          : <p className="muted">None flagged.</p>}

        <h3>Next steps for your role</h3>
        <ul>{report.next_steps.map((s) => <li key={s}>{s}</li>)}</ul>
      </div>

      {report.ai_assessments.length > 0 && (
        <div className="card">
          <h3>What the AI said about your written answers</h3>
          {report.ai_assessments.map((a) => (
            <div key={a.question} className="question">
              <p className="small muted">{a.question}</p>
              {a.status === "scored" ? (
                <p><b>{a.score}/5</b>: {a.reason}</p>
              ) : (
                <p className="warn-text">
                  The AI couldn't score this answer reliably, so it isn't counted. Your result is based on your other answers.
                </p>
              )}
              <p className="small muted">
                Scored by: {a.scored_by === "mock" ? "demo mode (canned responses, not a real model)" : a.scored_by}
              </p>
            </div>
          ))}
        </div>
      )}

      <div className="card row">
        <button onClick={onTake}>Retake the diagnostic</button>
        <button className="danger" onClick={deleteMyData}>Delete my data</button>
      </div>
    </>
  );
}
