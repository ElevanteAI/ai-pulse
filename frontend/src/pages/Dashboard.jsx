import React, { useEffect, useState } from "react";
import { api, RISK_LABELS } from "../api.js";

function Risks({ risks }) {
  if (!risks.length) return <span className="muted">none</span>;
  return risks.map((r) => <div key={r.risk} className="small">{RISK_LABELS[r.risk] || r.risk} ({r.people})</div>);
}

export default function Dashboard() {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api("/dashboard").then(setData).catch((e) => setError(e.message));
  }, []);

  if (error) return <div className="card"><p className="error">{error}</p></div>;
  if (!data) return <div className="card"><p>Loading…</p></div>;

  const n = data.min_group_size;
  return (
    <>
      <div className="card">
        <h2>{data.organization}</h2>
        {data.overall ? (
          <div className="stats">
            <div><span className="big">{data.overall.level}</span><span className="muted">overall maturity</span></div>
            <div><span className="big">{data.overall.average_score}</span><span className="muted">average score (1–5)</span></div>
            <div><span className="big">{data.overall.respondents}</span><span className="muted">people included</span></div>
          </div>
        ) : (
          <p>Not enough responses yet. Results appear once at least {n} people in a group have taken the diagnostic.</p>
        )}
        <p className="small muted">
          To protect anonymity, no group with fewer than {n} responses is shown on its own.
          {data.small_teams_left_out && " Teams below that size are left out of every number on this page."}
        </p>
      </div>

      {data.policy_reality && (
        <div className="card">
          <h3>Policy reality check</h3>
          <p className="headline">{data.policy_reality.headline}</p>
          <p className="small muted">
            “Gap” means people who say they follow the AI policy but whose answers show customer or confidential data
            reaching AI tools. A high gap means the policy isn't changing behaviour, so practical training or approved
            tools will help more than another policy email.
          </p>
        </div>
      )}

      {data.groups.length > 0 && (
        <div className="card">
          <h3>By team</h3>
          <table>
            <thead>
              <tr><th>Team</th><th>Level</th><th>Avg</th><th>Responded</th><th>Policy gap</th><th>Top risks</th></tr>
            </thead>
            <tbody>
              {data.groups.map((g) => (
                <tr key={g.department}>
                  <td>
                    {g.department}
                    {g.includes && <div className="small muted">{g.includes.join(", ")}</div>}
                  </td>
                  <td>{g.level}</td>
                  <td>{g.average_score}</td>
                  <td>{g.respondents}{g.employees ? ` / ${g.employees}` : ""}</td>
                  <td>{g.policy_reality.of_whom_risky_practice} of {g.policy_reality.say_they_follow_policy}</td>
                  <td><Risks risks={g.top_risks} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {data.not_shown.length > 0 && (
        <div className="card">
          <h3>Not shown separately</h3>
          <p className="small muted">
            Fewer than {n} responses each (possibly none).{" "}
            {data.small_teams_left_out ? "Not included in any figure." : "Included in Other teams."}
          </p>
          <ul>
            {data.not_shown.map((d) => <li key={d.department}>{d.department}</li>)}
          </ul>
        </div>
      )}

      {data.overall && (
        <div className="card">
          <h3>Top risks across the company</h3>
          <Risks risks={data.top_risks} />
          {data.ai_scoring && (
            <p className="small muted">
              AI scoring: {data.ai_scoring.open_answers} written answers, {data.ai_scoring.needs_review} could not be
              scored reliably and are excluded from all averages.
            </p>
          )}
        </div>
      )}
    </>
  );
}
