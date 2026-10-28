const BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

// Token lives in localStorage for this pilot. See docs/SECURITY_AUDIT.md (V21) for the trade-off.
export function getToken() {
  return localStorage.getItem("token");
}

export function setToken(t) {
  if (t) localStorage.setItem("token", t);
  else localStorage.removeItem("token");
}

export async function api(path, options = {}) {
  const res = await fetch(BASE + path, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(getToken() ? { Authorization: `Bearer ${getToken()}` } : {}),
      ...(options.headers || {}),
    },
  });
  let data = null;
  try {
    data = await res.json();
  } catch {
    // non-JSON body (e.g. a proxy error page)
  }
  if (!res.ok) throw new Error(errorMessage(data, res.status));
  return data;
}

function errorMessage(data, status) {
  const detail = data && data.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) return detail.map((d) => d.msg).join("; "); // FastAPI validation errors
  return `Request failed (${status})`;
}

export const RISK_LABELS = {
  customer_data_shared: "Customer data shared with AI tools",
  confidential_data_shared: "Confidential data shared with AI tools",
  unreviewed_output: "AI output used without review",
  policy_unaware: "Unaware of AI policy",
};
