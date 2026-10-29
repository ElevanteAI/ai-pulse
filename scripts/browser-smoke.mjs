import assert from "node:assert/strict";
import { spawn, spawnSync } from "node:child_process";
import { existsSync, mkdtempSync, writeFileSync } from "node:fs";
import { createServer } from "node:net";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const directory = mkdtempSync(join(tmpdir(), "ai-pulse-smoke-"));
const chrome = process.env.CHROME_PATH || "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
assert.ok(existsSync(chrome), "Set CHROME_PATH to a Chrome or Chromium executable");
const children = [];
let socket;
const delay = (ms) => new Promise((done) => setTimeout(done, ms));

async function waitFor(check, message) {
  for (let attempt = 0; attempt < 150; attempt++) {
    try {
      const value = await check();
      if (value) return value;
    } catch {}
    await delay(100);
  }
  throw new Error(message);
}

async function requireFreePort(port) {
  await new Promise((done, reject) => {
    const server = createServer();
    server.once("error", reject);
    server.listen(port, "127.0.0.1", () => server.close(done));
  });
}

function start(executable, args, options = {}) {
  const child = spawn(executable, args, { windowsHide: true, stdio: "ignore", ...options });
  children.push(child);
  return child;
}

try {
  for (const port of [8000, 5173, 9223]) await requireFreePort(port);
  const env = { ...process.env, PYTHONPATH: join(root, "backend"), DEV_MODE: "true", DATABASE_URL: "sqlite:///./test.db", AI_MODE: "mock", SECRET_KEY: "local-smoke-test-secret-that-is-not-for-production" };
  const python = process.env.PYTHON || "python";
  const seeded = spawnSync(python, ["-m", "app.seed"], { cwd: directory, env, windowsHide: true, encoding: "utf8", timeout: 60000 });
  assert.equal(seeded.status, 0, seeded.stderr);
  start(python, ["-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000"], { cwd: directory, env });
  start(process.execPath, [join(root, "frontend/node_modules/vite/bin/vite.js"), "preview", "--host", "127.0.0.1", "--port", "5173", "--strictPort"], { cwd: join(root, "frontend") });
  start(chrome, ["--headless=new", "--disable-gpu", "--no-first-run", "--no-default-browser-check", "--remote-debugging-port=9223", `--user-data-dir=${join(directory, "chrome")}`, "about:blank"]);
  await waitFor(async () => (await fetch("http://127.0.0.1:8000/health")).ok, "Backend did not start");
  await waitFor(async () => (await fetch("http://localhost:5173")).ok, "Frontend did not start");
  const targets = await waitFor(async () => (await fetch("http://127.0.0.1:9223/json/list")).json(), "Chrome did not start");
  const target = targets.find((item) => item.type === "page");
  socket = new WebSocket(target.webSocketDebuggerUrl);
  await new Promise((done, reject) => { socket.addEventListener("open", done, { once: true }); socket.addEventListener("error", reject, { once: true }); });
  const pending = new Map();
  let nextId = 0;
  socket.addEventListener("message", (event) => {
    const message = JSON.parse(event.data);
    if (pending.has(message.id)) {
      const { done, reject } = pending.get(message.id);
      pending.delete(message.id);
      if (message.error) reject(new Error(message.error.message));
      else done(message.result);
    }
  });
  function command(method, params = {}) {
    return new Promise((done, reject) => {
      const id = ++nextId;
      pending.set(id, { done, reject });
      socket.send(JSON.stringify({ id, method, params }));
    });
  }
  async function evaluate(expression) {
    const result = await command("Runtime.evaluate", { expression, returnByValue: true, awaitPromise: true });
    if (result.exceptionDetails) throw new Error(result.exceptionDetails.text);
    return result.result.value;
  }
  const text = () => evaluate("document.body.innerText");
  const see = (value) => waitFor(async () => (await text()).includes(value), `Missing screen text: ${value}`);
  async function click(label) {
    const clicked = await evaluate(`(() => { const button = [...document.querySelectorAll('button')].find(item => item.textContent.trim().startsWith(${JSON.stringify(label)})); if (!button) return false; button.click(); return true; })()`);
    assert.ok(clicked, `Missing button: ${label}`);
  }
  async function login(email) {
    await see("Welcome back");
    await evaluate(`(() => { for (const [id,value] of [['email',${JSON.stringify(email)}],['password','pulse123']]) { const input=document.getElementById(id); Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set.call(input,value); input.dispatchEvent(new Event('input',{bubbles:true})); } })()`);
    await click("Sign in");
    await see("Where are you working?");
    await evaluate("document.querySelector('.org-card').click()");
  }
  async function screenshot(name) {
    const { data } = await command("Page.captureScreenshot", { format: "png" });
    const path = join(directory, name);
    writeFileSync(path, Buffer.from(data, "base64"));
    console.log(`Screenshot: ${path}`);
  }
  await command("Emulation.setDeviceMetricsOverride", { width: 1440, height: 1000, deviceScaleFactor: 1, mobile: false });
  await command("Page.navigate", { url: "http://localhost:5173" });
  await see("Welcome back");
  await screenshot("login.png");
  await login("asha@northwind.test");
  await see("Department snapshot");
  assert.ok((await text()).includes("Sales"));
  assert.ok((await text()).includes("Not enough responses"));
  assert.ok(!(await text()).includes("Support"));
  await screenshot("dashboard.png");
  await click("Log out");
  await login("neha@northwind.test");
  await see("0 of 6 answered");
  await click("View my report");
  assert.equal(await evaluate("document.querySelectorAll('.question-card').length"), 6);
  await evaluate("(() => { for (const select of document.querySelectorAll('select')) { const value=select.options[1].value; Object.getOwnPropertyDescriptor(HTMLSelectElement.prototype,'value').set.call(select,value); select.dispatchEvent(new Event('change',{bubbles:true})); } for (const input of document.querySelectorAll('textarea')) { Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype,'value').set.call(input,'I used AI to draft a fictional email and reviewed its facts.'); input.dispatchEvent(new Event('input',{bubbles:true})); } })()");
  await see("6 of 6 answered");
  await click("View my report");
  await see("Your next three steps");
  await waitFor(async () => await evaluate("document.querySelectorAll('.suggestion-list li').length === 3"), "Suggestions did not load");
  await screenshot("report.png");
  await command("Page.reload");
  await see("Your next three steps");
  await click("Delete my data");
  await see("Delete your diagnostic?");
  await click("Keep my data");
  assert.equal(await evaluate("document.querySelector('[role=dialog]') === null"), true);
  await click("Delete my data");
  await click("Yes, delete my data");
  await see("A fresh start");
  assert.ok(!(await text()).includes("Your next three steps"));
  await click("Log out");
  await login("asha@northwind.test");
  await see("Department snapshot");
  assert.ok(!(await text()).includes("Sales"));
  await command("Emulation.setDeviceMetricsOverride", { width: 390, height: 844, deviceScaleFactor: 1, mobile: true });
  assert.ok(await evaluate("document.documentElement.scrollWidth <= window.innerWidth"));
  await screenshot("dashboard-mobile.png");
  await evaluate("localStorage.setItem('token','invalid-token')");
  await click("Refresh results");
  await see("Your session ended. Please sign in again.");
  console.log("Browser smoke passed: login, privacy, validation, submit, suggestions, refresh, deletion, logout, responsive layout and 401 expiry.");
} finally {
  socket?.close();
  for (const child of children.reverse()) child.kill();
}
