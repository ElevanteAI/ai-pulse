import React, { useEffect, useState } from "react";
import { api } from "../api.js";

export default function Diagnostic({ onDone, onBack }) {
  const [questions, setQuestions] = useState([]);
  const [answers, setAnswers] = useState({});
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const answeredCount = Object.values(answers).filter((a) => a && a.trim()).length;
  const progressPercent = questions.length ? Math.round((answeredCount / questions.length) * 100) : 0;

  useEffect(() => {
    api("/diagnostic/questions")
      .then(setQuestions)
      .catch((err) => setError(err.message));
  }, []);

  function handleSelectOption(questionId, optionText) {
    setAnswers((prev) => ({ ...prev, [questionId]: optionText }));
  }

  function handleTextChange(questionId, text) {
    setAnswers((prev) => ({ ...prev, [questionId]: text }));
  }

  async function submit() {
    if (questions.some((q) => !answers[q.id]?.trim())) {
      setError("Please answer every question before submitting your diagnostic.");
      window.scrollTo({ top: 0, behavior: "smooth" });
      return;
    }
    setSubmitting(true);
    setError("");
    const payload = Object.entries(answers).map(([question_id, answer]) => ({
      question_id,
      answer,
    }));
    try {
      await api("/diagnostic/submit", {
        method: "POST",
        body: JSON.stringify({ answers: payload }),
      });
      onDone();
    } catch (err) {
      setError(err.message);
      window.scrollTo({ top: 0, behavior: "smooth" });
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="card">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
        <h2 className="card-title" style={{ margin: 0 }}>Role-Adaptive AI Diagnostic</h2>
        {onBack && (
          <button type="button" className="secondary" style={{ padding: "6px 12px", fontSize: "0.82rem" }} onClick={onBack}>
            ← Back
          </button>
        )}
      </div>
      <p className="card-subtitle">
        Questions are adapted to your job role and seniority. Please provide honest reflections on your daily AI use.
      </p>

      {error && <div className="error-banner">{error}</div>}

      {questions.length > 0 && (
        <div className="progress-container">
          <div className="progress-header">
            <span>Completion Progress</span>
            <span>
              {answeredCount} of {questions.length} answered ({progressPercent}%)
            </span>
          </div>
          <div className="progress-track">
            <div className="progress-fill" style={{ width: `${progressPercent}%` }} />
          </div>
        </div>
      )}

      {questions.map((q, idx) => {
        const currentAnswer = answers[q.id] || "";
        return (
          <div key={q.id} className="question-block">
            <p className="question-text">
              <span style={{ color: "var(--primary)", marginRight: "8px" }}>Q{idx + 1}.</span>
              {q.text}
            </p>

            {q.type === "mcq" ? (
              <div className="options-grid">
                {q.options.map((opt) => {
                  const isSelected = currentAnswer === opt;
                  return (
                    <div
                      key={opt}
                      className={`option-card ${isSelected ? "selected" : ""}`}
                      onClick={() => handleSelectOption(q.id, opt)}
                    >
                      <div className="option-radio" />
                      <span style={{ fontSize: "0.92rem" }}>{opt}</span>
                    </div>
                  );
                })}
              </div>
            ) : (
              <div>
                <p style={{ fontSize: "0.8rem", color: "var(--amber)", margin: "0 0 8px" }}>
                  ⚠️ Privacy Notice: Do not paste real customer names, confidential secrets, or internal keys.
                </p>
                <textarea
                  rows={4}
                  placeholder="Describe your typical AI use cases, prompt patterns, and how you verify the output..."
                  value={currentAnswer}
                  onChange={(e) => handleTextChange(q.id, e.target.value)}
                />
              </div>
            )}
          </div>
        );
      })}

      <div style={{ display: "flex", justifyContent: "flex-end", marginTop: "24px" }}>
        <button onClick={submit} disabled={submitting}>
          {submitting ? "Analyzing Diagnostic with Live AI…" : "Submit Diagnostic"}
        </button>
      </div>
    </div>
  );
}
