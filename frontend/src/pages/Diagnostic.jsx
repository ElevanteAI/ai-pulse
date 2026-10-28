import React, { useEffect, useState } from "react";
import { api } from "../api.js";

const MAX_CHARS = 2000;

export default function Diagnostic({ onDone }) {
  const [questions, setQuestions] = useState(null);
  const [answers, setAnswers] = useState({});
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api("/diagnostic/questions").then(setQuestions).catch((e) => setError(e.message));
  }, []);

  if (!questions) return <div className="card">{error ? <p className="error">{error}</p> : <p>Loading…</p>}</div>;

  const answered = questions.filter((q) => (answers[q.id] || "").trim()).length;
  const complete = answered === questions.length;
  const set = (id, value) => setAnswers({ ...answers, [id]: value });

  async function submit() {
    setBusy(true);
    setError("");
    try {
      const payload = questions.map((q) => ({ question_id: q.id, answer: answers[q.id] }));
      await api("/diagnostic/submit", { method: "POST", body: JSON.stringify({ answers: payload }) });
      onDone();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="card">
      <h2>Your AI diagnostic</h2>
      <p className="muted">
        {questions.length} questions, tailored to your role. Taking it again replaces your previous answers.
      </p>
      {questions.map((q, i) => (
        <div key={q.id} className="question">
          <p><b>{i + 1}. {q.text}</b></p>
          {q.type === "mcq" ? (
            q.options.map((o) => (
              <label key={o} className="option">
                <input type="radio" name={q.id} checked={answers[q.id] === o} onChange={() => set(q.id, o)} /> {o}
              </label>
            ))
          ) : (
            <>
              <textarea rows={4} maxLength={MAX_CHARS} value={answers[q.id] || ""} onChange={(e) => set(q.id, e.target.value)} />
              <p className="muted small">
                {(answers[q.id] || "").length}/{MAX_CHARS} · This answer is scored by an AI model. You'll see its
                score and reasoning on your report. Please don't include customer names or confidential details.
              </p>
            </>
          )}
        </div>
      ))}
      {error && <p className="error">{error}</p>}
      <button onClick={submit} disabled={!complete || busy}>
        {busy ? "Scoring…" : complete ? "Submit" : `Answer all questions (${answered}/${questions.length})`}
      </button>
    </div>
  );
}
