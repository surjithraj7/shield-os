import { useEffect, useState } from "react";
import { ENDPOINTS, getJSON } from "../api";

function pad(n) {
  return (n < 10 ? "0" : "") + n;
}

const AR_MARKERS = [
  { x: 22, y: 30, w: 70, h: 42, color: "#00cc66", sev: "safe", label: "B-01 FOUNDATION", detail: "CLR 2.50m" },
  { x: 58, y: 18, w: 60, h: 40, color: "#ff8800", sev: "notice", label: "SEWER DN800", detail: "CLR 2.186m" },
  { x: 78, y: 62, w: 56, h: 34, color: "#ff2d6f", sev: "critical", label: "METRO L-LINE", detail: "CLR 2.10m" },
  { x: 12, y: 68, w: 54, h: 30, color: "#ffff00", sev: "warning", label: "WATER MAIN", detail: "20m AHEAD" },
  { x: 70, y: 12, w: 52, h: 26, color: "#00cc66", sev: "safe", label: "HV DUCT", detail: "CLR 4.20m" }
];

export default function CctvFeed() {
  const [ts, setTs] = useState("00:00:00");
  const [ar, setAr] = useState(false);
  const [twin, setTwin] = useState(null);

  useEffect(() => {
    const id = setInterval(() => {
      const d = new Date();
      setTs(`${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`);
    }, 1000);
    return () => clearInterval(id);
  }, []);

  useEffect(() => {
    let cancelled = false;
    getJSON(ENDPOINTS.twinSnapshot)
      .then((s) => {
        if (!cancelled) setTwin(s);
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, []);

  const settlement = twin ? twin.settlement : null;

  return (
    <div className="crt">
      <div className="crt-badge crt-live">&#9679; LIVE</div>
      <div className="crt-badge crt-rec">&#9678; REC</div>
      <div className="crt-ts">{ts}</div>
      <div className="crt-label">TUNNEL FACE CAM 01 &mdash; KM 12+080</div>
      <svg className="crt-scene" viewBox="0 0 320 200" preserveAspectRatio="xMidYMid slice" aria-hidden="true">
        <rect x="0" y="0" width="320" height="200" fill="#050510" />
        <path d="M0 200 L0 120 Q160 20 320 120 L320 200 Z" fill="#12122a" />
        <path d="M0 200 L0 135 Q160 45 320 135 L320 200 Z" fill="#1c1c3a" />
        <ellipse cx="160" cy="80" rx="60" ry="46" fill="#0a0a18" stroke="#6a0dad" strokeWidth="3" />
        <ellipse cx="160" cy="80" rx="44" ry="32" fill="#08080f" stroke="#a300a3" strokeWidth="2" />
        <circle cx="160" cy="80" r="18" fill="#ff00ff" opacity="0.25" />
        <line x1="60" y1="200" x2="60" y2="150" stroke="#008080" strokeWidth="3" />
        <line x1="260" y1="200" x2="260" y2="150" stroke="#008080" strokeWidth="3" />
        <line x1="60" y1="155" x2="260" y2="155" stroke="#008080" strokeWidth="2" />
        <line x1="60" y1="162" x2="260" y2="162" stroke="#008080" strokeWidth="2" />
        <rect x="0" y="0" width="320" height="200" fill="#ff00ff" opacity="0.04" />

        {ar &&
          AR_MARKERS.map((m, i) => (
            <g key={i} className={`ar-marker ar-${m.sev}`}>
              <rect
                x={m.x}
                y={m.y}
                width={m.w}
                height={m.h}
                fill="none"
                stroke={m.color}
                strokeWidth="1.5"
                strokeDasharray="4 2"
              />
              <rect x={m.x} y={m.y} width={m.w} height={m.h} fill={m.color} opacity="0.12" />
              <text x={m.x + 2} y={m.y + 10} fill={m.color} fontSize="7" fontFamily="Courier New" fontWeight="bold">
                {m.label}
              </text>
              <text x={m.x + 2} y={m.y + 19} fill="#fff" fontSize="6" fontFamily="Courier New">
                {m.detail}
              </text>
              <line x1={m.x + m.w / 2} y1={m.y + m.h} x2={m.x + m.w / 2} y2={m.y + m.h + 12} stroke={m.color} strokeWidth="1" />
            </g>
          ))}
      </svg>
      {ar && (
        <div className="ar-hud">
          <div className="ar-hud-title">AR FIELD OVERLAY // SUBSURFACE RISK</div>
          <div className="ar-hud-row">
            <span>RING</span><b>{twin ? twin.current_ring : "----"}</b>
          </div>
          <div className="ar-hud-row">
            <span>SETTLEMENT</span>
            <b className={settlement && settlement.risk === "high" ? "ar-hot" : ""}>
              {settlement ? `${Number(settlement.predicted_mm).toFixed(2)} / ${settlement.monitored_mm != null ? Number(settlement.monitored_mm).toFixed(2) : "--"}mm` : "----"}
            </b>
          </div>
          <div className="ar-hud-row">
            <span>RISK</span><b>{settlement ? settlement.risk.toUpperCase() : "----"}</b>
          </div>
        </div>
      )}
      <button className={`btn chunky ar-toggle ${ar ? "active" : ""}`} onClick={() => setAr((v) => !v)}>
        {ar ? "AR: ON" : "AR: OFF"}
      </button>
      <div className="crt-scanlines" aria-hidden="true" />
    </div>
  );
}
