import { useCallback, useEffect, useRef, useState } from "react";
import { ENDPOINTS, getJSON, setAuthToken } from "./api";
import Window from "./components/Window";
import Equalizer, { METRICS } from "./components/Equalizer";
import CctvFeed from "./components/CctvFeed";
import AlertsLog from "./components/AlertsLog";
import Controls from "./components/Controls";
import SettlementChart from "./components/SettlementChart";
import ContextMenu from "./components/ContextMenu";
import SearchDock from "./components/SearchDock";
import Taskbar from "./components/Taskbar";
import Toasts from "./components/Toasts";
import LoginScreen from "./components/LoginScreen";
import DigitalTwin from "./components/DigitalTwin";
import TbmDashboard from "./components/TbmDashboard";
import ShmMonitor from "./components/ShmMonitor";
import AnomalyEngine from "./components/AnomalyEngine";
import ExperienceTransfer from "./components/ExperienceTransfer";
import SpatialPlanner from "./components/SpatialPlanner";
import ReportGenerator from "./components/ReportGenerator";
import AiAssistant from "./components/AiAssistant";
import Autodrive from "./components/Autodrive";
import GroutSim from "./components/GroutSim";
import XrayMap from "./components/XrayMap";
import RingEye from "./components/RingEye";
import GeologyView from "./components/GeologyView";
import CutterWear from "./components/CutterWear";
import GisView from "./components/GisView";
import Annotations from "./components/Annotations";
import AROverlay from "./components/AROverlay";
import VoiceCommand from "./components/VoiceCommand";

const INITIAL_WINDOWS = [
  { id: "win-sensor", title: "SENSOR.EXE - Real-Time Cutterhead Metrics", x: 24, y: 60 },
  { id: "win-camera", title: "CAMERA.EXE - CCTV: Tunnel Face (AR)", x: 500, y: 130 },
  { id: "win-alerts", title: "ALERTS.LOG - Active Risk Sources", x: 960, y: 60 },
  { id: "win-controls", title: "ADVANCE.CTL - Parameter Controls", x: 24, y: 340 },
  { id: "win-settlement", title: "SETTLEMENT.PLT - Predicted vs Monitored", x: 500, y: 340 },
  { id: "win-twin", title: "TWIN.EXE - Digital Cyber Twin 3D", x: 60, y: 120 },
  { id: "win-dashboard", title: "TBM-DASH.EXE - Real-Time TBM Monitoring Dashboard", x: 240, y: 70 },
  { id: "win-shm", title: "SHM.EXE - Structural Health Monitor", x: 60, y: 120 },
  { id: "win-anomaly", title: "ANOMALY.AI - ML Anomaly Engine", x: 80, y: 140 },
  { id: "win-transfer", title: "TRANSFER.AI - A/B/C Experience Transfer", x: 100, y: 160 },
  { id: "win-spatial", title: "SPATIAL.PLN - 3D Clearance Planner", x: 120, y: 180 },
  { id: "win-report", title: "REPORT.EXE - Auto-Regulatory Reporting", x: 140, y: 200 },
  { id: "win-ai", title: "AI-ASSIST.EXE - TunnelArchitect-AI Chat", x: 420, y: 140 },
  { id: "win-autodrive", title: "AUTODRIVE.AI - Closed-Loop Predict-Then-Control", x: 60, y: 120 },
  { id: "win-grout", title: "GROUT-SIM.EXE - Hydro-Thermal Grout Hardening", x: 80, y: 140 },
  { id: "win-xray", title: "X-RAY.EXE - Spatial Strain Map", x: 100, y: 160 },
  { id: "win-ringeye", title: "RING-EYE.EXE - Optical Ring Deformation", x: 120, y: 180 },
  { id: "win-geology", title: "GEOLOGY.EXE - 3D Geological Stratigraphy", x: 200, y: 100 },
  { id: "win-cutter", title: "CUTTER.AI - Predictive Cutter Wear Intelligence", x: 220, y: 120 },
  { id: "win-gis", title: "GIS.MAP - Tunnel Alignment & Coordinates", x: 240, y: 140 },
  { id: "win-ar", title: "AR.EXE - Augmented Reality Field Inspection", x: 260, y: 160 },
  { id: "win-voice", title: "VOICE.EXE - Voice Command Interface", x: 280, y: 180 },
  { id: "search-results", title: "SEARCH.EXE - Query Results", x: 300, y: 160 }
];

