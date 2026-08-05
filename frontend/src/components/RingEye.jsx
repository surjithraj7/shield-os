import { useEffect, useRef, useState } from "react";
import { ENDPOINTS, getJSON } from "../api";

function drawRing(canvas, cloud, analysis) {
  const ctx = canvas.getContext("2d");
  const W = canvas.width;
  const H = canvas.height;
  ctx.clearRect(0, 0, W, H);
  ctx.fillStyle = "#0a0a1a";
  ctx.fillRect(0, 0, W, H);

  const cx = W / 2;
  const cy = H / 2;
  const base = Math.min(W, H) * 0.4;

  ctx.strokeStyle = "#1f1f3a";
  ctx.lineWidth = 1;
  for (let r = 0.3; r <= 1; r += 0.25) {
    ctx.beginPath();
    ctx.arc(cx, cy, base * r, 0, Math.PI * 2);
    ctx.stroke();
  }
  for (let a = 0; a < 8; a++) {
    const th = (a / 8) * Math.PI * 2;
    ctx.beginPath();
    ctx.moveTo(cx, cy);
    ctx.lineTo(cx + Math.cos(th) * base, cy + Math.sin(th) * base);
    ctx.stroke();
  }

  if (!cloud || !analysis) {
    ctx.fillStyle = "#0f0";
    ctx.font = "12px Courier New";
    ctx.fillText("NO SCAN DATA - RUN RING SCAN", 40, H / 2);
    return;
  }

  const nominalR = analysis.nominal_diameter_mm / 2;
  const scale = base / nominalR;
  cloud.radial_devs_mm.forEach((dev, i) => {
    const th = (cloud.angles_deg[i] * Math.PI) / 180;
    const r = (nominalR + dev) * scale;
    ctx.fillStyle = "#00ffff";
    ctx.fillRect(cx + Math.cos(th) * r - 1.5, cy + Math.sin(th) * r - 1.5, 3, 3);
  });

  ctx.strokeStyle = "#ff00ff";
  ctx.lineWidth = 1.5;
  ctx.beginPath();
  cloud.radial_devs_mm.forEach((dev, i) => {
    const th = (cloud.angles_deg[i] * Math.PI) / 180;
    const r = (nominalR + dev) * scale;
    if (i === 0) ctx.moveTo(cx + Math.cos(th) * r, cy + Math.sin(th) * r);
    else ctx.lineTo(cx + Math.cos(th) * r, cy + Math.sin(th) * r);
  });
  ctx.closePath();
  ctx.stroke();

  ctx.fillStyle = "#fff";
  ctx.font = "10px Courier New";
  ctx.fillText("ΔD = " + Number(analysis.delta_d_mm).toFixed(2) + "mm", 8, 16);
  ctx.fillText("OVALIZATION " + Number(analysis.ovalization_pct).toFixed(2) + "%", 8, 30);
  ctx.fillText("JOINT GAP " + Number(analysis.joint_gap_mm).toFixed(2) + "mm", 8, 44);
}

