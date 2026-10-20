export const API_BASE = (import.meta.env.VITE_API_URL || "").replace(/\/$/, "");
const defaultWS = typeof window !== "undefined"
  ? `${window.location.protocol === "https:" ? "wss:" : "ws:"}//${window.location.host}`
  : "ws://localhost:8000";
export const WS_BASE = API_BASE ? API_BASE.replace(/^http/, "ws") : defaultWS;

let authToken = localStorage.getItem("shield_token") || null;

// ============================================================
// WebSocket Manager - FORGE3D Innovation #1
// ============================================================

export class WSManager {
  constructor(path = "/api/ws/live") {
    this.path = path;
    this.ws = null;
    this.listeners = new Map();
    this.reconnectDelay = 1000;
    this.maxReconnectDelay = 30000;
    this.connected = false;
    this._reconnectTimer = null;
  }

  connect() {
    if (this.ws && (this.ws.readyState === WebSocket.OPEN || this.ws.readyState === WebSocket.CONNECTING)) {
      return;
    }

    const url = `${WS_BASE}${this.path}`;
    this.ws = new WebSocket(url);

    this.ws.onopen = () => {
      this.connected = true;
      this.reconnectDelay = 1000;
      this._emit("connection", { status: "connected" });
      console.log(`[WS] Connected to ${this.path}`);
    };

    this.ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        this._emit(data.type || "message", data);
        this._emit("any", data);
      } catch (e) {
        console.warn("[WS] Parse error:", e);
      }
    };

    this.ws.onclose = () => {
      this.connected = false;
      this._emit("connection", { status: "disconnected" });
      this._scheduleReconnect();
    };

    this.ws.onerror = (err) => {
      console.warn("[WS] Error:", err);
      this.ws?.close();
    };
  }

  _scheduleReconnect() {
    if (this._reconnectTimer) clearTimeout(this._reconnectTimer);
    this._reconnectTimer = setTimeout(() => {
      console.log(`[WS] Reconnecting (delay: ${this.reconnectDelay}ms)...`);
      this.connect();
      this.reconnectDelay = Math.min(this.reconnectDelay * 2, this.maxReconnectDelay);
    }, this.reconnectDelay);
  }

  on(event, callback) {
    if (!this.listeners.has(event)) this.listeners.set(event, new Set());
    this.listeners.get(event).add(callback);
    return () => this.listeners.get(event)?.delete(callback);
  }

  _emit(event, data) {
    this.listeners.get(event)?.forEach((cb) => cb(data));
    this.listeners.get("*")?.forEach((cb) => cb(event, data));
  }

  send(command, payload = {}) {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ command, ...payload }));
    }
  }

  disconnect() {
    if (this._reconnectTimer) clearTimeout(this._reconnectTimer);
    this.reconnectDelay = 300000; // don't reconnect
    this.ws?.close();
    this.connected = false;
  }
}

// Singleton instances
export const liveWS = new WSManager("/api/ws/live");
export const twinWS = new WSManager("/api/ws/twin");

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
  xraySummary: "/api/xray/summary",
  iotSensors: "/api/iot/sensors",
  iotHealth: "/api/iot/health",
  iotReadings: "/api/iot/readings",
  iotSimulate: "/api/iot/simulate",
  iotTypes: "/api/iot/types",
  alerts: "/api/alerts",
  alertsSummary: "/api/alerts/summary",
  riskAssessments: "/api/risk/assessments"
};