const ICONS = [
  { id: "icon-geo", open: "win-sensor", label: "Geo Data" },
  { id: "icon-cutter", open: "win-camera", label: "Cutterhead" },
  { id: "icon-risk", open: "win-alerts", label: "Risk Reports" },
  { id: "icon-settle", open: "win-settlement", label: "Settlement" },
  { id: "icon-twin", open: "win-twin", label: "Cyber Twin" },
  { id: "icon-dashboard", open: "win-dashboard", label: "TBM Dash" },
  { id: "icon-shm", open: "win-shm", label: "SHM" },
  { id: "icon-anomaly", open: "win-anomaly", label: "Anomaly AI" },
  { id: "icon-transfer", open: "win-transfer", label: "Transfer" },
  { id: "icon-spatial", open: "win-spatial", label: "Spatial" },
  { id: "icon-report", open: "win-report", label: "Report" },
  { id: "icon-ai", open: "win-ai", label: "AI Assist" },
  { id: "icon-autodrive", open: "win-autodrive", label: "Autodrive" },
  { id: "icon-grout", open: "win-grout", label: "Grout-Sim" },
  { id: "icon-xray", open: "win-xray", label: "X-Ray" },
  { id: "icon-ringeye", open: "win-ringeye", label: "Ring-Eye" },
  { id: "icon-geology", open: "win-geology", label: "Geology" },
  { id: "icon-cutter", open: "win-cutter", label: "Cutter AI" },
  { id: "icon-gis", open: "win-gis", label: "GIS Map" },
  { id: "icon-ar", open: "win-ar", label: "AR View" },
  { id: "icon-voice", open: "win-voice", label: "Voice" }
];

const RISK_SOURCES = [
  { time: "--:--", sev: "safe", desc: "Building B-01 foundation, clearance check OK" },
  { time: "--:--", sev: "notice", desc: "Sewer DN800 pipe, clearance 2.186 m (verify)" },
  { time: "--:--", sev: "warning", desc: "Water main DN1200 20 m ahead of face" },
  { time: "--:--", sev: "critical", desc: "Adjacent operating metro tunnel, L-line" }
];

let toastSeq = 0;

