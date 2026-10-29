import React, { useEffect, useState } from "react";
import { api } from "../api.js";

export default function Diagnostic({ onDone }) {
  const [questions, setQuestions] = useState([]);
  const [answers, setAnswers] = useState({});
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [attempt, setAttempt] = useState(0);
  const completed = questions.filter((question) => answers[question.id]?.trim()).length;

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError("");
    api("/diagnostic/questions", { signal: controller.signal })
      .then(setQuestions)
      .catch((err) => { if (err.name !== "AbortError") setError(err.message); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [attempt]);

  async function submit(event) {
    event.preventDefault();
    if (!questions.length || completed !== questions.length) {
      setError("Please answer every question before submitting.");
      return;
    }
    setBusy(true);
    setError("");
    try {
      const payload = questions.map((question) => ({ question_id: question.id, answer: answers[question.id].trim() }));
      await api("/diagnostic/submit", { method: "POST", body: JSON.stringify({ answers: payload }) });
      onDone();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="narrow">
      <div className="page-heading"><span className="eyebrow">YOUR STARTING POINT</span><h1>A little reflection.<br />A useful next step.</h1><p className="muted">Answer honestly about your everyday work. This is a diagnostic, not an exam.</p></div>
      {loading ? <p className="card" role="status">Loading your questions...</p> : questions.length ? (
        <form onSubmit={submit}>
          <div className="progress-card"><div className="row"><strong>Your progress</strong><span className="muted" aria-live="polite">{completed} of {questions.length} answered</span></div><progress value={completed} max={questions.length} aria-label="Diagnostic completion" /></div>
          {questions.map((question, index) => <div className="card question-card" key={question.id}>
            <label htmlFor={question.id}><span className="question-number">{String(index + 1).padStart(2, "0")}</span>{question.text}</label>
            {question.type === "mcq" ? <select id={question.id} value={answers[question.id] || ""} required disabled={busy} onChange={(e) => setAnswers({ ...answers, [question.id]: e.target.value })}>
              <option value="" disabled>Select an answer</option>
              {question.options.map((option) => <option key={option}>{option}</option>)}
            </select> : <><p className="fine-print">Use an anonymized example. Leave out names, customer details and confidential information.</p><textarea id={question.id} rows={4} value={answers[question.id] || ""} required disabled={busy} onChange={(e) => setAnswers({ ...answers, [question.id]: e.target.value })} placeholder="Tell us about your approach..." /></>}
          </div>)}
          {error && <p className="error" role="alert">{error}</p>}
          <div className="submit-row"><span className="fine-print">Your answers can be deleted from your report.</span><button className="button" disabled={busy}>{busy ? "Saving and assessing..." : "View my report"} <span aria-hidden="true">&rarr;</span></button></div>
        </form>
      ) : <div className="card"><p className="error" role="alert">{error || "No questions are available."}</p><button className="button secondary" onClick={() => setAttempt(attempt + 1)}>Try again</button></div>}
    </section>
  );
}