export default function RingEye({ onToast }) {
  const canvasRef = useRef(null);
  const [summary, setSummary] = useState(null);
  const [readings, setReadings] = useState([]);
  const [last, setLast] = useState(null);
  const [ovalization, setOvalization] = useState(12);
  const [busy, setBusy] = useState(false);

  async function load() {
    try {
      const [s, r] = await Promise.all([
        getJSON(ENDPOINTS.ringeyeSummary),
        getJSON(`${ENDPOINTS.ringeyeReadings}?limit=30`)
      ]);
      setSummary(s);
      setReadings(r);
    } catch (e) {
      onToast("RING-EYE OFFLINE: " + e.message, "err");
    }
  }

  async function runScan() {
    setBusy(true);
    try {
      const res = await getJSON(ENDPOINTS.ringeyeScan, {
        method: "POST",
        body: JSON.stringify({ ring_no: (summary && summary.latest ? summary.latest.ring_no : 30) + 1, chainage_m: 140.5, ovalization_mm: ovalization })
      });
      setLast({ ...res, cloud: res.point_cloud });
      onToast(
        `RING ${res.analysis.ring_no} ΔD=${Number(res.analysis.delta_d_mm).toFixed(1)}mm RISK=${res.analysis.seepage_risk.toUpperCase()}`,
        res.analysis.seepage_risk === "critical" ? "err" : "ok"
      );
      await load();
    } catch (e) {
      onToast("RING SCAN FAILED: " + e.message, "err");
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    drawRing(canvasRef.current, last ? last.cloud : null, last ? last.analysis : null);
  }, [last]);

  const latest = summary ? summary.latest : null;

  return (
    <div className="adv-layout">
      <div className="adv-main">
        <div className="ringeye-canvas-wrap">
          <canvas ref={canvasRef} width="300" height="280" />
          <div className="ringeye-side">
            <div className="twin-hud">
              <div className="twin-hud-title">LATEST RING {latest ? latest.ring_no : "--"}</div>
              <div className="twin-hud-row"><span>ΔD</span><b>{latest ? latest.delta_d_mm : "--"}mm</b></div>
              <div className="twin-hud-row"><span>OVAL</span><b>{latest ? latest.ovalization_pct + "%" : "--"}</b></div>
              <div className="twin-hud-row"><span>GAP</span><b>{latest ? latest.joint_gap_mm : "--"}mm</b></div>
              <div className={`twin-risk risk-${latest ? latest.seepage_risk : "safe"}`}>
                {latest ? latest.seepage_risk.toUpperCase() : "NO DATA"}
              </div>
            </div>
            <label className="ringeye-slider">
              <span>OPTICAL SCAN OVALIZATION: {ovalization}mm</span>
              <input type="range" min="0" max="40" step="1" value={ovalization}
                onChange={(e) => setOvalization(Number(e.target.value))} />
            </label>
            <button className="btn chunky btn-apply adv-run" onClick={runScan} disabled={busy}>
              {busy ? "SCANNING..." : "RUN OPTICAL RING SCAN"}
            </button>
          </div>
        </div>
        <div className="adv-table-wrap">
          <table className="adv-table">
            <thead>
              <tr><th>RING</th><th>CHAINAGE</th><th>ΔD (mm)</th><th>OVAL %</th><th>JOINT GAP</th><th>RISK</th></tr>
            </thead>
            <tbody>
              {readings.slice(0, 20).map((r) => (
                <tr key={r.id}>
                  <td>R{r.ring_no}</td>
                  <td>{Number(r.chainage_m).toFixed(1)}m</td>
                  <td>{r.delta_d_mm}</td>
                  <td>{r.ovalization_pct}</td>
                  <td>{r.joint_gap_mm}</td>
                  <td className={`sev-${r.seepage_risk}`}>{r.seepage_risk.toUpperCase()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
      <div className="adv-side">
        <div className="twin-hud">
          <div className="twin-hud-title">RING-EYE.EXE // OPTICAL</div>
          <div className="twin-hud-row"><span>SCANS</span><b>{summary ? summary.total_scans : "--"}</b></div>
          <div className="twin-hud-row"><span>ALERTS</span><b className="ar-hot">{summary ? summary.total_alerts : "--"}</b></div>
          <div className="twin-hud-row"><span>CRITICAL</span><b className="ar-hot">{summary ? summary.risk_counts.critical : "--"}</b></div>
        </div>
        <div className="twin-hud">
          <div className="twin-hud-title">SEEPAGE TRIGGER</div>
          <div className="twin-hud-row"><span>ALLOW</span><b>1.0mm</b></div>
          <div className="twin-hud-row"><span>CRITICAL</span><b>2.0mm</b></div>
          <div className="twin-hud-row"><span>SOURCE</span><b>LiDAR / AR DEPTH</b></div>
        </div>
      </div>
    </div>
  );
}
