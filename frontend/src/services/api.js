// All communication with the FastAPI backend goes through this module.
import axios from "axios";

const TOKEN_KEY = "agentforge_token";

export const http = axios.create({
  baseURL: import.meta.env.VITE_API_URL || "",
  timeout: 60000,
});

export function getToken() {
  try {
    return localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

export function setToken(token) {
  try {
    if (token) localStorage.setItem(TOKEN_KEY, token);
    else localStorage.removeItem(TOKEN_KEY);
  } catch {
    /* storage unavailable (private mode) — token lives only for this page */
  }
}

http.interceptors.request.use((config) => {
  const token = getToken();
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

http.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) window.dispatchEvent(new Event("agentforge:unauthorized"));
    return Promise.reject(error);
  },
);

/** Turn any API/network error into a human-readable message. */
export function errorMessage(error) {
  const apiError = error?.response?.data?.error;
  if (apiError?.details?.length) {
    const first = apiError.details[0];
    return `${apiError.message} ${first.loc?.slice(1).join(".") || ""}: ${first.msg}`.trim();
  }
  if (apiError?.message) return apiError.message;
  if (error?.code === "ERR_NETWORK") return "Cannot reach the AgentForge API. Is the backend running?";
  return error?.message || "Request failed";
}

const data = (promise) => promise.then((response) => response.data);

async function saveBlob(url, fallbackName) {
  const response = await http.get(url, { responseType: "blob" });
  const disposition = response.headers["content-disposition"] || "";
  const match = disposition.match(/filename="?([^"]+)"?/);
  const link = document.createElement("a");
  link.href = URL.createObjectURL(response.data);
  link.download = match?.[1] || fallbackName;
  document.body.appendChild(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(link.href), 1000);
}

export const Api = {
  // system & auth
  systemStatus: () => data(http.get("/api/system/status")),
  me: () => data(http.get("/api/auth/me")),
  login: (email, password) => data(http.post("/api/auth/login", { email, password })),
  register: (name, email, password) => data(http.post("/api/auth/register", { name, email, password })),

  // projects & requirements
  listProjects: (params) => data(http.get("/api/projects", { params })),
  getProject: (id) => data(http.get(`/api/projects/${id}`)),
  createProject: (body) => data(http.post("/api/projects", body)),
  updateProject: (id, body) => data(http.put(`/api/projects/${id}`, body)),
  deleteProject: (id) => http.delete(`/api/projects/${id}`),
  listRequirements: (projectId) => data(http.get(`/api/projects/${projectId}/requirements`)),
  addRequirement: (projectId, text) =>
    data(http.post(`/api/projects/${projectId}/requirements`, { raw_requirement: text })),
  updateRequirement: (id, body) => data(http.put(`/api/requirements/${id}`, body)),

  // executions
  execute: (projectId, requirementId) =>
    data(http.post(`/api/projects/${projectId}/execute`, requirementId ? { requirement_id: requirementId } : {})),
  listExecutions: (params) => data(http.get("/api/executions", { params })),
  getExecution: (id) => data(http.get(`/api/executions/${id}`)),
  agentRuns: (id) => data(http.get(`/api/executions/${id}/agents`)),
  logs: (id, afterId = 0) => data(http.get(`/api/executions/${id}/logs`, { params: { after_id: afterId } })),
  tests: (id) => data(http.get(`/api/executions/${id}/tests`)),
  workflow: (id) => data(http.get(`/api/executions/${id}/workflow`)),
  cancel: (id) => data(http.post(`/api/executions/${id}/cancel`)),
  downloadPackage: (id) => saveBlob(`/api/executions/${id}/package`, `delivery-${id}.zip`),

  // approvals
  approvals: (params) => data(http.get("/api/approvals", { params })),
  approve: (id, feedback) => data(http.post(`/api/executions/${id}/approve`, { feedback: feedback || null })),
  reject: (id, feedback, requestRevision) =>
    data(http.post(`/api/executions/${id}/reject`, { feedback, request_revision: requestRevision })),

  // artifacts
  artifacts: (projectId, params) => data(http.get(`/api/projects/${projectId}/artifacts`, { params })),
  artifact: (id) => data(http.get(`/api/artifacts/${id}`)),
  downloadArtifact: (id, name) => saveBlob(`/api/artifacts/${id}/download`, name || `artifact-${id}`),

  // analytics
  analyticsOverview: () => data(http.get("/api/analytics/overview")),
  analyticsAgents: () => data(http.get("/api/analytics/agents")),
  analyticsExecutions: () => data(http.get("/api/analytics/executions")),
  agentCatalogue: () => data(http.get("/api/agents")),
};
