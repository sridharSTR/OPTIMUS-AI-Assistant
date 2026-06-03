import axios from "axios";

const getDefaultApiBaseUrl = () => {
  if (window.location.protocol === "file:") {
    return "http://127.0.0.1:8000/api";
  }

  if (window.location.protocol === "https:") {
    return "/api";
  }

  const hostname = window.location.hostname === "0.0.0.0"
    ? "127.0.0.1"
    : window.location.hostname || "127.0.0.1";

  return `${window.location.protocol}//${hostname}:8000/api`;
};

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || getDefaultApiBaseUrl();
const joinApiUrl = (path) => `${API_BASE_URL.replace(/\/$/, "")}${path}`;
const AUTH_USER_KEY = "user";
const AUTH_ROLE_KEY = "role";
const LEGACY_AUTH_USER_KEY = "jarvis_user";
const LEGACY_AUTH_ROLE_KEY = "jarvis_role";
const LEGACY_AUTH_ACCESS_KEY = "access";
const LEGACY_AUTH_REFRESH_KEY = "refresh";

const api = axios.create({
  baseURL: API_BASE_URL,
  withCredentials: true,
});

export const clearStoredTokens = () => {
  window.localStorage.removeItem(AUTH_USER_KEY);
  window.localStorage.removeItem(AUTH_ROLE_KEY);
  window.localStorage.removeItem(LEGACY_AUTH_ACCESS_KEY);
  window.localStorage.removeItem(LEGACY_AUTH_REFRESH_KEY);
  window.localStorage.removeItem(LEGACY_AUTH_USER_KEY);
  window.localStorage.removeItem(LEGACY_AUTH_ROLE_KEY);
  window.dispatchEvent(new Event("auth:cleared"));
};

export const storeAuthUser = (user) => {
  if (!user) return;
  window.localStorage.setItem(AUTH_USER_KEY, JSON.stringify(user));
  window.localStorage.setItem(AUTH_ROLE_KEY, user.role || "user");
  window.localStorage.removeItem(LEGACY_AUTH_USER_KEY);
  window.localStorage.removeItem(LEGACY_AUTH_ROLE_KEY);
  window.dispatchEvent(new Event("auth:updated"));
};

export const storeAuthSession = ({ user }) => {
  storeAuthUser(user);
  window.localStorage.removeItem(LEGACY_AUTH_ACCESS_KEY);
  window.localStorage.removeItem(LEGACY_AUTH_REFRESH_KEY);
};

export const getStoredAuthUser = () => {
  try {
    const rawUser = window.localStorage.getItem(AUTH_USER_KEY) || window.localStorage.getItem(LEGACY_AUTH_USER_KEY);
    return rawUser ? JSON.parse(rawUser) : null;
  } catch {
    clearStoredTokens();
    return null;
  }
};

export const getStoredAuthRole = () => window.localStorage.getItem(AUTH_ROLE_KEY) || getStoredAuthUser()?.role || "";

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    const requestUrl = originalRequest?.url || "";
    const canAttemptRefresh =
      originalRequest &&
      !originalRequest.skipAuthRefresh &&
      !requestUrl.includes("/token/refresh/") &&
      !requestUrl.includes("/users/login/") &&
      !requestUrl.includes("/users/register/") &&
      !requestUrl.includes("/users/verify-otp/");

    if (error.response?.status === 401 && canAttemptRefresh && !originalRequest._retry) {
      originalRequest._retry = true;
      try {
        await axios.post(
          joinApiUrl("/token/refresh/"),
          {},
          { withCredentials: true },
        );
        return api(originalRequest);
      } catch (refreshError) {
        clearStoredTokens();
        window.dispatchEvent(new Event("auth:expired"));
        return Promise.reject(refreshError);
      }
    }

    return Promise.reject(error);
  },
);

