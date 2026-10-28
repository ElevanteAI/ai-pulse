import React, { useEffect, useState } from "react";
import { api } from "../api.js";

export default function Diagnostic({ onDone }) {
  const [questions, setQuestions] = useState([]);
  const [answers, setAnswers] = useState({});
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const answered = Object.values(answers).filter((answer) => answer?.trim()).length;

  useEffect(() => {
    api("/diagnostic/questions").then(setQuestions).catch((err) => setError(err.message));
  }, []);

  async function submit() {
    if (questions.some((q) => !answers[q.id]?.trim())) {
      setError("Please answer every question before submitting.");
      return;
    }
    setSubmitting(true);
    setError("");
    const payload = Object.entries(answers).map(([question_id, answer]) => ({ question_id, answer }));
    try {
      await api("/diagnostic/submit", { method: "POST", body: JSON.stringify({ answers: payload }) });
      onDone();
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="card">
      <h2>Your AI diagnostic</h2>
      <p className="muted">Do not include customer, confidential, or personal information in your written answer.</p>
      {questions.length > 0 && <><p className="progress-label">Progress: {answered} of {questions.length}</p><div className="progress"><span style={{ width: `${(answered / questions.length) * 100}%` }} /></div></>}
      {questions.map((q) => (
        <div key={q.id}>
          <p><b>{q.text}</b></p>
          {q.type === "mcq" ? (
            <select onChange={(e) => setAnswers({ ...answers, [q.id]: e.target.value })} defaultValue="">
              <option value="" disabled>Choose…</option>
              {q.options.map((o) => <option key={o}>{o}</option>)}
            </select>
          ) : (
            <textarea rows={4} onChange={(e) => setAnswers({ ...answers, [q.id]: e.target.value })} />
          )}
        </div>
      ))}
      {error && <p className="error">{error}</p>}
      <button onClick={submit} disabled={submitting}>{submitting ? "Scoring…" : "Submit"}</button>
    </div>
  );
}
