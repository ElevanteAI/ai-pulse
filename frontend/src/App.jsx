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

  function handleLoginDone(userSession) {
    setSession(userSession);
    setStep("org");
  }

  function handleBack() {
    if (step === "org") {
      logout();
    } else if (step === "diagnostic") {
      setStep("org");
    } else if (step === "report") {
      setStep(session?.organizations?.length > 1 ? "org" : "diagnostic");
    } else if (step === "dashboard") {
      setStep("org");
    }
  }

  return (
    <div className="wrap">
      <header className="app-header">
        <div className="brand-group">
          <div className="brand-icon" title="AI Pulse Diagnostic Platform">
            <svg
              width="20"
              height="20"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2.2"
              strokeLinecap="round"
              strokeLinejoin="round"
              aria-hidden="true"
            >
              <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
            </svg>
          </div>
          <div className="brand-meta">
            <p className="brand-eyebrow">ELEVANTE AI</p>
            <h1>AI Pulse</h1>
          </div>
        </div>

        {org && step !== "login" && step !== "org" && (
          <div className="org-pill">
            <span>🏢</span>
            <span>{org.org_name}</span>
            <strong>• {org.role.toUpperCase()}</strong>
          </div>
        )}

        {step !== "login" && (
          <nav className="app-actions">
            <button className="back-btn" onClick={handleBack} title="Go back to previous screen">
              ← Back
            </button>
            <button className="secondary" onClick={logout}>
              Log out
            </button>
          </nav>
        )}
      </header>

      {step === "login" && <Login onDone={handleLoginDone} />}

      {step === "org" && (
        <OrgPicker
          orgs={session?.organizations || []}
          onBack={logout}
          onPick={(o) => {
            setOrg(o);
            setStep(o.role === "admin" ? "dashboard" : "diagnostic");
          }}
        />
      )}

      {step === "diagnostic" && (
        <Diagnostic onBack={() => setStep("org")} onDone={() => setStep("report")} />
      )}

      {step === "report" && (
        <Report onBack={() => setStep(session?.organizations?.length > 1 ? "org" : "diagnostic")} />
      )}

      {step === "dashboard" && (
        <Dashboard org={org} onBack={() => setStep("org")} />
      )}
    </div>
  );
}
