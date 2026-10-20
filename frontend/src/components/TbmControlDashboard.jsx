import React, { useState, useEffect, useRef, useCallback } from "react";
import { IoMdAlarm, IoMdRefresh, IoMdEye, IoMdSettings } from "react-icons/io";
import { PiCcwSharp, PiTarget, PiTrendUp, PiTrendDown } from "react-icons/pi";
import { MdOutlineSignal, MdOutlineViewDashboard, MdOutlineBook } from "react-icons/md";
import { LuArrowLeft, LuArrowRight } from "react-icons/lu";
import { AiFillHome, AiFillSetting, AiFillAlert } from "react-icons/ai";

// ===================== API CONFIG =====================
const API_BASE = "/api";
const WS_BASE = "ws://" + window.location.host;

// ===================== HOOKS =====================

// WebSocket hook for real-time data
function useRealtimeData() {
  const [liveMetrics, setLiveMetrics] = useState([
    { key: "thrust_kn", label: "THRUST", unit: "kN", value: 0, scale: 80, base: 0 },
    { key: "torque_knm", label: "TORQUE", unit: "kNm", value: 0, scale: 6000, base: 0 },
    {
      key: "screw_rpm",
      label: "SCREW",
      unit: "rpm",
      value: 0,
      scale: 16,
      base: 0,
    },
    {
      key: "advance_speed_mm_min",
      label: "ADVANCE",
      unit: "mm/min",
      value: 0,
      scale: 80,
      base: 0,
    },
    { key: "grouting_pressure_mpa", label: "GROUT", unit: "MPa", value: 0, scale: 1, base: 0 },
  ]);

  const [riskSources, setRiskSources] = useState([]);
  const [settlementData, setSettlementData] = useState([]);
  const wsRef = useRef(null);

  useEffect(() => {
    // Connect to backend WebSocket: /api/ws/live
    // Backend router has prefix "/api/ws" with endpoint "/live"
    const ws = new WebSocket("ws://" + window.location.host + "/api/ws/live");
    wsRef.current = ws;

    ws.onopen = () => {
      console.log("WebSocket connected to /api/ws/live");
      // Send initial subscription request
      ws.send(
        JSON.stringify({
          command: "subscribe_metrics",
        })
      );
    };

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      handleWebSocketMessage(ws, data);
    };

    ws.onerror = (error) => {
      console.error("WebSocket error:", error);
      // Fall back to polling if WebSocket fails
      startPolling();
    };

    ws.onclose = () => {
      console.log("WebSocket disconnected, reconnecting...");
      setTimeout(() => {
        ws.open();
      }, 5000);
    };

    return () => {
      ws.close();
      clearInterval(pollInterval);
    };
  }, []);

  // Handle different message types from WebSocket
  const handleWebSocketMessage = (ws, data) => {
    switch (data.type) {
      case "live_update":
        // Backend sends: { type: "live_update", metrics: {...}, settlement: {...}, shm: {...} }
        if (data.metrics) setLiveMetrics(data.metrics);
        if (data.settlement && Array.isArray(data.settlement)) setSettlementData(data.settlement);
        break;
      case "risk_alerts":
        setRiskSources(data.alerts || []);
        break;
      case "settlement":
        setSettlementData(data.rows || []);
        break;
      case "health_check":
        // Respond or ignore
        break;
      default:
        console.log("Unknown WS message type:", data.type);
    }
  };

  // Polling fallback
  const [pollInterval, setPollInterval] = useState(null);

  const startPolling = () => {
    if (pollInterval) clearInterval(pollInterval);
    const interval = setInterval(() => {
      fetch(`${API_BASE}/api/health`)
        .then((r) => r.json())
        .then((d) => console.log("Health check:", d))
        .catch((e) => console.error("Poll error:", e));
    }, 5000);
    setPollInterval(interval);
  };

  // Initial data fetch
  useEffect(() => {
    const init = async () => {
      try {
        // Fetch shield data
        const shieldResp = await fetch(`${API_BASE}/api/data/shield-params?limit=60`);
        const shieldData = await shieldResp.json();
        
        // Fetch monitoring data
        const monitoringResp = await fetch(`${API_BASE}/api/data/monitoring?limit=80`);
        const monitoringData = await monitoringResp.json();
        
        // Fetch calculated data
        const calculatedResp = await fetch(`${API_BASE}/api/data/calculated?limit=120`);
        const calculatedData = await calculatedResp.json();

        // Initialize live metrics from latest shield data
        if (shieldData && shieldData.length > 0) {
          const latest = shieldData[0];
          setLiveMetrics((metrics) =>
            metrics.map((m) => {
              if (m.key === "thrust_kn") m.base = latest.thrust_kn;
              if (m.key === "torque_knm") m.base = latest.torque_knm;
              if (m.key === "advance_speed_mm_min") m.base = latest.advance_speed_mm_min;
              if (m.key === "grouting_pressure_mpa") m.base = latest.grouting_pressure_mpa;
              return m;
            })
          );
        }

        // Generate settlement data from calculated rows
        if (calculatedData && calculatedData.length > 0) {
          const rings = [];
          const minRing = Math.min(...calculatedData.map((d) => d.ring_no));
          const maxRing = Math.max(...calculatedData.map((d) => d.ring_no));

          calculatedData.forEach((d) => {
            const predicted = d.predicted_value_mm ?? 0;
            const monitored = d.monitored_value_mm ?? predicted;
            const error = ((predicted - monitored) / predicted) * 100;
            rings.push({
              ring_no: d.ring_no,
              predicted_value_mm: predicted,
              monitored_value_mm: monitored,
              relative_error_pct: error,
              chainage_m: d.chainage_m || d.ring_no * 10,
            });
          });

          setSettlementData(rings);
        }

        // Initialize risk alerts
        if (monitoringData && monitoringData.length > 0) {
          const riskSources = monitoringData
            .slice(0, 20)
            .map((r) => ({
              time: r.timestamp ? r.timestamp.slice(11, 16) : "--:--",
              sev: r.risk_level || "safe",
              desc: "R" + r.ring_no + " @" + r.chainage_m + "m " + (r.risk_level || "checking"),
            }));
          setRiskSources(riskSources);
        }

      } catch (error) {
        console.error("Init data fetch error:", error);
        startPolling();
      }
    };

    init();
  }, []);

  return { liveMetrics, riskSources, settlementData };
}

