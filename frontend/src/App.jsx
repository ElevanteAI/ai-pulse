import React, { useState } from "react";
import Login from "./pages/Login.jsx";
import OrgPicker from "./pages/OrgPicker.jsx";
import Diagnostic from "./pages/Diagnostic.jsx";
import Report from "./pages/Report.jsx";
import Dashboard from "./pages/Dashboard.jsx";
import { setToken } from "./api.js";

export default function App() {
  const [step, setStep] = useState("login");
  const [session, setSession] = useState(null);
  const [org, setOrg] = useState(null);

  function logout() {
    setToken(null);
    setOrg(null);
    setSession(null);
    setStep("login");
  }

  return (
    <div className="wrap">
      <header className="app-header">
        <div><p className="eyebrow">ELEVANTE AI</p><h1>AI Pulse</h1>{org && <p className="muted">{org.org_name}</p>}</div>
        {step !== "login" && <nav className="app-actions">
          {step !== "org" && <button className="secondary" onClick={() => setStep("org")}>Back</button>}
          <button className="secondary" onClick={logout}>Log out</button>
        </nav>}
      </header>
      {step === "login" && (
        <Login onDone={(s) => { setSession(s); setStep("org"); }} />
      )}
      {step === "org" && (
        <OrgPicker
          orgs={session.organizations}
          onPick={(o) => { setOrg(o); setStep(o.role === "admin" ? "dashboard" : "diagnostic"); }}
        />
      )}
      {step === "diagnostic" && <Diagnostic onDone={() => setStep("report")} />}
      {step === "report" && <Report />}
      {step === "dashboard" && <Dashboard org={org} />}
    </div>
  );
}
