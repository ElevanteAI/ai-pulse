import React, { useState } from "react";
import { api, setToken } from "../api.js";

export default function OrgPicker({ orgs, onPick }) {
  const [busy, setBusy] = useState(null);
  const [error, setError] = useState("");

  async function pick(org) {
    setBusy(org.org_id);
    setError("");
    try {
      const data = await api("/auth/select-org", { method: "POST", body: JSON.stringify({ org_id: org.org_id }) });
      setToken(data.token);
      onPick(org);
    } catch (err) {
      setError(err.message);
      setBusy(null);
    }
  }

  return (
    <section className="narrow">
      <div className="page-heading"><span className="eyebrow">ONE ACCOUNT, YOUR WORKSPACES</span><h1>Where are you working?</h1><p className="muted">Choose an organization to continue.</p></div>
      {error && <p className="error" role="alert">{error}</p>}
      <div className="org-list">
        {orgs.map((org) => <button className="org-card" key={org.org_id} onClick={() => pick(org)} disabled={busy !== null}>
          <span className="org-avatar" aria-hidden="true">{org.org_name.slice(0, 1)}</span>
          <span><strong>{org.org_name}</strong><span className="org-role">{org.role === "admin" ? "Administrator workspace" : "Employee workspace"}</span></span>
          <span className="org-arrow" aria-hidden="true">{busy === org.org_id ? "..." : "\u2192"}</span>
        </button>)}
      </div>
      {!orgs.length && <p className="notice">No organization memberships found. Contact your administrator.</p>}
    </section>
  );
}
