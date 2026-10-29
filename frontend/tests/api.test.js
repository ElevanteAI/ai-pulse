import assert from "node:assert/strict";
import { beforeEach, test } from "node:test";
import { api, clearSession, getToken, loadSession, saveSession, setToken } from "../src/api.js";

beforeEach(() => {
  const values = new Map();
  Object.defineProperty(globalThis, "localStorage", { configurable: true, value: {
    getItem: (key) => values.get(key) ?? null,
    setItem: (key, value) => values.set(key, value),
    removeItem: (key) => values.delete(key),
  } });
  globalThis.window = new EventTarget();
});

test("API attaches the selected token and parses JSON", async () => {
  setToken("selected-token");
  globalThis.fetch = async (url, options) => {
    assert.equal(url, "http://localhost:8000/dashboard");
    assert.equal(options.headers.Authorization, "Bearer selected-token");
    return Response.json({ organization: "Northwind Logistics" });
  };
  assert.deepEqual(await api("/dashboard"), { organization: "Northwind Logistics" });
});

test("non-JSON server errors produce a readable error", async () => {
  globalThis.fetch = async () => new Response("Bad gateway", { status: 502 });
  await assert.rejects(api("/dashboard"), /unexpected response \(502\)/);
});

test("401 clears the session and notifies the application", async () => {
  setToken("expired-token");
  saveSession({ name: "Test" });
  let expired = false;
  window.addEventListener("session-expired", () => { expired = true; });
  globalThis.fetch = async () => Response.json({ detail: "Invalid token" }, { status: 401 });
  await assert.rejects(api("/reports/me"), /Invalid token/);
  assert.equal(getToken(), null);
  assert.equal(localStorage.getItem("session"), null);
  assert.equal(expired, true);
});

test("non-JSON 401 also clears the session", async () => {
  setToken("expired-token");
  globalThis.fetch = async () => new Response("Unauthorized", { status: 401 });
  await assert.rejects(api("/reports/me"), /unexpected response/);
  assert.equal(getToken(), null);
});

test("validation errors become readable text", async () => {
  globalThis.fetch = async () => Response.json({ detail: [{ msg: "Field required" }] }, { status: 422 });
  await assert.rejects(api("/auth/login"), /Field required/);
});

test("network errors get a useful message", async () => {
  globalThis.fetch = async () => { throw new TypeError("Network unavailable"); };
  await assert.rejects(api("/health"), /Could not reach AI Pulse/);
});

test("aborted requests retain their abort identity", async () => {
  globalThis.fetch = async () => { throw new DOMException("Aborted", "AbortError"); };
  await assert.rejects(api("/health"), { name: "AbortError" });
});

test("session survives refresh and logout removes it", () => {
  const org = { org_id: 1, org_name: "Northwind Logistics", role: "employee" };
  const session = { name: "Test", organizations: [org], org };
  setToken("token");
  saveSession(session);
  assert.deepEqual(loadSession(), session);
  clearSession();
  assert.equal(loadSession(), null);
});

test("corrupt session data does not crash the app", () => {
  setToken("token");
  localStorage.setItem("session", "{broken");
  assert.equal(loadSession(), null);
  assert.equal(getToken(), null);
});

test("invalid stored organization does not restore a session", () => {
  setToken("token");
  saveSession({ name: "Test", organizations: [], org: { org_id: 999, role: "admin" } });
  assert.equal(loadSession(), null);
});

test("empty successful responses are supported", async () => {
  globalThis.fetch = async () => new Response(null, { status: 204 });
  assert.equal(await api("/reports/me", { method: "DELETE" }), null);
});
