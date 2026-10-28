import React, { useEffect, useState } from "react";
import { api } from "../api.js";

export default function Report({ onBack }) {
  const [report, setReport] = useState(null);
  const [error, setError] = useState("");
  const [deleted, setDeleted] = useState(false);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [deleting, setDeleting] = useState(false);

  // In-platform practice sandbox states: practiceId -> { input, submitting, feedback, passed }
  const [practiceStates, setPracticeStates] = useState({});

  useEffect(() => {
    api("/reports/me")
      .then((data) => {
        setReport(data);
        // Initialize starter inputs for in-platform practice (empty by default)
        const initial = {};
        (data.pulse_practice || []).forEach((item) => {
          initial[item.id] = {
            input: "",
            submitting: false,
            feedback: null,
            passed: false,
          };
        });
        setPracticeStates(initial);
      })
      .catch((err) => setError(err.message));
  }, []);

  function handleInputChange(id, val) {
    setPracticeStates((prev) => ({
      ...prev,
      [id]: { ...(prev[id] || {}), input: val },
    }));
  }

  function handleResetInput(item) {
    setPracticeStates((prev) => ({
      ...prev,
      [item.id]: {
        ...(prev[item.id] || {}),
        input: "",
        feedback: null,
        passed: false,
      },
    }));
  }

  async function submitPractice(item) {
    const currentState = practiceStates[item.id] || {};
    const solution = currentState.input || "";
    if (!solution.trim()) return;

    setPracticeStates((prev) => ({
      ...prev,
      [item.id]: { ...(prev[item.id] || {}), submitting: true, feedback: null },
    }));

    try {
      const result = await api("/reports/practice/verify", {
        method: "POST",
        body: JSON.stringify({
          practice_id: item.id,
          scenario_description: item.scenario_description || item.practice,
          user_solution: solution,
        }),
      });

      setPracticeStates((prev) => ({
        ...prev,
        [item.id]: {
          ...(prev[item.id] || {}),
          submitting: false,
          feedback: result.feedback,
          passed: result.passed,
          score: result.score,
        },
      }));
    } catch (err) {
      setPracticeStates((prev) => ({
        ...prev,
        [item.id]: {
          ...(prev[item.id] || {}),
          submitting: false,
          feedback: "Could not evaluate practice: " + err.message,
          passed: false,
        },
      }));
    }
  }

  async function confirmDelete() {
    setDeleting(true);
    try {
      await api("/reports/me", { method: "DELETE" });
      setDeleted(true);
      setShowDeleteModal(false);
    } catch (err) {
      setError(err.message);
    } finally {
      setDeleting(false);
    }
  }

  function getBadgeClass(level) {
    switch (level?.toLowerCase()) {
      case "leader":
        return "badge-leader";
      case "practitioner":
        return "badge-practitioner";
      case "exploring":
        return "badge-exploring";
      default:
        return "badge-beginner";
    }
  }

  if (error) {
    return (
      <div className="card">
        <div className="error-banner">{error}</div>
      </div>
    );
  }

  if (deleted) {
    return (
      <div className="card" style={{ textAlign: "center", padding: "52px 32px" }}>
        <div style={{ fontSize: "2.8rem", marginBottom: "16px" }}>🗑️</div>
        <h2 className="card-title">Diagnostic Data Permanently Erased</h2>
        <p className="card-subtitle" style={{ maxWidth: "500px", margin: "0 auto 24px" }}>
          In accordance with your organization's privacy protocol, all submitted diagnostic responses and personal scores have been hard-deleted.
        </p>
        <p style={{ fontSize: "0.88rem", color: "var(--text-muted)" }}>
          Your data no longer impacts team maturity scores or organizational risk dashboards.
        </p>
      </div>
    );
  }

  if (!report) {
    return (
      <div className="card" style={{ textAlign: "center", padding: "48px" }}>
        <p style={{ color: "var(--navy-primary)", fontWeight: "600" }}>Loading your diagnostic report…</p>
      </div>
    );
  }

  const practices = report.pulse_practice || [];

  return (
    <>
      <div className="card">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "12px", marginBottom: "20px" }}>
          <div>
            <h2 className="card-title" style={{ margin: "0 0 4px" }}>
              {report.name}'s AI Maturity Diagnostic Report
            </h2>
            <p style={{ color: "var(--text-secondary)", fontSize: "0.9rem", margin: 0 }}>
              Organization: <strong style={{ color: "var(--navy-primary)" }}>{report.organization}</strong>
              {report.completed_at && ` • Completed: ${new Date(report.completed_at).toLocaleDateString()}`}
            </p>
          </div>
          <span className={`metric-badge ${getBadgeClass(report.level)}`}>
            {report.level || "Unassessed"}
          </span>
        </div>

        {/* High-level metrics */}
        <div className="metrics-grid">
          <div className="metric-card">
            <p className="metric-label">Assessed Maturity</p>
            <p className="metric-value">
              {report.level}
            </p>
          </div>
          <div className="metric-card">
            <p className="metric-label">Composite Score</p>
            <p className="metric-value">
              {report.average_score ?? "N/A"}{" "}
              <span style={{ fontSize: "0.9rem", color: "var(--text-muted)", fontWeight: "normal" }}>/ 5.0</span>
            </p>
          </div>
          <div className="metric-card">
            <p className="metric-label">Identified Risk Areas</p>
            <p className="metric-value" style={{ color: report.risks?.length ? "var(--rose)" : "var(--emerald)" }}>
              {report.risks?.length || 0}
            </p>
          </div>
        </div>

        {/* Active Risk Flags */}
        {report.risks?.length > 0 && (
          <div>
            <h3 style={{ fontSize: "0.95rem", margin: "0 0 8px", color: "var(--navy-primary)" }}>
              Identified Enterprise Risks:
            </h3>
            <div className="risk-chips">
              {report.risks.map((r) => (
                <span key={r} className="risk-chip">
                  <span>⚠️</span> {r.replaceAll("_", " ")}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* In-Platform Pulse Practice Hub */}
        {practices.length > 0 && (
          <div>
            <div className="section-title">
              <div>
                <span style={{ color: "var(--gold-accent)", fontSize: "0.72rem", letterSpacing: "0.12em", textTransform: "uppercase", display: "block", marginBottom: "2px" }}>
                  ELEVATING CAPABILITY • IN-PLATFORM SPRINT
                </span>
                <span>Pulse Practice • Interactive Workplace Sprints</span>
              </div>
              <span style={{ fontSize: "0.82rem", color: "var(--text-muted)", fontWeight: "normal" }}>
                Practice on this platform & get instant AI review
              </span>
            </div>

            <p style={{ fontSize: "0.92rem", color: "var(--text-secondary)", marginTop: "4px" }}>
              Tailored micro-practices generated specifically for each area identified in your assessment. Practice directly in the interactive sandbox below to build safe, high-leverage AI habits.
            </p>

            <div className="practice-grid">
              {practices.map((item) => {
                const state = practiceStates[item.id] || {};
                return (
                  <div key={item.id} className="practice-card">
                    <div className="practice-header">
                      <div className="practice-title-group">
                        <h4>{item.title}</h4>
                        <span className="practice-provider">
                          Curated by: {item.provider} • <span style={{ textTransform: "capitalize" }}>{item.topic?.replace("_", " ")}</span>
                        </span>
                      </div>
                      <span className="practice-duration">⏱️ {item.duration_minutes} min practice</span>
                    </div>

                    <div className="practice-why">
                      <strong>Why you received this:</strong> {item.why}
                    </div>

                    {/* Interactive In-Platform Sandbox */}
                    <div className="practice-sandbox">
                      <div className="sandbox-header">
                        <span className="sandbox-title">
                          <span style={{ color: "var(--navy-primary)", fontWeight: 700 }}>◈</span> {item.scenario_title || "Interactive Practice Challenge"}
                        </span>
                        {state.passed && (
                          <span style={{ fontSize: "0.8rem", fontWeight: "700", color: "var(--emerald)" }}>
                            Completed in Session ✅
                          </span>
                        )}
                      </div>

                      <p className="sandbox-scenario">
                        <strong>Task:</strong> {item.scenario_description}
                      </p>

                      {item.starter_input && (
                        <div className="sandbox-context-box">
                          <div className="context-label">
                            <span>📋 Incoming Scenario / Context:</span>
                            <button
                              type="button"
                              className="link-btn"
                              style={{ fontSize: "0.78rem", textDecoration: "underline" }}
                              onClick={() => handleInputChange(item.id, item.starter_input)}
                              title="Copy this text into your solution box to edit or redact it"
                            >
                              Insert text into editor ↵
                            </button>
                          </div>
                          <pre className="context-text">{item.starter_input}</pre>
                        </div>
                      )}

                      <p style={{ fontSize: "0.85rem", fontWeight: "700", color: "var(--navy-primary)", margin: "0 0 6px" }}>
                        ✍️ Your Practice Solution / Response:
                      </p>

                      <textarea
                        rows={4}
                        className="sandbox-textarea"
                        value={state.input || ""}
                        onChange={(e) => handleInputChange(item.id, e.target.value)}
                        placeholder="Type your response, policy checklist, or sanitized text here..."
                      />

                      <div className="sandbox-actions">
                        <button
                          type="button"
                          onClick={() => submitPractice(item)}
                          disabled={state.submitting || !state.input?.trim()}
                        >
                          {state.submitting ? "Live AI Evaluating…" : "Submit Practice for AI Review"}
                        </button>

                        <button
                          type="button"
                          className="link-btn"
                          onClick={() => handleResetInput(item)}
                        >
                          ↺ Reset Challenge
                        </button>
                      </div>

                      {/* Live AI Feedback */}
                      {state.feedback && (
                        <div
                          className={`practice-feedback ${
                            state.passed ? "feedback-success" : "feedback-retry"
                          }`}
                        >
                          <div style={{ fontWeight: "700", marginBottom: "4px" }}>
                            {state.passed ? "Evaluation Passed ✅ (Score: " + (state.score || 5) + "/5)" : "Review & Refine 💡"}
                          </div>
                          <div>{state.feedback}</div>
                        </div>
                      )}
                    </div>

                    {/* Bonus External Resource */}
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "10px", marginTop: "12px" }}>
                      <span style={{ fontSize: "0.82rem", color: "var(--text-muted)" }}>
                        🎯 <strong>Goal:</strong> {item.success_measure}
                      </span>
                      {item.bonus_url && (
                        <a
                          href={item.bonus_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="bonus-link-btn"
                          title="Open official documentation for extended deep dive"
                        >
                          Bonus: Open {item.provider} Guide ↗
                        </a>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Coaching Directives */}
        {report.coaching?.length > 0 && (
          <div style={{ marginTop: "34px" }}>
            <h3 style={{ fontSize: "1.1rem", margin: "0 0 14px", color: "var(--navy-primary)" }}>
              Specific Safety Directives
            </h3>
            {report.coaching.map((item) => (
              <div className="coaching-card" key={item.risk}>
                <b>{item.title}</b>
                <p>{item.action}</p>
              </div>
            ))}
          </div>
        )}

        {/* Role Next Steps */}
        {report.next_steps?.length > 0 && (
          <div style={{ marginTop: "28px" }}>
            <h3 style={{ fontSize: "1.1rem", margin: "0 0 12px", color: "var(--navy-primary)" }}>
              Recommended Role Next Steps
            </h3>
            <ul style={{ paddingLeft: "20px", color: "var(--text-secondary)", lineHeight: "1.7" }}>
              {report.next_steps.map((s) => (
                <li key={s}>{s}</li>
              ))}
            </ul>
          </div>
        )}

        <hr style={{ border: "0", borderTop: "1px solid var(--border-subtle)", margin: "34px 0 24px" }} />

        {/* Right to Delete / Privacy Compliance */}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "16px" }}>
          <div>
            <h3 style={{ fontSize: "1rem", margin: "0 0 4px", color: "var(--navy-primary)" }}>
              Data Privacy & Right to Erasure
            </h3>
            <p style={{ fontSize: "0.85rem", color: "var(--text-muted)", margin: 0, maxWidth: "520px" }}>
              Exercise your right to delete your diagnostic. All submitted answers, maturity scores, and risk flags will be purged immediately from this organization.
            </p>
          </div>
          <button className="outline-danger" onClick={() => setShowDeleteModal(true)}>
            Delete My Data
          </button>
        </div>
      </div>

      {/* Confirmation Modal */}
      {showDeleteModal && (
        <div className="modal-overlay">
          <div className="modal-content">
            <h3 style={{ margin: "0 0 12px", color: "var(--rose)", fontSize: "1.25rem" }}>
              Permanently Erase Diagnostic Data?
            </h3>
            <p style={{ color: "var(--text-secondary)", fontSize: "0.92rem", lineHeight: "1.6" }}>
              Are you sure you want to delete all diagnostic answers, scores, and risks for <strong>{report.organization}</strong>?
            </p>
            <p style={{ color: "var(--text-muted)", fontSize: "0.85rem", margin: "14px 0" }}>
              ⚠️ This action is irreversible. All team dashboards will immediately update without your data.
            </p>
            <div className="modal-actions">
              <button className="secondary" onClick={() => setShowDeleteModal(false)} disabled={deleting}>
                Cancel
              </button>
              <button className="danger" onClick={confirmDelete} disabled={deleting}>
                {deleting ? "Purging data…" : "Confirm Permanent Delete"}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