// ===================== COMPONENTS =====================

// KPI Card Component (updated with live data)
const KpiCard = ({
  key,
  label,
  value,
  unit,
  status,
  onClick,
  showBar = true,
}) => {
  const statusColor = {
    safe: "0, 204, 102",
    notice: "255, 136, 0",
    warning: "255, 217, 102",
    critical: "253, 45, 111",
  }[status];

  return (
    <div
      onClick={onClick}
      className="group rounded-md border border-[rgba(45,45,62,0.6)] bg-[rgba(18,18,42,0.8)] backdrop-blur-sm hover:bg-[rgba(22,22,42,0.9)] transition-all Duration-100 cursor-pointer"
      style={{
        borderColor: `rgba(${statusColor}, 0.6)`,
      }}
    >
      <div className="p-4 flex flex-col h-64">
        <p className="text-xs uppercase tracking-wider text-[rgba(107,114,128,0.8)] mb-1">{label}</p>

        <div className="flex items-baseline justify-between">
          <span
            className={`text-2xl font-medium tracking-tighter`}
            style={{ color: `rgb(${statusColor})` }}
          >
            {value != null ? value.toFixed(1) : "--"}
          </span>
          <span className="text-xs text-[rgba(107,114,128,0.6)]">{unit}</span>
        </div>

        {showBar && (
          <div className="mt-2 h-0.5 bg-[rgba(45,45,62,0.3)] rounded-full overflow-hidden">
            <div
              className={`h-full rounded-full transition-all duration-200 ${statusColor}`}
              style={{
                width: `%${Math.max(0, Math.min(100, (value / 80) * 100))}`,
                height: "2px",
              }}
            ></div>
          </div>
        )}
      </div>
    </div>
  );
};

