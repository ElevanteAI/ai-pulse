import React, { useEffect, useState } from "react";
import { api, getToken, setToken } from "./api.js";
import Login from "./pages/Login.jsx";
import OrgPicker from "./pages/OrgPicker.jsx";
import Diagnostic from "./pages/Diagnostic.jsx";
import Report from "./pages/Report.jsx";
import Dashboard from "./pages/Dashboard.jsx";

const SAVED = "session";

function loadSaved() {
  try {
    return JSON.parse(localStorage.getItem(SAVED));
  } catch {
    return null;
  }
}

function save(session, org) {
  try {
    localStorage.setItem(SAVED, JSON.stringify({ session, org }));
  } catch {
    // storage unavailable: the user just signs in again after a refresh
  }
}

export default function App() {
  const [step, setStep] = useState("starting");
  const [session, setSession] = useState(null);
  const [org, setOrg] = useState(null);

  async function enterOrg(o, s = session) {
    setOrg(o);
    save(s, o);
    if (o.role === "admin") return setStep("dashboard");
    // Employees who already submitted go straight to their report
    try {
      const report = await api("/reports/me");
      setStep(report.answered > 0 ? "report" : "diagnostic");
    } catch {
      setStep("diagnostic");
    }
  }

  // After a page refresh, pick up where the user was if their token is still valid
  useEffect(() => {
    const saved = loadSaved();
    if (!saved || !getToken()) return setStep("login");
    setSession(saved.session);
    if (!saved.org) return setStep("org");
    // /reports/me needs a valid org-scoped token, so it doubles as the "still signed in?" check
    api("/reports/me")
      .then(() => enterOrg(saved.org, saved.session))
      .catch(() => { signOut(); });
  }, []);

  function signOut() {
    setToken("");
    try {
      localStorage.removeItem(SAVED);
    } catch {
      // nothing to clear
    }
    setSession(null);
    setOrg(null);
    setStep("login");
  }

  const signedIn = step !== "login" && step !== "starting";

  return (
    <>
      {signedIn && (
        <header className="nav">
          <strong>AI Pulse</strong>
          <div className="nav-info">
            <span>{session.name}</span>
            {org && <span>{org.org_name}</span>}
            {org && <span className="badge badge-role">{org.role}</span>}
          </div>
          <div className="nav-actions">
            {session.organizations.length > 1 && (
              <button className="secondary" onClick={() => { setOrg(null); save(session, null); setStep("org"); }}>Switch Organization</button>
            )}
            <button className="secondary" onClick={signOut}>Sign Out</button>
          </div>
        </header>
      )}
      <div className="wrap">
        {!signedIn && <h1>AI Pulse</h1>}
        {step === "starting" && <p>Loading...</p>}
        {step === "login" && (
          <Login onDone={(s) => { setSession(s); save(s, null); setStep("org"); }} />
        )}
        {step === "org" && <OrgPicker orgs={session.organizations} onPick={(o) => enterOrg(o)} />}
        {step === "diagnostic" && <Diagnostic onDone={() => setStep("report")} />}
        {step === "report" && <Report onRetake={() => setStep("diagnostic")} />}
        {step === "dashboard" && <Dashboard org={org} />}
      </div>
    </>
  );
}
