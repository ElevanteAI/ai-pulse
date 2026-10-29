import React, { useEffect, useState } from "react";
import { api } from "../api.js";

const riskNames = { customer_data_shared: "Customer data shared", confidential_data_shared: "Confidential data shared", unreviewed_output: "AI output used without review", policy_unaware: "AI policy needs a review" };

export default function Report({ onStart }) {
  const [report, setReport] = useState(null);
  const [suggestions, setSuggestions] = useState(null);
  const [error, setError] = useState("");
  const [suggestionError, setSuggestionError] = useState("");
  const [busy, setBusy] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    setError("");
    setReport(null);
    setSuggestions(null);
    setSuggestionError("");
    api("/reports/me", { signal: controller.signal }).then((data) => {
      setReport(data);
      if (!data.answered) return;
      api("/reports/me/suggestions", { method: "POST", signal: controller.signal })
        .then(setSuggestions)
        .catch((err) => { if (err.name !== "AbortError") setSuggestionError(err.message); });
    }).catch((err) => { if (err.name !== "AbortError") setError(err.message); });
    return () => controller.abort();
  }, [attempt]);

  async function deleteData() {
    setBusy(true);
    setError("");
    try {
      await api("/reports/me", { method: "DELETE" });
      setConfirmDelete(false);
      setSuggestions(null);
      setAttempt(attempt + 1);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  if (!report) return <section className="card narrow">{error ? <><p className="error" role="alert">{error}</p><button className="button secondary" onClick={() => setAttempt(attempt + 1)}>Try again</button></> : <p role="status">Loading your report...</p>}</section>;

  return (
    <section>
      <div className="page-heading"><span className="eyebrow">YOUR PERSONAL SNAPSHOT</span><h1>A clearer path forward.</h1><p className="muted">Your AI habits today, and a few ways to build on them.</p></div>
      {!report.answered ? <div className="card empty-state"><div className="empty-symbol" aria-hidden="true">+</div><h2>A fresh start</h2><p className="muted">No diagnostic answers are saved in this organization.</p><button className="button" onClick={onStart}>Start my diagnostic</button></div> : <>
        <div className="report-summary"><div><span className="eyebrow">CURRENT MATURITY</span><h2>{report.level}</h2><p>Your answers are a starting point for growth.</p></div><div className="score"><strong>{report.average_score ?? "--"}</strong><span>{report.average_score === null ? "Not assessed" : "out of 5"}</span></div></div>
        <div className="report-grid">
          <section className="card"><span className="eyebrow">PAY ATTENTION TO</span><h2>Your risk signals</h2><p className="muted">Signals from your answers, not a judgment of you.</p>{report.risks.length ? <ul className="risk-list">{report.risks.map((risk) => <li key={risk}><span className="risk-dot" />{riskNames[risk] || risk.replaceAll("_", " ")}</li>)}</ul> : <div className="positive-note">No risk flags were identified in the saved answers.</div>}<p className="fine-print">AI assessments can be wrong. Treat these as prompts for reflection.</p></section>
          <section className="card"><span className="eyebrow">MAKE IT PRACTICAL</span><h2>Your next three steps</h2>{suggestionError ? <><p className="error" role="alert">{suggestionError}</p><button className="text-button" onClick={() => setAttempt(attempt + 1)}>Retry suggestions</button></> : !suggestions ? <p className="muted" role="status">Preparing your suggestions...</p> : <><p className="fine-print">{suggestions.source === "static" ? "Role guidance shown because AI suggestions were unavailable." : "Suggested from your diagnostic. Review before acting."}</p><ol className="suggestion-list">{suggestions.suggestions.map((item, index) => <li key={index}><span className="step-number">0{index + 1}</span><div><h3>{item.title}</h3><p>{item.action}</p></div></li>)}</ol></>}</section>
        </div>
        <section className="card data-card"><div><h3>Your data, your choice</h3><p className="muted">Delete all your answers and report in this organization. Company results update immediately.</p></div><button className="button danger" onClick={() => setConfirmDelete(true)}>Delete my data</button></section>
      </>}
      {confirmDelete && <div className="modal-backdrop"><section className="card modal" role="dialog" aria-modal="true" aria-labelledby="delete-title"><span className="eyebrow">YOU ARE IN CONTROL</span><h2 id="delete-title">Delete your diagnostic?</h2><p>This removes your answers and report in {report.organization}. This cannot be undone. Your account and other organizations stay available.</p><div className="modal-actions"><button className="button secondary" autoFocus onClick={() => setConfirmDelete(false)} disabled={busy}>Keep my data</button><button className="button danger" onClick={deleteData} disabled={busy}>{busy ? "Deleting..." : "Yes, delete my data"}</button></div></section></div>}
      {error && <p className="error" role="alert">{error}</p>}
    </section>
  );
}
