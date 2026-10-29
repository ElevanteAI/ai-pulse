import React, { useEffect, useState } from "react";
import { api } from "../api.js";

const MIN_OPEN_LENGTH = 20;

function problem(q, value) {
  if (!value || !value.trim()) return "This question needs an answer.";
  if (q.type === "open" && value.trim().length < MIN_OPEN_LENGTH) {
    return `Please write at least ${MIN_OPEN_LENGTH} characters.`;
  }
  return "";
}

export default function Diagnostic({ onDone }) {
  const [questions, setQuestions] = useState(null);
  const [answers, setAnswers] = useState({});
  const [errors, setErrors] = useState({});
  const [submitting, setSubmitting] = useState(false);
  const [serverError, setServerError] = useState("");

  useEffect(() => {
    api("/diagnostic/questions").then(setQuestions).catch((e) => setServerError(e.message));
  }, []);

  function setAnswer(q, value) {
    setAnswers({ ...answers, [q.id]: value });
    if (errors[q.id]) setErrors({ ...errors, [q.id]: problem(q, value) });
  }

  async function submit(e) {
    e.preventDefault();
    const found = {};
    for (const q of questions) {
      const msg = problem(q, answers[q.id]);
      if (msg) found[q.id] = msg;
    }
    setErrors(found);
    if (Object.keys(found).length) return;

    setSubmitting(true);
    setServerError("");
    try {
      const payload = questions.map((q) => ({ question_id: q.id, answer: answers[q.id].trim() }));
      await api("/diagnostic/submit", { method: "POST", body: JSON.stringify({ answers: payload }) });
      onDone();
    } catch (err) {
      setServerError(err.message);
      setSubmitting(false);
    }
  }

  if (!questions) return <p>{serverError || "Loading…"}</p>;

  const answered = questions.filter((q) => !problem(q, answers[q.id])).length;

  return (
    <form className="card" onSubmit={submit} noValidate>
      <h2>Your AI diagnostic</h2>
      <p className="muted">{answered} of {questions.length} questions complete. Submitting replaces any earlier answers.</p>
      {questions.map((q, i) => (
        <div key={q.id} className="field">
          <label htmlFor={q.id}><b>{i + 1}. {q.text}</b></label>
          {q.type === "mcq" ? (
            <select id={q.id} value={answers[q.id] || ""} onChange={(e) => setAnswer(q, e.target.value)}>
              <option value="" disabled>Choose…</option>
              {q.options.map((o) => <option key={o}>{o}</option>)}
            </select>
          ) : (
            <textarea id={q.id} rows={4} value={answers[q.id] || ""} onChange={(e) => setAnswer(q, e.target.value)} />
          )}
          {errors[q.id] && <p className="error">{errors[q.id]}</p>}
        </div>
      ))}
      {serverError && <p className="error">{serverError}</p>}
      <button disabled={submitting}>{submitting ? "Submitting…" : "Submit"}</button>
    </form>
  );
}