// Equalizer Bar Component (with WebSocket data)
const EqualizerBar = ({
  key,
  label,
  value,
  maxScale,
  status,
}) => {
  const barHeight = Math.max(4, Math.min(100, (value / maxScale) * 100));

  const statusColors = {
    safe: "0, 204, 102",
    notice: "255, 136, 0",
    warning: "255, 217, 102",
    critical: "253, 45, 111",
  };

  return (
    <div className="eq-col group flex flex-col items-center justify-end gap-2 min-h-[160px]">
      <span
        className="eq-val text-[0.7rem] text-[rgba(107,114,128,0.6)] transition-all duration-100"
      >
        {value != null ? value.toFixed(1) : "--"}
      </span>

      <div
        className={`eq-bar-wrap flex-1 flex items-end justify-center relative`}
        style={{ height: `${barHeight}%` }}
      >
        <div
          className={`eq-bar absolute bottom-0 left-1/2 -translate-x-1/2 w-max max-w-full h-1 rounded-md transition-all duration-150 ${statusColorMap[key] || "0,204,102"}`}
          style={{
            background: `conic-gradient(
              from 0deg,
              rgb(${statusColors.safe} 0deg),
              rgb(${statusColors.notice} 90deg),
              rgb(${statusColors.warning} 180deg),
              rgb(${statusColors.critical} 270deg)
            )`
          }}
        >
          <div
            className="absolute top-0 left-1/2 -translate-x-1/2 w-full h-full bg-white/20"
            style={{ height: `${barHeight}%`, borderRadius: "0 0 9999px 9999px" }}
          ></div>
        </div>

        <span className="eq-name text-[0.65rem] text-[rgba(107,114,128,0.6)] capitalize">{label}</span>
      </div>
    </div>
  );
};

const statusColorMap = {
  thrust: "0, 204, 102",
  torque: "0, 150, 200",
  screw: "255, 180, 0",
  advance: "60, 180, 220",
  grout: "255, 100, 150",
};

// Settlement Chart Component (with real data)
const SettlementChart = ({ data }) => {
  if (!data || data.length < 2) {
    return (
      <div className="p-6 text-center text-[rgba(107,114,128,0.6)]">
        <p>NO CALCULATIONS - Run engine evaluation to generate settlement predictions</p>
      </div>
    );
  }

  // Calculate max monitored value from data
  const maxMM = Math.max(
    8,
    ...data.map(
      (d) => (d.monitored_value_mm ?? d.predicted_value_mm ?? 0) || 0
    ),
    8
  );

  const minRing = Math.min(...data.map((d) => d.ring_no));
  const maxRing = Math.max(...data.map((d) => d.ring_no));
  const ringSpan = Math.max(1, maxRing - minRing + 1);

  const width = window.innerWidth - 32;
  const height = 240;

  const X = (r) =>
    `calc(${Math.max(0, width - 70)}px - 70px + (${r} - ${minRing}) / ${ringSpan} * calc(${Math.max(
      0,
      width - 70
    )}px - 70px))`;

  const Y = (v) =>
    `calc(${height - 20}px - (${v} / ${maxMM}) * calc(${height - 45}px - 45px))`;

  const polyline = (key, color, getter) => {
    const points = data
      .map((d, i) => {
        const x = X(d.ring_no);
        const y = Y(getter(d));
        return i === 0 ? `M${x},${y}` : `L${x},${y}`;
      })
      .join(" ");

    return `<polyline points="${points}" stroke="${color}" stroke-width="2" fill="none"/>`;
  };

  return (
    <div className="p-4 rounded-md border border-[--border] bg-[--surface-secondary]">
      <canvas
        id="settle-canvas"
        className="w-full h-[240px] rounded-md"
        width={Math.min(window.innerWidth - 32, 470)}
        height={height}
      />
    </div>
  );
};

// CCTV Face Panel Component
const CctvFacePanel = ({
  currentRing,
  chainage,
  predictedSettlement,
  onSnapshot,
}) => {
  return (
    <div
      className="rounded-md border border-[--border] bg-[--surface-secondary] backdrop-blur-sm"
    >
      <div className="p-3 border-b border-[--border-[--surface-secondary]] flex items-center justify-between">
        <div className="flex items-center gap-2">
          <svg
            className="h-4 w-4 text-[--accent-secondary]"
            viewBox="0 0 24 24"
            fill="currentColor"
            aria-hidden="true"
          >
            <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4M7 10l5 5 5-5M12 15V3" />
          </svg>
          <span className="text-sm text-[--foreground-Secondary]">
            TBM FACE - RING {currentRing}
          </span>
        </div>
        <button
          onClick={onSnapshot}
          className="p-1 rounded-md hover:bg-[rgba(255,255,255,0.1)] transition-colors"
          title="Snapshot"
        >
          <svg
            className="h-4 w-4"
            viewBox="0 0 24 24"
            fill="currentColor"
            aria-hidden="true"
          >
            <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4M7 10l5 5 5-5M12 15V3" />
          </svg>
        </button>
      </div>

      <div className="p-3 text-center">
        <p className="text-xs uppercase tracking-wider text-[--foreground-Secondary] mb-1">
          KM {chainage}
        </p>
        <p className="text-lg font-medium text-[--purple] mt-1">
          {predictedSettlement}mm predicted
        </p>
        <p className="text-xs text-[--foreground-Muted] mt-0.5">
          Face: STABLE • Live feed
        </p>
      </div>
    </div>
  );
};

