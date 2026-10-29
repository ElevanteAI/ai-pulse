import React, { useEffect, useState } from "react";
import { api } from "../api.js";
import Badge from "../Badge.jsx";

function Section({ title, items }) {
  return (
    <>
      <h4>{title}</h4>
      <ul>{items.map((i) => <li key={i}>{i}</li>)}</ul>
    </>
  );
}

function ActionCard({ card, onClose }) {
  return (
    <div className="card playbook">
      <button className="secondary" onClick={onClose} style={{ float: "right" }}>Close</button>
      <h3>{card.title}</h3>
      <p>{card.summary}</p>
      <Section title="Recommended guardrails" items={card.guardrails} />
      <Section title="Approved tooling policy" items={card.approved_tooling} />
      <Section title="Team guidance" items={card.team_guidance} />
    </div>
  );
}

function Stat({ label, children }) {
  return (
    <div className="card stat">
      <div className="muted">{label}</div>
      <div className="big">{children}</div>
    </div>
  );
}

export default function Dashboard({ org }) {
  const [data, setData] = useState(null);
  const [card, setCard] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api(`/dashboard?org_id=${org.org_id}`).then(setData).catch((e) => setError(e.message));
  }, [org]);

  function openRisk(risk) {
    setError("");
    api(`/playbooks/${risk}`).then(setCard).catch((e) => setError(e.message));
  }

  if (!data) return <p>{error || "Loading…"}</p>;

  const { totals } = data;
  const rate = totals.headcount ? Math.round((totals.completed / totals.headcount) * 100) : 0;

  return (
    <>
      <h2>{data.organization}</h2>
      <div className="stats">
        <Stat label="Total headcount">{totals.headcount}</Stat>
        <Stat label="Completed diagnostics">
          {totals.completed} <small className="muted">({rate}%)</small>
        </Stat>
        <Stat label="Company AI maturity"><Badge level={totals.level} /></Stat>
      </div>

      <div className="card">
        <h3>Teams</h3>
        <table>
          <thead>
            <tr><th>Team</th><th>Responded</th><th>Average</th><th>Level</th></tr>
          </thead>
          <tbody>
            {data.departments.map((d) => (
              <tr key={d.department}>
                <td>
                  {d.department}{" "}
                  {d.department === "Other teams" && (
                    <span className="badge badge-private" title="Teams with fewer than 5 respondents are grouped so no individual can be identified">
                      Privacy-protected
                    </span>
                  )}
                </td>
                <td>{d.responded} / {d.employees}</td>
                <td>{d.average_score ?? "–"}</td>
                <td>{d.suppressed ? <span className="muted">{d.level}</span> : <Badge level={d.level} />}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <p className="muted">Teams with fewer than 5 respondents are pooled as "Other teams"; their scores and risks are hidden.</p>
      </div>

      <div className="card">
        <h3>Risk alerts</h3>
        {data.top_risks.length === 0 ? (
          <p className="muted">No risks to show.</p>
        ) : (
          <>
            <p className="muted">Select a risk to see the recommended actions.</p>
            <div className="chips">
              {data.top_risks.map(([risk, count]) => (
                <button key={risk} className="risk-button" onClick={() => openRisk(risk)}>
                  {risk.replaceAll("_", " ")} <span className="count">{count}</span>
                </button>
              ))}
            </div>
          </>
        )}
        {error && <p className="error">{error}</p>}
      </div>

      {card && <ActionCard card={card} onClose={() => setCard(null)} />}
    </>
  );
}
