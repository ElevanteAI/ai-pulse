import React, { useState } from "react";
import { api, setToken } from "../api.js";

export default function Login({ onDone }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function submit(e) {
    if (e) e.preventDefault();
    if (!email || !password) {
      setError("Please enter both email and password.");
      return;
    }
    setLoading(true);
    setError("");
    try {
      const data = await api("/auth/login", {
        method: "POST",
        body: JSON.stringify({ email, password }),
      });
      setToken(data.token);
      onDone(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  function fillDemo(demoEmail) {
    setEmail(demoEmail);
    setPassword("pulse123");
    setError("");
  }

  return (
    <div className="card">
      <h2 className="card-title">Sign in to AI Pulse</h2>
      <p className="card-subtitle">
        Enter your enterprise credentials to access your diagnostic or organization dashboard.
      </p>

      {error && <div className="error-banner">{error}</div>}

      <form onSubmit={submit}>
        <label>
          Work Email
          <input
            type="email"
            placeholder="name@company.com"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
        </label>

        <label>
          Password
          <input
            type="password"
            placeholder="••••••••"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
        </label>

        <button type="submit" disabled={loading} style={{ width: "100%", marginTop: "8px" }}>
          {loading ? "Authenticating…" : "Sign In"}
        </button>
      </form>

      <div className="demo-hints">
        <span style={{ fontSize: "0.78rem", color: "var(--text-muted)" }}>Demo Accounts (Click to fill):</span>
        <span className="demo-chip" onClick={() => fillDemo("priya@northwind.test")}>
          priya@northwind (Support)
        </span>
        <span className="demo-chip" onClick={() => fillDemo("dev@northwind.test")}>
          dev@northwind (Eng Lead)
        </span>
        <span className="demo-chip" onClick={() => fillDemo("asha@northwind.test")}>
          asha@northwind (HR Admin)
        </span>
        <span className="demo-chip" onClick={() => fillDemo("ravi@consult.test")}>
          ravi@consult (Multi-org)
        </span>
      </div>
    </div>
  );
}
