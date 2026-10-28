import React, { useState } from "react";
import { setToken } from "./api.js";
import Login from "./pages/Login.jsx";
import OrgPicker from "./pages/OrgPicker.jsx";
import Diagnostic from "./pages/Diagnostic.jsx";
import Report from "./pages/Report.jsx";
import Dashboard from "./pages/Dashboard.jsx";

export default function App() {
  const [step, setStep] = useState("login");
  const [session, setSession] = useState(null);
  const [org, setOrg] = useState(null);

  function signOut() {
    setToken(null);
    setSession(null);
    setOrg(null);
    setStep("login");
  }

  const isAdmin = org && org.role === "admin";

  return (
    <div className="wrap">
      <header>
        <h1>AI Pulse</h1>
        {session && (
          <nav>
            {org && <span className="muted">{session.name} · {org.org_name}</span>}
            {isAdmin && step !== "dashboard" && <button className="link" onClick={() => setStep("dashboard")}>Dashboard</button>}
            {isAdmin && step === "dashboard" && <button className="link" onClick={() => setStep("report")}>My report</button>}
            {session.organizations.length > 1 && org && <button className="link" onClick={() => setStep("org")}>Switch org</button>}
            <button className="link" onClick={signOut}>Sign out</button>
          </nav>
        )}
      </header>
      {step === "login" && (
        <Login onDone={(s) => { setSession(s); setStep("org"); }} />
      )}
      {step === "org" && (
        <OrgPicker
          orgs={session.organizations}
          onPick={(o) => { setOrg(o); setStep(o.role === "admin" ? "dashboard" : "report"); }}
        />
      )}
      {step === "diagnostic" && <Diagnostic onDone={() => setStep("report")} />}
      {step === "report" && <Report key={org.org_id} onTake={() => setStep("diagnostic")} />}
      {step === "dashboard" && <Dashboard key={org.org_id} />}
    </div>
  );
}
