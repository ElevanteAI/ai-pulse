import React, { useEffect, useState } from "react";
import { clearSession, loadSession, saveSession } from "./api.js";
import Login from "./pages/Login.jsx";
import OrgPicker from "./pages/OrgPicker.jsx";
import Diagnostic from "./pages/Diagnostic.jsx";
import Report from "./pages/Report.jsx";
import Dashboard from "./pages/Dashboard.jsx";

export default function App() {
  const [session, setSession] = useState(loadSession);
  const [page, setPage] = useState(() => {
    const saved = loadSession();
    return saved?.org ? (saved.org.role === "admin" ? "dashboard" : "report") : "org";
  });
  const [notice, setNotice] = useState("");

  function logout() {
    clearSession();
    setSession(null);
    setPage("org");
  }

  useEffect(() => {
    function expired() {
      logout();
      setNotice("Your session ended. Please sign in again.");
    }
    window.addEventListener("session-expired", expired);
    return () => window.removeEventListener("session-expired", expired);
  }, []);

  function signIn(data) {
    const next = { name: data.name, organizations: data.organizations, org: null };
    saveSession(next);
    setSession(next);
    setNotice("");
    setPage("org");
  }

  function selectOrg(org) {
    const next = { ...session, org };
    saveSession(next);
    setSession(next);
    setPage(org.role === "admin" ? "dashboard" : "diagnostic");
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <a className="brand" href="/" aria-label="AI Pulse home"><span className="brand-mark">a<span>i</span></span> pulse<span className="brand-dot">.</span></a>
        <div className="header-actions">
          <span className="workspace-label">{session?.org?.org_name || "Workplace AI readiness"}</span>
          {session && <button className="button secondary small" onClick={logout}>Log out</button>}
        </div>
      </header>
      <main className="wrap">
        {!session ? <Login onDone={signIn} notice={notice} /> : (
          <>
            {session.org && <nav className="navigation" aria-label="Workspace navigation">
              <button className="text-button" onClick={() => setPage("org")}>Switch organization</button>
              {session.org.role === "employee" && <div className="tabs">
                <button className={page === "diagnostic" ? "tab active" : "tab"} onClick={() => setPage("diagnostic")}>Diagnostic</button>
                <button className={page === "report" ? "tab active" : "tab"} onClick={() => setPage("report")}>My report</button>
              </div>}
              <span className="muted">Hello, {session.name.split(" ")[0]}</span>
            </nav>}
            {page === "org" && <OrgPicker orgs={session.organizations} onPick={selectOrg} />}
            {page === "diagnostic" && <Diagnostic key={session.org.org_id} onDone={() => setPage("report")} />}
            {page === "report" && <Report key={session.org.org_id} onStart={() => setPage("diagnostic")} />}
            {page === "dashboard" && <Dashboard key={session.org.org_id} />}
          </>
        )}
      </main>
      <footer className="footer"><span>AI PULSE</span> Better habits. Thoughtful AI.</footer>
    </div>
  );
}
