export const API_BASE = (import.meta.env.VITE_API_URL || "").replace(/\/$/, "");

let authToken = localStorage.getItem("shield_token") || null;

export function setAuthToken(token) {
  authToken = token;
  if (token) localStorage.setItem("shield_token", token);
  else localStorage.removeItem("shield_token");
}

export function getAuthToken() {
  return authToken;
}

export async function getJSON(path, opts = {}) {
  const headers = { "Content-Type": "application/json" };
  if (authToken) headers["Authorization"] = `Bearer ${authToken}`;
  const res = await fetch(`${API_BASE}${path}`, { headers, ...opts });
  if (!res.ok) throw new Error(`${path} -> ${res.status}`);
  return res.json();
}

export const ENDPOINTS = {
  shield: "/api/data/shield-params",
  monitoring: "/api/data/monitoring",
  calculated: "/api/data/calculated",
  evaluate: "/api/engine/evaluate",
  calibrate: "/api/engine/calibrate",
  reference: "/api/engine/reference/beijing-line12",
  login: "/api/auth/login",
  logout: "/api/auth/logout",
  me: "/api/auth/me",
  twinSnapshot: "/api/twin/snapshot",
  models: "/api/models",
  shmSummary: "/api/shm/summary",
  shmReadings: "/api/shm/readings",
  anomalyScan: "/api/anomaly/scan",
  experienceRecommend: "/api/experience/recommend",
  experienceHistory: "/api/experience/history",
  spatialAssets: "/api/spatial/assets",
  spatialClearances: "/api/spatial/clearances",
  reportRegulatory: "/api/report/regulatory",
  assistantChat: "/api/assistant/chat",
  groutHydration: "/api/grout/hydration",
  groutImpact: "/api/grout/impact",
  autodriveAdvisory: "/api/autodrive/advisory",
  ringeyeScan: "/api/ringeye/scan",
  ringeyeAnalyze: "/api/ringeye/analyze",
  ringeyeReadings: "/api/ringeye/readings",
  ringeyeSummary: "/api/ringeye/summary",
  xrayMap: "/api/xray/map",
  xraySummary: "/api/xray/summary"
};
