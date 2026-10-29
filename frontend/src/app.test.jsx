import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import Badge from "./Badge.jsx";
import Diagnostic from "./pages/Diagnostic.jsx";
import Report from "./pages/Report.jsx";
import Dashboard from "./pages/Dashboard.jsx";
import App from "./App.jsx";

// Route-by-route fake backend: { "GET /path": body | (init) => body }
function mockApi(routes) {
  const calls = [];
  vi.stubGlobal("fetch", vi.fn(async (url, init = {}) => {
    const path = url.replace(/^https?:\/\/[^/]+/, "");
    const key = `${init.method || "GET"} ${path}`;
    calls.push(key);
    const hit = routes[key];
    if (hit === undefined) return { ok: false, status: 404, json: async () => ({ detail: `no mock for ${key}` }) };
    const body = typeof hit === "function" ? hit(init) : hit;
    return { ok: true, status: 200, json: async () => body };
  }));
  return calls;
}

const QUESTIONS = [
  { id: "q1", type: "mcq", text: "How often?", options: ["Daily", "Never"] },
  { id: "q2", type: "open", text: "Describe a task." },
];

describe("Badge", () => {
  it("shows the level and falls back to neutral for unknown levels", () => {
    const { rerender } = render(<Badge level="Leader" />);
    expect(screen.getByText("Leader")).toHaveClass("badge-leader");
    rerender(<Badge level="Not assessed" />);
    expect(screen.getByText("Not assessed")).toHaveClass("badge-neutral");
  });
});

describe("Diagnostic", () => {
  it("blocks submit and shows errors until every question is valid", async () => {
    const calls = mockApi({ "GET /diagnostic/questions": QUESTIONS });
    const onDone = vi.fn();
    render(<Diagnostic onDone={onDone} />);
    await screen.findByText(/How often/);

    await userEvent.click(screen.getByRole("button", { name: "Submit" }));
    expect(screen.getAllByText("This question needs an answer.")).toHaveLength(2);
    expect(calls).not.toContain("POST /diagnostic/submit");

    await userEvent.selectOptions(screen.getByRole("combobox"), "Daily");
    await userEvent.type(screen.getByRole("textbox"), "too short");
    await userEvent.click(screen.getByRole("button", { name: "Submit" }));
    expect(screen.getByText(/at least 20 characters/)).toBeInTheDocument();
    expect(onDone).not.toHaveBeenCalled();
  });

  it("submits once everything is valid", async () => {
    const calls = mockApi({
      "GET /diagnostic/questions": QUESTIONS,
      "POST /diagnostic/submit": { saved: 2 },
    });
    const onDone = vi.fn();
    render(<Diagnostic onDone={onDone} />);
    await screen.findByText(/How often/);
    await userEvent.selectOptions(screen.getByRole("combobox"), "Daily");
    await userEvent.type(screen.getByRole("textbox"), "I drafted emails with AI and checked them.");
    await userEvent.click(screen.getByRole("button", { name: "Submit" }));
    await waitFor(() => expect(onDone).toHaveBeenCalled());
    expect(calls).toContain("POST /diagnostic/submit");
  });
});

describe("Report", () => {
  const report = {
    name: "Priya", level: "Exploring", average_score: 2.5, answered: 2, risks: ["customer_data_shared"],
    remediation: [{ risk: "customer_data_shared", title: "Customer data shared", tips: ["Use placeholders"] }],
    next_steps: ["Try drafts"],
  };

  it("shows score, badge, risks and fix tips", async () => {
    mockApi({ "GET /reports/me": report });
    render(<Report onRetake={() => {}} />);
    expect(await screen.findByText("2.5")).toBeInTheDocument();
    expect(screen.getByText("Exploring")).toHaveClass("badge-exploring");
    expect(screen.getByText("customer data shared")).toBeInTheDocument();
    expect(screen.getByText("Use placeholders")).toBeInTheDocument();
  });

  it("does not delete when the confirmation is declined", async () => {
    const calls = mockApi({ "GET /reports/me": report });
    vi.spyOn(window, "confirm").mockReturnValue(false);
    render(<Report onRetake={() => {}} />);
    await userEvent.click(await screen.findByRole("button", { name: "Delete My Data" }));
    expect(calls).not.toContain("DELETE /diagnostic/me");
  });

  it("deletes after confirmation and shows the empty state", async () => {
    let deleted = false;
    const calls = mockApi({
      "GET /reports/me": () => (deleted ? { ...report, answered: 0, average_score: null, risks: [], remediation: [] } : report),
      "DELETE /diagnostic/me": () => { deleted = true; return { deleted: 2 }; },
    });
    vi.spyOn(window, "confirm").mockReturnValue(true);
    render(<Report onRetake={() => {}} />);
    await userEvent.click(await screen.findByRole("button", { name: "Delete My Data" }));
    expect(await screen.findByText(/no answers on file/i)).toBeInTheDocument();
    expect(calls).toContain("DELETE /diagnostic/me");
  });
});

