const BASE = import.meta.env?.VITE_API_URL || "http://localhost:8000";

export function getToken() {
  return localStorage.getItem("token");
}

export function setToken(token) {
  localStorage.setItem("token", token);
}

export function clearSession() {
  localStorage.removeItem("token");
  localStorage.removeItem("session");
}

export function loadSession() {
  try {
    const session = JSON.parse(localStorage.getItem("session"));
    if (getToken() && typeof session?.name === "string" && session.name && Array.isArray(session.organizations)) {
      const validOrganizations = session.organizations.every((org) => Number.isInteger(org.org_id) && typeof org.org_name === "string" && ["admin", "employee"].includes(org.role));
      const selectedOrganization = !session.org || session.organizations.some((org) => org.org_id === session.org.org_id && org.role === session.org.role);
      if (validOrganizations && selectedOrganization) return session;
    }
  } catch {
    clearSession();
  }
  clearSession();
  return null;
}

export function saveSession(session) {
  localStorage.setItem("session", JSON.stringify(session));
}

export async function api(path, options = {}) {
  let response;
  try {
    response = await fetch(BASE + path, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        ...(getToken() ? { Authorization: `Bearer ${getToken()}` } : {}),
        ...(options.headers || {}),
      },
    });
  } catch (error) {
    if (error.name === "AbortError") throw error;
    throw new Error("Could not reach AI Pulse. Check your connection and try again.");
  }
  if (response.status === 401 && getToken()) {
    clearSession();
    window.dispatchEvent(new Event("session-expired"));
  }
  if (response.status === 204) return null;
  let data;
  try {
    data = await response.json();
  } catch {
    throw new Error(`The server returned an unexpected response (${response.status}). Please try again.`);
  }
  if (!response.ok) {
    const detail = data?.detail;
    const message = Array.isArray(detail) ? detail.map((item) => item.msg).join("; ") : detail;
    throw new Error(typeof message === "string" ? message : "Request failed. Please try again.");
  }
  return data;
}
