// All backend calls live in this one file. They follow API_CONTRACT.md (repository root).
// The backend address comes from the .env file (VITE_API_URL).
export const BASE = (import.meta.env && import.meta.env.VITE_API_URL) || "http://127.0.0.1:8000";

const store = typeof localStorage !== "undefined" ? localStorage : null;
const TOKEN_KEY = "cg_admin_token";

export const getToken = () => (store ? store.getItem(TOKEN_KEY) : null);
export const setToken = (t) => store && store.setItem(TOKEN_KEY, t);
export const clearToken = () => store && store.removeItem(TOKEN_KEY);

// Turns FastAPI's {"detail": ...} into one readable sentence.
export function formatDetail(data) {
  if (!data || !data.detail) return "";
  if (typeof data.detail === "string") return data.detail;
  if (Array.isArray(data.detail)) {
    return data.detail.map((d) => `${(d.loc || []).slice(1).join(".")}: ${d.msg}`).join("; ");
  }
  return JSON.stringify(data.detail);
}

// Builds "?a=1&b=2", leaving out empty values.
export function query(params = {}) {
  const parts = Object.entries(params)
    .filter(([, v]) => v !== undefined && v !== null && v !== "" && v !== "all")
    .map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(v)}`);
  return parts.length ? `?${parts.join("&")}` : "";
}

async function request(path, { method = "GET", body, auth = true } = {}) {
  const headers = { "Content-Type": "application/json" };
  if (auth) {
    const t = getToken();
    if (t) headers.Authorization = `Bearer ${t}`;
  }

  let res;
  try {
    res = await fetch(BASE + path, {
      method,
      headers,
      body: body ? JSON.stringify(body) : undefined,
    });
  } catch {
    throw new Error(`Cannot reach the backend at ${BASE}. Is it running?`);
  }

  let data = null;
  try {
    data = await res.json();
  } catch {
    /* empty body */
  }

  if (!res.ok) {
    if (res.status === 401 && auth) {
      clearToken();
      if (typeof window !== "undefined") window.location.hash = "#/login";
    }
    throw new Error(formatDetail(data) || `Request failed (${res.status})`);
  }
  return data;
}

// ---- auth ----
export const login = (email, password) =>
  request("/auth/login", { method: "POST", body: { email, password }, auth: false });
export const me = () => request("/auth/me");

// ---- statistics ----
export const getStats = () => request("/admin/stats");
export const getReports = () => request("/admin/reports");

// ---- submissions ----
// params: { status, activity_type, search, skip, limit }
export const listSubmissions = (params) => request("/admin/submissions" + query(params));
export const getSubmission = (id) => request(`/admin/submissions/${id}`);
const review = (action) => (id, notes) =>
  request(`/admin/submissions/${id}/${action}`, { method: "POST", body: { notes: notes || null } });
export const approve = review("approve");
export const reject = review("reject");
export const sendToManualReview = review("manual-review");

// ---- users ----
export const listUsers = (params) => request("/admin/users" + query(params));
export const getUser = (id) => request(`/admin/users/${id}`);
export const setUserActive = (id, isActive) =>
  request(`/admin/users/${id}`, { method: "PATCH", body: { is_active: isActive } });

// ---- logs ----
export const getFraudFlags = (params) => request("/admin/fraud-flags" + query(params));
export const getAuditLogs = (params) => request("/admin/audit-logs" + query(params));

// ---- rules and settings ----
export const getCreditRules = () => request("/admin/credit-rules");
export const updateCreditRule = (type, rule) =>
  request(`/admin/credit-rules/${type}`, { method: "PUT", body: rule });
export const getConfig = () => request("/admin/config");
export const updateConfig = (changes) => request("/admin/config", { method: "PUT", body: changes });

// Full URL for an image path such as "/uploads/abc.jpg".
export const fileUrl = (path) => (path ? BASE + path : "");