export default function App() {
  const [windows, setWindows] = useState(() =>
    Object.fromEntries(INITIAL_WINDOWS.map((w, i) => [w.id, { ...w, open: false, minimized: false, maximized: false, z: 10 + i }]))
  );
  const topRef = useRef(100);

  const [data, setData] = useState({ shield: [], monitoring: [], calculated: [] });
  const [sysMsg, setSysMsg] = useState("CONNECTING...");
  const [thresholds, setThresholds] = useState({ orange: 10, yellow: 20, red: 30 });
  const [playing, setPlaying] = useState(true);
  const [toasts, setToasts] = useState([]);
  const [searchResults, setSearchResults] = useState(null);
  const [auth, setAuth] = useState(null);

  const [metrics, setMetrics] = useState({});
  const [xrayAlerts, setXrayAlerts] = useState([]);

  useEffect(() => {
    let cancelled = false;
    async function poll() {
      try {
        const res = await getJSON(ENDPOINTS.xraySummary);
        if (cancelled) return;
        const alerts = res.results
          .filter((r) => r.level !== "safe")
          .map((r) => ({
            time: "--:--",
            sev: r.level,
            desc: `X-RAY ${r.name}: ${r.settlement_mm}mm settle / ${r.strain_ue}ue strain`
          }));
        setXrayAlerts(alerts);
      } catch (e) {
        /* API offline - ignore */
      }
    }
    poll();
    const id = setInterval(poll, 12000);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, []);

  useEffect(() => {
    const token = localStorage.getItem("shield_token");
    if (!token) return;
    getJSON(ENDPOINTS.me)
      .then((u) => setAuth(u))
      .catch(() => setAuthToken(null));
  }, []);

  function handleAuth(user) {
    setAuth(user);
    toast(`WELCOME ${user.username.toUpperCase()} - ROLE: ${user.role.toUpperCase()}`, "ok");
  }

  function handleGuest() {
    setAuth({ username: "guest", role: "guest", full_name: "Offline Guest" });
    toast("GUEST MODE - READ ONLY SIMULATION", "ok");
  }

  function handleLogout() {
    getJSON(ENDPOINTS.logout, { method: "POST" }).catch(() => {});
    setAuthToken(null);
    setAuth(null);
  }

  const toast = useCallback((msg, cls) => {
    const id = ++toastSeq;
    setToasts((prev) => [...prev, { id, msg, cls }]);
    setTimeout(() => setToasts((prev) => prev.filter((t) => t.id !== id)), 4000);
  }, []);

  const focus = useCallback((id) => {
    topRef.current += 1;
    setWindows((prev) => (prev[id] ? { ...prev, [id]: { ...prev[id], z: topRef.current } } : prev));
  }, []);
  const toggleMin = useCallback((id) => setWindows((p) => ({ ...p, [id]: { ...p[id], minimized: !p[id].minimized } })), []);
  const toggleMax = useCallback((id) => setWindows((p) => ({ ...p, [id]: { ...p[id], maximized: !p[id].maximized } })), []);
  const close = useCallback((id) => setWindows((p) => ({ ...p, [id]: { ...p[id], open: false } })), []);
  const move = useCallback((id, x, y) => setWindows((p) => (p[id] ? { ...p, [id]: { ...p[id], x, y } } : p)), []);
  const openWin = useCallback((id) => {
    setWindows((p) => ({ ...p, [id]: { ...p[id], open: true, minimized: false } }));
    focus(id);
  }, [focus]);

  const handleSearchResults = useCallback((results) => {
    setSearchResults(results);
    if (results) openWin("search-results");
  }, [openWin]);

  const runAssistantAction = useCallback((action) => {
    if (!action || !action.type) return;
    if (action.type === "navigate") {
      if (windows[action.window] && !windows[action.window].open) {
        openWin(action.window);
      }
      focus(action.window);
    } else if (action.type === "design") {
      openWin("win-dashboard");
      toast("TBM-DASH OPENED - DESIGN APPLIED TO 3D MODEL", "ok");
    } else if (action.type === "report") {
      openWin("win-report");
      toast("REPORT.EXE OPENED - CLICK GENERATE", "ok");
    }
  }, [windows, openWin, focus, toast]);

  const load = useCallback(async () => {
    setSysMsg("CONNECTING...");
    try {
      const [shield, monitoring, calculated] = await Promise.all([
        getJSON(`${ENDPOINTS.shield}?limit=60`),
        getJSON(`${ENDPOINTS.monitoring}?limit=80`),
        getJSON(`${ENDPOINTS.calculated}?limit=120`)
      ]);
      setData({ shield, monitoring, calculated });
      setSysMsg(`DATA LINK OK (${calculated.length} calc rows)`);
      return true;
    } catch (e) {
      setSysMsg("API OFFLINE - SIM MODE");
      return false;
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    const rows = data.shield;
    if (!rows.length) return;
    const latest = rows[0];
    const base = {
      thrust_kn: latest.thrust_kn,
      torque_knm: latest.torque_knm,
      advance_speed_mm_min: latest.advance_speed_mm_min,
      grouting_pressure_mpa: latest.grouting_pressure_mpa,
      screw_rpm: 8.5
    };
    setMetrics(base);
  }, [data.shield]);

  useEffect(() => {
    const id = setInterval(() => {
      setMetrics((prev) => {
        const next = { ...prev };
        METRICS.forEach((m) => {
          const base = prev[m.key] ?? 0;
          next[m.key] = Math.max(0, base + (Math.random() - 0.5) * m.scale * 0.03);
        });
        return next;
      });
    }, 1400);
    return () => clearInterval(id);
  }, []);

  useEffect(() => {
    getJSON(ENDPOINTS.reference)
      .then((r) =>
        toast(`REFERENCE ${r.line}: ${r.predicted_mm}mm vs ${r.monitored_mm}mm (${Number(r.relative_error_pct).toFixed(1)}% < 5%)`, "ok")
      )
      .catch(() => {});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const latest = data.shield[0] || {};

  const currentStation = latest.chainage_m != null ? `${Number(latest.chainage_m).toFixed(1)}m` : "----";
  const currentRing = latest.ring_no != null ? latest.ring_no : "----";

  function contextAction(action) {
    if (action === "refresh") {
      load().then((ok) => toast(ok ? "FEED REFRESHED" : "REFRESH FAILED: API offline", ok ? "ok" : "err"));
    } else if (action === "export") {
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = "shield_export.json";
      a.click();
      URL.revokeObjectURL(a.href);
      toast(`EXPORTED shield_export.json (${data.calculated.length} rows)`);
    } else if (action === "calibrate") {
      const mm = window.prompt("Enter monitored settlement (mm):", "4.4");
      if (mm == null) return;
      getJSON(ENDPOINTS.calibrate, {
        method: "POST",
        body: JSON.stringify({ monitored_mm: Number(mm) })
      })
        .then((r) => toast(`CALIBRATION FACTOR: ${Number(r.calibration_immediate).toFixed(4)} (hit ${mm}mm)`, "ok"))
        .catch((e) => toast("CALIBRATE FAILED: " + e.message, "err"));
    } else if (action === "thresholds") {
      const input = window.prompt("Alert thresholds (orange, yellow, red):", `${thresholds.orange}, ${thresholds.yellow}, ${thresholds.red}`);
      if (!input) return;
      const parts = input.split(",").map((s) => Number(s.trim()));
      if (parts.length === 3 && parts.every(Number.isFinite)) {
        setThresholds({ orange: parts[0], yellow: parts[1], red: parts[2] });
        toast(`THRESHOLDS: ${parts[0]}/${parts[1]}/${parts[2]}mm`);
      }
    }
  }

  return (
    <>
      {!auth ? (
        <LoginScreen onAuth={handleAuth} onGuest={handleGuest} />
      ) : (
        <>
      <div className="wallpaper" />
      <div className="desktop">
        {ICONS.map((ic) => (
          <button
            key={ic.id}
            className="icon"
            onClick={() => openWin(ic.open)}
            onDoubleClick={() => toggleMax(ic.open)}
          >
            {ic.label === "Geo Data" && (
              <svg viewBox="0 0 32 24" width="34" height="26">
                <rect x="2" y="4" width="28" height="18" rx="1" fill="#ffd966" stroke="#6a0dad" strokeWidth="1.5" />
                <rect x="2" y="4" width="8" height="3" fill="#ffd966" stroke="#6a0dad" strokeWidth="1.5" />
                <line x1="8" y1="12" x2="24" y2="12" stroke="#6a0dad" strokeWidth="1.5" />
                <line x1="8" y1="16" x2="18" y2="16" stroke="#6a0dad" strokeWidth="1.5" />
              </svg>
            )}
            {ic.label === "Cutterhead" && (
              <svg viewBox="0 0 32 24" width="34" height="26">
                <rect x="1" y="2" width="12" height="20" rx="1" fill="#c0c0c0" stroke="#008080" strokeWidth="1.5" />
                <rect x="1" y="2" width="12" height="8" fill="#a0d8ef" stroke="#008080" strokeWidth="1.5" />
                <rect x="18" y="6" width="13" height="16" rx="1" fill="#ff00ff" stroke="#6a0dad" strokeWidth="1.5" />
                <rect x="21" y="10" width="7" height="5" fill="#0a0a2a" stroke="#6a0dad" strokeWidth="1.5" />
                <rect x="2" y="13" width="10" height="4" rx="1" fill="#6a0dad" />
              </svg>
            )}
            {ic.label === "Risk Reports" && (
              <svg viewBox="0 0 32 24" width="34" height="26">
                <path d="M16 1 L31 22 H1 Z" fill="#ffb3c8" stroke="#6a0dad" strokeWidth="1.5" />
                <rect x="14.5" y="8" width="3" height="7" fill="#ff00ff" stroke="#6a0dad" strokeWidth="0.8" />
                <rect x="14.5" y="17" width="3" height="2" fill="#ff00ff" stroke="#6a0dad" strokeWidth="0.8" />
              </svg>
            )}
            {ic.label === "Settlement" && (
              <svg viewBox="0 0 32 24" width="34" height="26">
                <rect x="2" y="4" width="28" height="18" rx="1" fill="#b8f4e0" stroke="#008080" strokeWidth="1.5" />
                <polyline points="5,18 11,14 16,16 22,9 28,10" fill="none" stroke="#ff00ff" strokeWidth="1.5" />
                <polyline points="5,18 12,16 17,17 23,12 28,13" fill="none" stroke="#ffff00" strokeWidth="1.5" />
              </svg>
            )}
            {ic.label === "Cyber Twin" && (
              <svg viewBox="0 0 32 24" width="34" height="26">
                <rect x="2" y="3" width="28" height="18" rx="1" fill="#0a0a2a" stroke="#00ffff" strokeWidth="1.5" />
                <ellipse cx="16" cy="12" rx="9" ry="6.5" fill="none" stroke="#ff00ff" strokeWidth="1.5" />
                <circle cx="16" cy="12" r="2" fill="#ff00ff" />
                <line x1="6" y1="20" x2="12" y2="9" stroke="#00ffff" strokeWidth="1" />
                <line x1="26" y1="20" x2="20" y2="9" stroke="#00ffff" strokeWidth="1" />
                <rect x="4" y="2" width="7" height="2" fill="#00ffff" opacity="0.8" />
                <rect x="21" y="2" width="7" height="2" fill="#ff00ff" opacity="0.8" />
              </svg>
            )}
            {ic.label === "TBM Dash" && (
              <svg viewBox="0 0 32 24" width="34" height="26">
                <rect x="5" y="3" width="22" height="18" rx="2" fill="#3a4152" stroke="#ff7711" strokeWidth="1.5" />
                <rect x="5" y="3" width="22" height="6" rx="1" fill="none" stroke="#00ffff" strokeWidth="1" opacity="0.6" />
                <circle cx="16" cy="12" r="6.2" fill="#ff8822" stroke="#ff5500" strokeWidth="1.5" />
                <circle cx="16" cy="12" r="1.6" fill="#ffdd88" />
                <line x1="16" y1="6" x2="16" y2="18" stroke="#ffdd88" strokeWidth="1" />
                <line x1="10" y1="12" x2="22" y2="12" stroke="#ffdd88" strokeWidth="1" />
                <line x1="21" y1="21" x2="26" y2="21" stroke="#00ff88" strokeWidth="1.2" strokeDasharray="2 2" />
              </svg>
            )}
            {ic.label === "SHM" && (
              <svg viewBox="0 0 32 24" width="34" height="26">
                <rect x="2" y="4" width="28" height="18" rx="1" fill="#0a0a2a" stroke="#00cc66" strokeWidth="1.5" />
                <polyline points="4,14 9,14 12,8 15,17 18,11 21,15 28,15" fill="none" stroke="#00ff88" strokeWidth="1.8" />
                <circle cx="4" cy="20" r="1.4" fill="#ff00ff" />
                <circle cx="28" cy="20" r="1.4" fill="#00ffff" />
              </svg>
            )}
            {ic.label === "Anomaly AI" && (
              <svg viewBox="0 0 32 24" width="34" height="26">
                <rect x="2" y="4" width="28" height="18" rx="1" fill="#101020" stroke="#ff00ff" strokeWidth="1.5" />
                <polyline points="4,16 9,16 12,6 15,14 18,10 21,13 28,13" fill="none" stroke="#ff2d6f" strokeWidth="1.8" />
                <circle cx="12" cy="6" r="2" fill="#ff2d6f" />
                <circle cx="18" cy="10" r="2" fill="#ffff00" />
              </svg>
            )}
            {ic.label === "Transfer" && (
              <svg viewBox="0 0 32 24" width="34" height="26">
                <rect x="2" y="4" width="28" height="18" rx="1" fill="#fff" stroke="#008080" strokeWidth="1.5" />
                <rect x="4" y="8" width="8" height="9" fill="#ff00ff" stroke="#6a0dad" strokeWidth="1" />
                <rect x="20" y="8" width="8" height="9" fill="#00cc66" stroke="#008080" strokeWidth="1" />
                <text x="11" y="15" fontSize="7" fill="#6a0dad" fontFamily="Courier New">A</text>
                <text x="24" y="15" fontSize="7" fill="#008080" fontFamily="Courier New">B</text>
                <line x1="13" y1="12.5" x2="19" y2="12.5" stroke="#6a0dad" strokeWidth="1.5" markerEnd="url(#arr)" />
                <polygon points="19,11 21,12.5 19,14" fill="#6a0dad" />
              </svg>
            )}
            {ic.label === "Spatial" && (
              <svg viewBox="0 0 32 24" width="34" height="26">
                <rect x="2" y="3" width="28" height="18" rx="1" fill="#101020" stroke="#00ffff" strokeWidth="1.5" />
                <circle cx="16" cy="12" r="6" fill="none" stroke="#ff00ff" strokeWidth="1.5" />
                <circle cx="16" cy="12" r="1.6" fill="#ff00ff" />
                <line x1="16" y1="2" x2="16" y2="8" stroke="#00ffff" strokeWidth="1.5" />
                <line x1="16" y1="16" x2="16" y2="22" stroke="#00ffff" strokeWidth="1.5" />
                <line x1="7" y1="12" x2="11" y2="12" stroke="#00ffff" strokeWidth="1.5" />
                <line x1="21" y1="12" x2="25" y2="12" stroke="#00ffff" strokeWidth="1.5" />
              </svg>
            )}
            {ic.label === "Report" && (
              <svg viewBox="0 0 32 24" width="34" height="26">
                <rect x="2" y="3" width="28" height="18" rx="1" fill="#fff" stroke="#6a0dad" strokeWidth="1.5" />
                <rect x="6" y="6" width="20" height="2.4" fill="#ff00ff" />
                <rect x="6" y="10" width="14" height="1.6" fill="#008080" />
                <rect x="6" y="13" width="18" height="1.6" fill="#008080" />
                <rect x="6" y="16" width="11" height="1.6" fill="#ff8800" />
              </svg>
            )}
            {ic.label === "AI Assist" && (
              <svg viewBox="0 0 32 24" width="34" height="26">
                <rect x="2" y="3" width="28" height="18" rx="2" fill="#0a0a2a" stroke="#00ffff" strokeWidth="1.5" />
                <circle cx="12" cy="10" r="3.2" fill="none" stroke="#ff00ff" strokeWidth="1.5" />
                <circle cx="20" cy="10" r="3.2" fill="none" stroke="#ff00ff" strokeWidth="1.5" />
                <circle cx="12" cy="10" r="1.2" fill="#ff00ff" />
                <circle cx="20" cy="10" r="1.2" fill="#ff00ff" />
                <path d="M12 15 q4 3.4 8 0" fill="none" stroke="#00ffff" strokeWidth="1.5" />
                <rect x="14.5" y="2" width="3" height="2.2" fill="#00ffff" opacity="0.9" />
                <rect x="14.5" y="19.8" width="3" height="2.2" fill="#ff00ff" opacity="0.9" />
              </svg>
            )}
            {ic.label === "Autodrive" && (
              <svg viewBox="0 0 32 24" width="34" height="26">
                <rect x="2" y="3" width="28" height="18" rx="1" fill="#101020" stroke="#ff8800" strokeWidth="1.5" />
                <polyline points="4,16 9,16 12,7 15,14 19,9 22,13 28,13" fill="none" stroke="#ff8800" strokeWidth="1.8" />
                <circle cx="12" cy="7" r="2" fill="#ffff00" />
                <path d="M5 20 h22" stroke="#ff00ff" strokeWidth="1.5" strokeDasharray="2 2" />
              </svg>
            )}
            {ic.label === "Grout-Sim" && (
              <svg viewBox="0 0 32 24" width="34" height="26">
                <rect x="2" y="3" width="28" height="18" rx="1" fill="#0a0a2a" stroke="#00cc66" strokeWidth="1.5" />
                <path d="M7 17 q3 -6 6 0 t6 0 t6 0" fill="none" stroke="#00ff88" strokeWidth="1.8" />
                <path d="M7 17 h18" stroke="#ff00ff" strokeWidth="1" strokeDasharray="2 2" />
                <circle cx="7" cy="17" r="1.4" fill="#ff00ff" />
                <circle cx="25" cy="17" r="1.4" fill="#ff00ff" />
              </svg>
            )}
            {ic.label === "X-Ray" && (
              <svg viewBox="0 0 32 24" width="34" height="26">
                <rect x="2" y="3" width="28" height="18" rx="1" fill="#0a0a2a" stroke="#00ffff" strokeWidth="1.5" />
                <rect x="6" y="7" width="20" height="10" fill="#101028" stroke="#00ffff" strokeWidth="1" />
                <circle cx="12" cy="12" r="2.4" fill="#ff2d6f" />
                <circle cx="18" cy="10" r="2.4" fill="#ffff00" />
                <circle cx="22" cy="14" r="2.4" fill="#00cc66" />
                <line x1="16" y1="5" x2="16" y2="19" stroke="#ff00ff" strokeWidth="0.8" strokeDasharray="1 2" />
              </svg>
            )}
            {ic.label === "Ring-Eye" && (
              <svg viewBox="0 0 32 24" width="34" height="26">
                <rect x="2" y="3" width="28" height="18" rx="1" fill="#0a0a2a" stroke="#ff00ff" strokeWidth="1.5" />
                <ellipse cx="16" cy="12" rx="8" ry="6" fill="none" stroke="#00ffff" strokeWidth="1.5" />
                <ellipse cx="16" cy="12" rx="8" ry="6" fill="none" stroke="#ff2d6f" strokeWidth="1.5" transform="rotate(20 16 12)" />
                <circle cx="16" cy="12" r="1.4" fill="#ff00ff" />
              </svg>
            )}
            {ic.label === "Geology" && (
              <svg viewBox="0 0 32 24" width="34" height="26">
                <rect x="2" y="2" width="28" height="20" rx="1" fill="#3a2a1a" stroke="#8B6914" strokeWidth="1.5" />
                <rect x="2" y="2" width="28" height="4" fill="#C4A97D" />
                <rect x="2" y="6" width="28" height="5" fill="#8B6914" />
                <rect x="2" y="11" width="28" height="5" fill="#CD853F" />
                <rect x="2" y="16" width="28" height="6" fill="#DEB887" />
                <line x1="16" y1="2" x2="16" y2="22" stroke="#00ffff" strokeWidth="1.5" strokeDasharray="2 2" />
                <circle cx="16" cy="12" r="3" fill="none" stroke="#ff00ff" strokeWidth="1.5" />
              </svg>
            )}
            {ic.label === "Cutter AI" && (
              <svg viewBox="0 0 32 24" width="34" height="26">
                <circle cx="16" cy="12" r="10" fill="#101020" stroke="#ff00ff" strokeWidth="1.5" />
                <circle cx="16" cy="12" r="3" fill="#666" stroke="#00ffff" strokeWidth="1" />
                <line x1="16" y1="2" x2="16" y2="5" stroke="#00cc66" strokeWidth="2" />
                <line x1="16" y1="19" x2="16" y2="22" stroke="#00cc66" strokeWidth="2" />
                <line x1="6" y1="12" x2="9" y2="12" stroke="#ffaa00" strokeWidth="2" />
                <line x1="23" y1="12" x2="26" y2="12" stroke="#ff4444" strokeWidth="2" />
                <circle cx="16" cy="2" r="1.5" fill="#00cc66" />
                <circle cx="16" cy="22" r="1.5" fill="#00cc66" />
                <circle cx="6" cy="12" r="1.5" fill="#ffaa00" />
                <circle cx="26" cy="12" r="1.5" fill="#ff4444" />
              </svg>
            )}
            {ic.label === "GIS Map" && (
              <svg viewBox="0 0 32 24" width="34" height="26">
                <rect x="2" y="2" width="28" height="20" rx="1" fill="#0a1628" stroke="#ff00ff" strokeWidth="1.5" />
                <polyline points="6,18 10,14 16,15 22,8 26,10" fill="none" stroke="#ff00ff" strokeWidth="2" />
                <circle cx="16" cy="12" r="2" fill="#00ffff" />
                <line x1="26" y1="4" x2="26" y2="10" stroke="#00ffff" strokeWidth="1.5" />
                <line x1="23" y1="7" x2="29" y2="7" stroke="#00ffff" strokeWidth="1.5" />
                <text x="24" y="6" fontSize="5" fill="#00ffff" fontFamily="Courier New">N</text>
              </svg>
            )}
            {ic.label === "AR View" && (
              <svg viewBox="0 0 32 24" width="34" height="26">
                <rect x="2" y="2" width="28" height="20" rx="2" fill="#101020" stroke="#00ffff" strokeWidth="1.5" />
                <circle cx="16" cy="12" r="6" fill="none" stroke="#ff00ff" strokeWidth="1.5" />
                <line x1="16" y1="4" x2="16" y2="8" stroke="#00ffff" strokeWidth="1.5" />
                <line x1="16" y1="16" x2="16" y2="20" stroke="#00ffff" strokeWidth="1.5" />
                <line x1="8" y1="12" x2="12" y2="12" stroke="#00ffff" strokeWidth="1.5" />
                <line x1="20" y1="12" x2="24" y2="12" stroke="#00ffff" strokeWidth="1.5" />
                <circle cx="16" cy="12" r="1.5" fill="#ff00ff" />
              </svg>
            )}
            {ic.label === "Voice" && (
              <svg viewBox="0 0 32 24" width="34" height="26">
                <rect x="2" y="2" width="28" height="20" rx="1" fill="#101020" stroke="#00cc66" strokeWidth="1.5" />
                <rect x="13" y="6" width="6" height="10" rx="3" fill="#00cc66" />
                <path d="M10 14 Q10 20 16 20 Q22 20 22 14" fill="none" stroke="#00cc66" strokeWidth="1.5" />
                <line x1="16" y1="20" x2="16" y2="22" stroke="#00cc66" strokeWidth="1.5" />
                <circle cx="8" cy="10" r="1" fill="#ff00ff" />
                <circle cx="24" cy="10" r="1" fill="#ff00ff" />
              </svg>
            )}
            <span>{ic.label}</span>
          </button>
        ))}
      </div>

      {Object.values(windows).map((w) => (
        <Window
          key={w.id}
          id={w.id}
          title={w.title}
          x={w.x}
          y={w.y}
          z={w.z}
          open={w.open}
          minimized={w.minimized}
          maximized={w.maximized}
          onFocus={focus}
          onClose={close}
          onToggleMin={toggleMin}
          onToggleMax={toggleMax}
          onMove={move}
          bodyClass={w.id === "search-results" ? "search-body" : undefined}
        >
          {w.id === "win-sensor" && (
            <Equalizer values={metrics} station={currentStation} ring={currentRing} playing={playing} />
          )}
          {w.id === "win-camera" && <CctvFeed />}
          {w.id === "win-alerts" && (
            <AlertsLog
              calculated={data.calculated}
              thresholds={thresholds}
              sources={[...RISK_SOURCES, ...xrayAlerts]}
            />
          )}
          {w.id === "win-controls" && <Controls shield={data.shield} onToast={toast} />}
          {w.id === "win-settlement" && <SettlementChart calculated={data.calculated} />}
          {w.id === "win-twin" && <DigitalTwin onToast={toast} />}
          {w.id === "win-dashboard" && <TbmDashboard shield={data.shield} onToast={toast} />}
          {w.id === "win-shm" && <ShmMonitor onToast={toast} />}
          {w.id === "win-anomaly" && <AnomalyEngine onToast={toast} />}
          {w.id === "win-transfer" && <ExperienceTransfer onToast={toast} />}
          {w.id === "win-spatial" && <SpatialPlanner onToast={toast} />}
          {w.id === "win-report" && <ReportGenerator onToast={toast} />}
          {w.id === "win-ai" && <AiAssistant onAction={runAssistantAction} onToast={toast} />}
          {w.id === "win-autodrive" && <Autodrive onToast={toast} />}
          {w.id === "win-grout" && <GroutSim onToast={toast} />}
          {w.id === "win-xray" && <XrayMap onToast={toast} />}
          {w.id === "win-ringeye" && <RingEye onToast={toast} />}
          {w.id === "win-geology" && <GeologyView onToast={toast} />}
          {w.id === "win-cutter" && <CutterWear onToast={toast} />}
          {w.id === "win-gis" && <GisView onToast={toast} />}
          {w.id === "win-ar" && <AROverlay onToast={toast} />}
          {w.id === "win-voice" && (
            <VoiceCommand
              onNavigate={(id) => {
                openWin(id);
                focus(id);
              }}
              onQuery={(endpoint) => {
                toast(`QUERYING: ${endpoint}`, "ok");
              }}
              onToast={toast}
            />
          )}
          {w.id === "search-results" && (
            <div className="alert-list">
              {!searchResults && <div className="alert-row sev-notice"><span className="alert-desc">TYPE A QUERY AND PRESS FIND</span></div>}
              {searchResults && searchResults.hits.length === 0 && (
                <div className="alert-row sev-notice"><span className="alert-desc">NO MATCHES FOR "{searchResults.query}"</span></div>
              )}
              {searchResults && searchResults.hits.map((h, i) => (
                <div className={`alert-row sev-${h.sev}`} key={i}>
                  <span className="alert-desc">{h.desc}</span>
                </div>
              ))}
            </div>
          )}
        </Window>
      ))}

      <SearchDock data={data} thresholds={thresholds} onResults={handleSearchResults} onToast={toast} />
      <Taskbar
        windows={Object.values(windows).map((w) => ({ id: w.id, title: w.title, open: w.open, minimized: w.minimized }))}
        onToggle={toggleMin}
        sysMsg={sysMsg}
        user={auth}
        onLogout={handleLogout}
      />
      <ContextMenu onAction={contextAction} />
      <Toasts toasts={toasts} onDismiss={(id) => setToasts((p) => p.filter((t) => t.id !== id))} />
        </>
      )}
    </>
  );
}
