import React, { useState } from "react";
import { api, setToken } from "../api.js";

export default function Login({ onDone, notice }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(event) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const data = await api("/auth/login", { method: "POST", body: JSON.stringify({ email, password }) });
      setToken(data.token);
      onDone(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="login-layout">
      <section className="login-intro">
        <span className="eyebrow">A CLEARER PICTURE OF AI AT WORK</span>
        <h1>Small habits.<br />Better <span className="accent">AI outcomes.</span></h1>
        <p className="lead">Understand how you use AI today. Find a practical next step for tomorrow.</p>
        <div className="intro-note"><span className="status-dot" /> Built around people, with privacy in mind.</div>
      </section>
      <form className="card login-card" onSubmit={submit}>
        <span className="eyebrow">YOUR WORKSPACE</span>
        <h2>Welcome back</h2>
        <p className="muted">Sign in to your AI Pulse account.</p>
        {notice && <p className="notice" role="status">{notice}</p>}
        <label htmlFor="email">Work email</label>
        <input id="email" type="email" autoComplete="username" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@company.com" required disabled={busy} />
        <label htmlFor="password">Password</label>
        <input id="password" type="password" autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)} required disabled={busy} />
        {error && <p className="error" role="alert">{error}</p>}
        <button className="button full" disabled={busy}>{busy ? "Signing in..." : "Sign in"}<span aria-hidden="true"> &rarr;</span></button>
        <p className="fine-print">Your diagnostic belongs to you. You can delete your answers at any time.</p>
      </form>
    </div>
  );
}
