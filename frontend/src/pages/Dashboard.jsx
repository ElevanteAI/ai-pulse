import React, { useEffect, useState } from "react";
import { api } from "../api.js";

export default function Dashboard() {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    setError("");
    api("/dashboard", { signal: controller.signal }).then(setData)
      .catch((err) => { if (err.name !== "AbortError") setError(err.message); });
    return () => controller.abort();
  }, [attempt]);

  const visible = data?.departments.filter((department) => !department.hidden) || [];
  const completers = visible.reduce((total, department) => total + department.responded, 0);

  return (
    <section>
      <div className="page-heading heading-row"><div><span className="eyebrow">ORGANIZATION OVERVIEW</span><h1>AI at work. In perspective.</h1><p className="muted">{data?.organization || "Your organization"} &middot; Department readiness</p></div><button className="button secondary" onClick={() => setAttempt(attempt + 1)}>Refresh results</button></div>
      {error && <p className="error" role="alert">{error}</p>}
      {!data ? !error && <p className="card" role="status">Loading organization results...</p> : <>
        <div className="stats-grid"><div className="stat"><span className="stat-label">Visible groups</span><strong>{visible.length}</strong><span className="fine-print">Each has at least 5 completers</span></div><div className="stat"><span className="stat-label">Completions in visible groups</span><strong>{completers}</strong><span className="fine-print">Hidden groups are excluded</span></div><div className="stat privacy-stat"><span className="stat-label">PRIVACY FIRST</span><h3>A useful view.<br />Without the small groups.</h3><span className="fine-print">Small teams are combined or hidden.</span></div></div>
        <section className="card dashboard-card"><div className="section-heading"><div><h2>Department snapshot</h2><p className="muted">Each completed person's average has equal weight.</p></div><span className="badge">1 &ndash; 5 maturity scale</span></div>
          <div className="table-scroll"><table><thead><tr><th scope="col">Department</th><th scope="col">Employees</th><th scope="col">Completed</th><th scope="col">Average</th><th scope="col">Maturity</th></tr></thead><tbody>{data.departments.map((department) => <tr key={department.department}><th scope="row">{department.department}</th>{department.hidden ? <td colSpan={4}><span className="hidden-state">Not enough responses</span></td> : <><td>{department.employees}</td><td>{department.responded}</td><td><strong>{department.average_score ?? "--"}</strong></td><td><span className="level-badge">{department.level}</span></td></>}</tr>)}</tbody></table></div>
          {!data.departments.length && <p className="muted empty-state">No departments are available yet.</p>}
          <p className="table-note">A completed diagnostic includes every assigned question. Unscored answers are excluded from averages.</p>
        </section>
        <section className="card"><span className="eyebrow">WHERE TO FOCUS</span><h2>Top risk signals</h2><p className="muted">Flag occurrences from visible groups only.</p>{data.top_risks.length ? <ul className="dashboard-risks">{data.top_risks.map(([risk, count]) => <li key={risk}><span>{risk.replaceAll("_", " ")}</span><span className="risk-count">{count}</span></li>)}</ul> : <p className="positive-note">No risk flags in the visible results.</p>}</section>
      </>}
    </section>
  );
}