describe("Dashboard", () => {
  const data = {
    organization: "Northwind",
    totals: { headcount: 10, completed: 6, average_score: 3.2, level: "Practitioner" },
    departments: [
      { department: "Sales", employees: 6, responded: 6, average_score: 3.2, level: "Practitioner", suppressed: false },
      { department: "Other teams", employees: 4, responded: 0, average_score: null, level: "Not enough responses", suppressed: true },
    ],
    top_risks: [["policy_unaware", 3]],
  };

  it("shows stats, a privacy badge for Other teams, and opens a playbook on click", async () => {
    mockApi({
      "GET /dashboard?org_id=1": data,
      "GET /playbooks/policy_unaware": {
        risk: "policy_unaware", title: "Unaware of policy", summary: "s",
        guardrails: ["Publish a policy"], approved_tooling: ["List tools"], team_guidance: ["Walk through it"],
      },
    });
    render(<Dashboard org={{ org_id: 1 }} />);
    expect(await screen.findByText("Total headcount")).toBeInTheDocument();
    expect(screen.getByText("Privacy-protected")).toBeInTheDocument();
    expect(screen.getByText("Not enough responses")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: /policy unaware/ }));
    expect(await screen.findByText("Publish a policy")).toBeInTheDocument();
  });
});

describe("App session", () => {
  beforeEach(() => localStorage.clear());

  it("shows the login screen when there is no saved session", async () => {
    mockApi({});
    render(<App />);
    expect(await screen.findByRole("heading", { name: "Sign in" })).toBeInTheDocument();
  });

  it("restores an admin straight to the dashboard after a refresh", async () => {
    localStorage.setItem("token", "t");
    localStorage.setItem("session", JSON.stringify({
      session: { name: "Asha", organizations: [{ org_id: 1, org_name: "Northwind", role: "admin" }] },
      org: { org_id: 1, org_name: "Northwind", role: "admin" },
    }));
    mockApi({
      "GET /reports/me": { answered: 0 },
      "GET /dashboard?org_id=1": {
        organization: "Northwind", totals: { headcount: 1, completed: 0, average_score: null, level: "Not assessed" },
        departments: [], top_risks: [],
      },
    });
    render(<App />);
    expect(await screen.findByText("Total headcount")).toBeInTheDocument();
    expect(screen.getByText("Asha")).toBeInTheDocument();
  });

  it("falls back to login when the saved token is no longer valid", async () => {
    localStorage.setItem("token", "expired");
    localStorage.setItem("session", JSON.stringify({
      session: { name: "Asha", organizations: [] },
      org: { org_id: 1, org_name: "Northwind", role: "admin" },
    }));
    mockApi({}); // every call 404s, which the app treats as a failed session check
    render(<App />);
    expect(await screen.findByRole("heading", { name: "Sign in" })).toBeInTheDocument();
    expect(localStorage.getItem("session")).toBeNull();
  });

  it("sends an employee who already answered to their report", async () => {
    localStorage.setItem("token", "t");
    localStorage.setItem("session", JSON.stringify({
      session: { name: "Priya", organizations: [{ org_id: 1, org_name: "Northwind", role: "employee" }] },
      org: { org_id: 1, org_name: "Northwind", role: "employee" },
    }));
    mockApi({
      "GET /reports/me": {
        name: "Priya", level: "Exploring", average_score: 2.5, answered: 2, risks: [], remediation: [], next_steps: [],
      },
    });
    render(<App />);
    expect(await screen.findByRole("button", { name: "Retake diagnostic" })).toBeInTheDocument();
  });
});