export const authApi = {
  register: (payload) => api.post("/users/register/", payload),
  verifyOtp: (payload) => api.post("/users/verify-otp/", payload),
  login: (payload) => api.post("/users/login/", payload),
  logout: () => api.post("/users/logout/", {}, { skipAuthRefresh: true }),
  me: (config = {}) => api.get("/users/me/", config),
  updateProfile: (payload) => api.patch("/users/me/", payload),
};

export const chatApi = {
  conversations: () => api.get("/ai/conversations/"),
  deleteConversation: (id) => api.delete(`/ai/conversations/${id}/`),
  sendMessage: (payload) => api.post("/ai/chat/", payload),
};

export const nlpApi = {
  memories: () => api.get("/ai/memories/"),
  memory: () => api.get("/ai/memory/"),
  createMemory: (payload) => api.post("/ai/memories/", payload),
  updateMemory: (id, payload) => api.patch(`/ai/memories/${id}/`, payload),
  deleteMemory: (id) => api.delete(`/ai/memories/${id}/`),
  analytics: () => api.get("/ai/analytics/nlp/"),
  responseCache: () => api.get("/ai/response-cache/"),
  resumeAnalyses: () => api.get("/ai/resume-analyses/"),
  deleteResumeAnalysis: (id) => api.delete(`/ai/resume-analyses/${id}/`),
  analyzeResume: (file) => {
    const formData = new window.FormData();
    formData.append("file", file);
    return api.post("/ai/resume-analyses/", formData);
  },
};

export const ragApi = {
  documents: (query = "") => api.get(`/rag/documents/${query ? `?q=${encodeURIComponent(query)}` : ""}`),
  upload: (file, onUploadProgress) => {
    const formData = new window.FormData();
    formData.append("file", file);
    return api.post("/rag/upload/", formData, {
      onUploadProgress,
    });
  },
  deleteDocument: (id) => api.delete(`/rag/documents/${id}/`),
  chat: (payload) => api.post("/rag/chat/", payload),
  analytics: () => api.get("/rag/analytics/"),
  analyzeResume: (id) => api.post(`/rag/documents/${id}/resume-analysis/`),
};

export const adminApi = {
  dashboard: () => api.get("/admin/dashboard/"),
  users: (query = "") => api.get(`/admin/users/${query ? `?q=${encodeURIComponent(query)}` : ""}`),
  promoteUser: (payload) => api.post("/admin/promote-user/", payload),
  demoteUser: (payload) => api.post("/admin/demote-user/", payload),
  banUser: (payload) => api.post("/admin/ban-user/", payload),
  deleteUser: (userId) => api.delete("/admin/users/", { data: { user_id: userId } }),
  conversations: (query = "") => api.get(`/admin/conversations/${query ? `?q=${encodeURIComponent(query)}` : ""}`),
  deleteConversation: (conversationId) => api.delete("/admin/conversations/", { data: { conversation_id: conversationId } }),
  messages: ({ query = "", conversationId = "", userId = "" } = {}) => {
    const params = new window.URLSearchParams();
    if (query) params.set("q", query);
    if (conversationId) params.set("conversation_id", conversationId);
    if (userId) params.set("user_id", userId);
    const suffix = params.toString() ? `?${params.toString()}` : "";
    return api.get(`/admin/messages/${suffix}`);
  },
  analytics: () => api.get("/admin/analytics/"),
  memories: (query = "") => api.get(`/admin/memories/${query ? `?q=${encodeURIComponent(query)}` : ""}`),
  updateMemory: (payload) => api.patch("/admin/memories/", payload),
  deleteMemory: (memoryId) => api.delete("/admin/memories/", { data: { memory_id: memoryId } }),
  resumeAnalyses: (query = "") => api.get(`/admin/resume-analyses/${query ? `?q=${encodeURIComponent(query)}` : ""}`),
  deleteResumeAnalysis: (analysisId) => api.delete("/admin/resume-analyses/", { data: { analysis_id: analysisId } }),
};

export default api;