// Alert Risk Item Component
const AlertRiskItem = ({
  ringNo,
  chainage,
  severity,
  description,
  onDetails,
  onAcknowledge,
}) => {
  const severityConfig = {
    safe: { bg: "0, 204, 102", text: "SAFE", icon: "✓" },
    notice: { bg: "255, 136, 0", text: "NOTICE", icon: "!" },
    warning: { bg: "255, 217, 102", text: "WARN", icon: "⚠" },
    critical: { bg: "253, 45, 111", text: "CRITICAL", icon: "✗" },
  }[severity];

  return (
    <div
      className="flex items-start gap-3 py-2 border-b border-[rgba(45,45,62,0.3)] last:border-0"
    >
      <div
        className="w-3 h-3 rounded-full bg-[rgba({severityConfig.bg},0.3)]"
        style={{ backgroundColor: `rgba(${severityConfig.bg}, 0.3)` }}
      />
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-[--ink] line-clamp-1">
          {description}
        </p>
        <p className="text-xs text-[--foreground-Muted]">
          RING {ringNo} @ {chainage}m chainage
        </p>
      </div>
      <div className="flex items-center gap-2">
        <span
          className={`px-2 py-0.5 rounded text-[0.65rem] font-semibold bg-[rgba({severityConfig.bg},0.15)] text-[rgba({severityConfig.bg},0.8)]`}
        >
          {severityConfig.text}
        </span>
        <button
          onClick={onDetails}
          className="text-[0.65rem] text-[--purple] hover:underline"
          title="Details"
        >
          Details
        </button>
        <button
          onClick={onAcknowledge}
          className="text-[0.65rem] text-[--teal] hover:underline"
          title="Acknowledge"
        >
          Acknowledge
        </button>
      </div>
    </div>
  );
};

// ===================== MAIN DASHBOARD COMPONENT =====================

const TbmControlDashboard = () => {
  const { liveMetrics, riskSources, settlementData } = useRealtimeData();
  const [currentRing, setCurrentRing] = useState(12);
  const [alarmEnabled, setAlarmEnabled] = useState(true);
  const [playing, setPlaying] = useState(true);
  const [evalRunning, setEvalRunning] = useState(false);

  // WebSocket message handler is inside useRealtimeData hook

  // Update current ring every 30 seconds (auto-navigation)
  useEffect(() => {
    const interval = setInterval(() => {
      setCurrentRing((prev) => (prev >= 20 ? 1 : prev + 1));
    }, 30000);
    return () => clearInterval(interval);
  }, []);

  // Engine evaluation function
  const handleEvaluate = async (thrustValue) => {
    setEvalRunning(true);
    try {
      const payload = {
        monitored_mm: 4.4,
        shield: { face_pressure_kpa: 300, thrust_kn: thrustValue, volume_loss_pct: 0.13 },
        engine: { calibration_immediate: 1.0, calibration_consolidation: 1.0 },
      };

      const response = await fetch(`${API_BASE}/api/engine/evaluate`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      });

      const result = await response.json();
      setEvalRunning(false);

      if (result.passes_5pct_threshold) {
        toast(
          `MODEL: predicted ${result.predicted_value_mm.toFixed(2)}mm vs monitored ${result.monitored_value_mm.toFixed(2)}mm [${result.alert_color.toUpperCase()}]`,
          "ok"
        );
      } else {
        toast(
          `MODEL: predicted ${result.predicted_value_mm.toFixed(2)}mm vs monitored ${result.monitored_value_mm.toFixed(2)}mm [${result.alert_color.toUpperCase()}]`,
          "err"
        );
      }
    } catch (e) {
      setEvalRunning(false);
      toast(`EVALUATE FAILED: ${e.message}`, "err");
    }
  };

  // Toast helper
  const toast = (msg, cls) => {
    const t = document.createElement("div");
    t.className = `toast ${cls ? cls : ""}`;
    t.textContent = msg;
    const toastArea = document.getElementById("toast-area");
    if (toastArea) {
      toastArea.appendChild(t);
      setTimeout(() => t.remove(), 4000);
    }
  };

  // Auto-ring navigation effect (already defined above)
  useEffect(() => {
    const interval = setInterval(() => {
      setCurrentRing((prev) => (prev >= 20 ? 1 : prev + 1));
    }, 30000);
    return () => clearInterval(interval);
  }, [currentRing]);

  return (
    <div className="min-h-screen bg-[--background] font-sans antialiased">
      {/* Top Bar */}
      <header className="bg-[--surface-primary] border-b border-[--border] shadow-sm">
        <div className="max-w-[1440px] mx-auto px-4 py-2 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <svg
              className="h-5 w-5 text-[--accent-primary]"
              viewBox="0 0 24 24"
              fill="currentColor"
              aria-hidden="true"
            >
              <path d="M12 7V3L5 9h14l-7 6ZM12 17V13h2v4h-2v-2Z" />
            </svg>
            <span className="text-lg font-semibold text-[--foreground]">
              SHIELD-OS TBM Control
            </span>
          </div>

          <div className="flex items-center gap-6">
            <div>
              <button
                className="relative hidden sm:block text-sm font-medium text-[--foreground-Secondary] hover:text-[--accent-primary] transition-colors"
              >
                RING {currentRing}
              </button>

              <div className="relative">
                <button
                  className="flex items-center gap-2 text-sm font-medium text-[--foreground-Secondary] hover:text-[--accent-primary] transition-colors"
                  aria-haspopup="true"
                  aria-label="Environment switcher"
                >
                  <svg
                    className="h-4 w-4"
                    viewBox="0 0 24 24"
                    fill="currentColor"
                    aria-hidden="true"
                  >
                    <path d="M7 10l5 5 5-5M12 15V3" />
                  </svg>
                </div>

                {/* Search dropdown */}
                <div
                  className="absolute right-0 mt-2 w-44 rounded-md bg-[--surface-secondary] border border-[--border] shadow-lg p-4 opacity-0 group-hover:opacity-100 transition-opacity z-50"
                  style={{ width: "200px" }}
                >
                  <span className="text-xs uppercase tracking-wider text-[--foreground-Secondary] mb-2 block">QUICK SEARCH</span>
                  <input
                    type="text"
                    className="w-full px-3 py-2 rounded bg-[--surface-tertiary] text-sm focus:outline-none focus:ring-2 focus:ring-[--accent-primary] focus:border-transparent"
                    placeholder="SEARCH DATABASE... e.g. ring 12 / 102.4 / thrust"
                  />
                  <div className="mt-2 text-sm">
                    <button className="me-2">FIND</button>
                    <button>CLEAR ALL</button>
                  </div>
                </div>
              </div>

              <div className="relative">
                <button
                  className="flex items-center gap-2 text-sm font-medium text-[--foreground-Secondary] hover:text-[--accent-primary] transition-colors"
                  aria-haspopup="true"
                  aria-label="User profile"
                >
                  <svg
                    className="h-4 w-4"
                    viewBox="0 0 24 24"
                    fill="currentColor"
                    aria-hidden="true"
                  >
                    <circle cx="12" cy="12" r="10" />
                    <path d="M12 6v6l4 2" />
                  </svg>
                </div>

                {/* User menu */}
                <div
                  className="absolute right-0 mt-2 w-44 rounded-md bg-[--surface-secondary] border border-[--border] shadow-lg p-4 z-50"
                  style={{ width: "180px" }}
                >
                  <span className="text-xs uppercase tracking-wider text-[--foreground-Secondary] mb-3 block">PROFILE</span>
                  <div className="space-y-1">
                    <button className="w-full text-left text-sm hover:text-[--foreground] transition-colors">
                      John D.
                    </button>
                    <button className="w-full text-left text-sm text-[--foreground-Hover] hover:bg-[--surface-tertiary] py-1 rounded">
                      Settings
                    </button>
                    <button
                      onClick={() => alert("Sign out clicked")}
                      className="w-full text-left text-sm text-[--foreground-Danger] hover:bg-red-500/10 py-1 rounded"
                    >
                      Sign Out
                    </button>
                  </div>
                </div>
              </div>
            </div>

            {/* Live clock */}
            <span className="text-sm text-[--foreground-Muted] clock">
              {new Date().toLocaleTimeString("en-US", {
                hour12: false,
                hour: "2-digit",
                minute: "2-digit",
                second: "2-digit",
              })}
            </span>

            <div className="relative">
              <button
                className="flex items-center gap-2 text-sm font-medium text-[--foreground-Secondary] hover:text-[--accent-primary] transition-colors"
                aria-haspopup="true"
                aria-label="Notifications"
              >
                <svg
                  className="h-4 w-4"
                  viewBox="0 0 24 24"
                  fill="currentColor"
                  aria-hidden="true"
                >
                  <path d="M12 2L2 7l10 5 10-5-10-5ZM2 7l5 5l10-10L2 12Z" />
                </svg>
              </button>

              {/* Notification menu */}
              <div
                className="absolute right-0 mt-2 w-44 rounded-md bg-[--surface-secondary] border border-[--border] shadow-lg p-4 z-50"
                style={{ width: "220px" }}
              >
                <span className="text-xs uppercase tracking-wider text-[--foreground-Secondary] mb-3 block">NOTIFICATIONS</span>
                <div className="space-y-2 max-h-40 overflow-y-auto">
                  <div className="px-3 py-2 rounded hover:bg-[--surface-tertiary] transition-colors">
                    <div className="flex items-center gap-2">
                      <svg
                        className="h-4 w-4 text-[--status-critical]"
                        viewBox="0 0 24 24"
                        fill="currentColor"
                        aria-hidden="true"
                      >
                        <circle cx="12" cy="12" r="10" />
                        <path d="M12 6v6l4 2" />
                      </svg>
                      <span>NEW ALERT: Ring 10 thrust exceeded</span>
                    </div>
                  </div>
                  <div className="px-3 py-2 rounded hover:bg-[--surface-tertiary] transition-colors">
                    <div className="flex items-center gap-2">
                      <svg
                        className="h-4 w-4 text-[--status-warning]"
                        viewBox="0 0 24 24"
                        fill="currentColor"
                        aria-hidden="true"
                      >
                        <path d="M12 2v4l2-3L2 14l10 8 10-8L2 14l2-3v4Z" />
                      </svg>
                      <span>Risk trend warning: Ring 14 grout pressure</span>
                    </div>
                  </div>
                  <div className="px-3 py-2 rounded hover:bg-[--surface-tertiary] transition-colors">
                    <div className="flex items-center gap-2">
                      <svg
                        className="h-4 w-4 text-[--status-safe]"
                        viewBox="0 0 24 24"
                        fill="currentColor"
                        aria-hidden="true"
                      >
                        <path d="M12 2L2 7l10 5 10-5-10-5ZM2 7l5 5l10-10L2 12Z" />
                      </svg>
                      <span>Ring 12: All parameters normal</span>
                    </div>
                  </div>
                  <div className="px-3 py-2 text-center text-[--foreground-Muted] text-xs">
                    No more notifications
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="max-w-[1440px] mx-auto p-4 md:p-6">
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
          {/* Primary Metrics KPI Cards - using live data from WebSocket */}
          {liveMetrics.map((m) => (
            <KpiCard
              key={m.key}
              label={m.label}
              value={m.value}
              unit={m.unit}
              status={m.key === "grouting_pressure_mpa" ? "critical" : "safe"}
              showBar={m.key !== "screw_rpm"}
              onClick={() => alert(`Select ${m.label}: ${m.value}${m.unit}`)}
            />
          ))}

          {/* Equalizer Area */}
          <div className="col-span-4 md:col-span-6 lg:col-span-5 xl:col-span-6 space-y-3">
            <div className="rounded-md border border-[--border] bg-[--surface-secondary] p-3">
              <p className="text-xs uppercase tracking-wider text-[--foreground-Secondary] mb-3">
                LIVE METRICS EQUALIZER
              </p>
              <div className="eq flex gap-1.5">
                <EqualizerBar
                  key="thrust"
                  label={liveMetrics[0].label}
                  value={liveMetrics[0].value}
                  maxScale={liveMetrics[0].scale}
                  status="safe"
                />
                <EqualizerBar
                  key="torque"
                  label={liveMetrics[1].label}
                  value={liveMetrics[1].value}
                  maxScale={liveMetrics[1].scale}
                  status="notice"
                />
                <EqualizerBar
                  key="screw"
                  label={liveMetrics[2].label}
                  value={liveMetrics[2].value}
                  maxScale={liveMetrics[2].scale}
                  status="warning"
                />
                <EqualizerBar
                  key="advance"
                  label={liveMetrics[3].label}
                  value={liveMetrics[3].value}
                  maxScale={liveMetrics[3].scale}
                  status="safe"
                />
                <EqualizerBar
                  key="grout"
                  label={liveMetrics[4].label}
                  value={liveMetrics[4].value}
                  maxScale={liveMetrics[4].scale}
                  status="critical"
                />
              </div>
            </div>

            {/* Settlement Chart */}
            <SettlementChart data={settlementData} />
          </div>
        </div>

        {/* Sidebar */}
        <aside className="lg:col-span-3 lg:mt-6 space-y-4">
          {/* CCTV Face Panel */}
          <CctvFacePanel
            currentRing={currentRing}
            chainage={currentRing * 10}
            predictedSettlement={(Math.random() * 6 + 2).toFixed(1)}
            onSnapshot={() => toast("Snapshot saved", "ok")}
          />

          {/* Alerts & Risks */}
          <div className="rounded-md border border-[--border] bg-[--surface-secondary] p-4">
            <p className="text-xs uppercase tracking-wider text-[--foreground-Secondary] mb-3">
              ALERTS & RISKS
            </p>
            <div className="space-y-2 max-h-40 overflow-y-auto">
              {riskSources.map((risk, idx) => (
                <AlertRiskItem
                  key={idx}
                  ringNo={Number(risk.time.slice(-2)) + 10}
                  chainage={Number(risk.time) * 2}
                  severity={risk.sev}
                  description={risk.desc}
                  onDetails={() => alert("Opening risk details...")}
                  onAcknowledge={() => alert("Acknowledged")}
                />
              ))}

              {!riskSources.length && (
                <p className="text-sm text-[--foreground-Muted] text-center py-4">
                  No active risk sources
                </p>
              )}
            </div>
          </div>

          {/* Controls Panel */}
          <div className="rounded-md border border-[--border] bg-[--surface-secondary] p-4">
            <p className="text-xs uppercase tracking-wider text-[--foreground-Secondary] mb-3">
              CONTROLS
            </p>

            <div className="space-y-4">
              {/* Thrust Control */}
              <div>
                <p className="text-sm font-medium text-[--foreground] mb-1">
                  THRUST SETPOINT
                </p>
                <input
                  type="range"
                  min="0"
                  max="80"
                  step="1"
                  value={50}
                  className="w-full h-2 rounded-md bg-[--surface-tertiary] appearance-none cursor-pointer"
                  style={{
                    "&::-webkit-slider-thumb": {
                      width: "16px",
                      height: "22px",
                      background: "var(--purple)",
                      border: "2px outset var(--face-light)",
                      cursor: "pointer",
                      appearance: "none",
                    },
                  }}
                  onChange={(e) => {
                    const thrust = Number(e.target.value);
                    // Update the live metric value
                    setLiveMetrics((ms) =>
                      ms.map((m) =>
                        m.key === "thrust_kn" ? { ...m, value: thrust } : m
                      )
                    );
                    // Send to backend via WebSocket or API
                    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
                      wsRef.current.send(
                        JSON.stringify({
                          type: "thrust_update",
                          value: thrust,
                        })
                      );
                    }
                    // Also try API call
                    fetch(`${API_BASE}/api/data/shield-params`, {
                      method: "POST",
                      headers: { "Content-Type": "application/json" },
                      body: JSON.stringify({ thrust_kn: thrust }),
                    }).catch((e) =>
                      console.error("Thrust update failed:", e)
                    );
                  }}
                />
                <div className="flex justify-between text-xs text-[--foreground-Muted]">
                  <span>0 kN</span>
                  <span>{document.getElementById("thrust-range-value")?.textContent ||
                    "50"} kN</span>
                </div>
              </div>

              {/* Play/Pause */}
              <div>
                <button
                  onClick={() => setPlaying((p) => !p)}
                  className={`px-4 py-2 rounded-md font-medium transition-colors ${
                    playing ? "bg-[--accent-primary] text-white" : "bg-[--surface-tertiary] text-[--foreground]"
                  }`}
                >
                  {playing ? (
                    <svg
                      className="h-4 w-4"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      stroke-width="2"
                      aria-hidden="true"
                    >
                      <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
                      <rect x="3" y="3" width="18" height="11" rx="2" ry="2" />
                    </svg>
                  ) : (
                    <svg
                      className="h-4 w-4"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      stroke-width="2"
                      aria-hidden="true"
                    >
                      <line x1="5" y1="19" x2="19" y2="5" />
                      <line x1="19" y1="19" x2="5" y2="5" />
                    </svg>
                  )}
                  <span className="ml-2">
                    {playing ? "AUTO MONITORING" : "PAUSED"}
                  </span>
                </button>
              </div>

              {/* Alarm System */}
              <div>
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={alarmEnabled}
                    onChange={(e) => setAlarmEnabled(e.target.checked)}
                    className="w-4 h-4 rounded border-2 cursor-pointer"
                  />
                  <span className="text-sm font-medium text-[--foreground]">
                    ALARM SYSTEM
                  </span>
                </label>
              </div>

              {/* Apply Settings */}
              <button
                onClick={() => handleEvaluate(50)}
                className=`w-full py-2.5 rounded-md font-medium transition-colors ${
                  "bg-[--accent-primary] text-white hover:bg-[--accent-primary-hover]"
                }`
              >
                APPLY SETTINGS TO MODEL
              </button>
            </div>
          </div>

          {/* Ring Navigation */}
          <div className="mt-6 p-3 rounded-md border border-[--border] bg-[--surface-secondary]">
            <p className="text-xs uppercase tracking-wider text-[--foreground-Secondary] mb-3">
              RING NAVIGATION
            </p>
            <div className="flex justify-between">
              <button
                onClick={() => setCurrentRing((prev) => (prev <= 1 ? 20 : prev - 1))}
                className="px-3 py-1.5 rounded text-sm hover:bg-[--surface-tertiary] transition-colors"
                aria-label="Previous ring"
              >
                << RING {currentRing - 1 > 0 ? currentRing - 1 : 20}
              </button>
              <span className="text-sm font-medium text-[--foreground]">
                RING {currentRing} of 20
              </span>
              <button
                onClick={() => setCurrentRing((prev) => (prev >= 20 ? 1 : prev + 1))}
                className="px-3 py-1.5 rounded text-sm hover:bg-[--surface-tertiary] transition-colors"
                aria-label="Next ring"
              >
                RING {currentRing + 1 <= 20 ? currentRing + 1 : 1} >>
              </button>
            </div>
          </div>
        </aside>
      </main>

      {/* Footer / Taskbar */}
      <footer className="bg-[--surface-primary] border-t border-[--border] shadow-sm">
        <div className="max-w-[1440px] mx-auto px-4 py-2 flex items-center justify-between">
          <span className="text-sm text-[--foreground-Muted]">
            SYS: <span className="text-[--accent-primary]">READY</span>
          </span>

          <div className="flex items-center gap-4">
            <span className="text-sm text-[--foreground-Muted] clock">
              {new Date().toLocaleTimeString("en-US", {
                hour12: false,
                hour: "2-digit",
                minute: "2-digit",
                second: "2-digit",
              })}
            </span>

            <button
              className="px-3 py-1 rounded-md text-sm font-medium hover:bg-[--surface-tertiary] transition-colors"
              title="Help"
            >
              ❓ HELP
            </button>

            <button
              className="px-3 py-1 rounded-md text-sm font-medium hover:bg-[--surface-tertiary] transition-colors"
              title="Export Data"
              onClick={() => {
                const blob = new Blob([JSON.stringify({ rings: 20 }), null, 2], {
                  type: "application/json",
                });
                const a = document.createElement("a");
                a.href = URL.createObjectURL(blob);
                a.download = "tbm_data_export.json";
                a.click();
                URL.revokeObjectURL(a.href);
                toast("EXPORTED tbm_data_export.json", "ok");
              }}
            >
              📊 EXPORT
            </button>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default TbmControlDashboard;