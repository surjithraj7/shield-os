import { useEffect, useRef, useState } from "react";
import { ENDPOINTS, getJSON } from "../api";

const ASSET_COLORS = { safe: "#00cc66", warning: "#ffff00", critical: "#ff2d6f" };

function heatColor(t) {
  const stops = [
    [0.0, [10, 40, 20]],
    [0.25, [0, 204, 102]],
    [0.5, [255, 136, 0]],
    [0.75, [255, 255, 0]],
    [1.0, [255, 45, 111]]
  ];
  const i = t <= 0 ? 0 : t >= 1 ? stops.length - 2 : 0;
  const a = stops[i];
  const b = stops[i + 1];
  const f = (t - a[0]) / Math.max(1e-9, b[0] - a[0]);
  return [Math.round(a[1][0] + (b[1][0] - a[1][0]) * f), Math.round(a[1][1] + (b[1][1] - a[1][1]) * f), Math.round(a[1][2] + (b[1][2] - a[1][2]) * f)];
}

function drawMap(canvas, data) {
  const ctx = canvas.getContext("2d");
  const W = canvas.width;
  const H = canvas.height;
  ctx.clearRect(0, 0, W, H);
  ctx.fillStyle = "#0a0a1a";
  ctx.fillRect(0, 0, W, H);

  const pad = 28;
  const iw = W - pad - 14;
  const ih = H - pad - 14;

  if (!data || !data.map) {
    ctx.fillStyle = "#0f0";
    ctx.font = "12px Courier New";
    ctx.fillText("NO X-RAY MAP - START BACKEND", 40, H / 2);
    return;
  }

  const { stations_m, y_m, surface_mm } = data.map;
  const maxMM = Math.max(1, data.max_settlement_mm);
  const xs = (s) => pad + (s / Math.max(1e-9, stations_m[stations_m.length - 1])) * iw;
  const ys = (o) => pad + ih / 2 - (o / Math.max(1e-9, y_m[y_m.length - 1])) * (ih / 2);

  const cellW = iw / (stations_m.length - 1);
  const cellH = ih / (y_m.length - 1);
  for (let i = 0; i < stations_m.length - 1; i++) {
    for (let j = 0; j < y_m.length - 1; j++) {
      const v = (surface_mm[i][j] + surface_mm[i][j + 1]) / 2;
      const [r, g, b] = heatColor(v / maxMM);
      ctx.fillStyle = `rgb(${r},${g},${b})`;
      ctx.fillRect(xs(stations_m[i]), ys(y_m[j]), cellW + 0.5, cellH + 0.5);
    }
  }

  ctx.strokeStyle = "#00ffff";
  ctx.lineWidth = 1;
  ctx.setLineDash([3, 3]);
  ctx.beginPath();
  ctx.moveTo(pad, pad + ih / 2);
  ctx.lineTo(pad + iw, pad + ih / 2);
  ctx.stroke();
  ctx.setLineDash([]);

  ctx.fillStyle = "#fff";
  ctx.font = "9px Courier New";
  ctx.fillText("TUNNEL AXIS", pad + 2, pad + ih / 2 - 4);
  ctx.fillText(data.start_x + "m", pad, H - 4);
  ctx.fillText(data.end_x + "m", W - 46, H - 4);

  data.results.forEach((r) => {
    const x = xs(r.station_m);
    const y = ys(r.transverse_offset_m);
    ctx.beginPath();
    ctx.arc(x, y, r.level === "critical" ? 6 : 4, 0, Math.PI * 2);
    ctx.fillStyle = ASSET_COLORS[r.level];
    ctx.fill();
    ctx.strokeStyle = "#fff";
    ctx.lineWidth = 1;
    ctx.stroke();
    ctx.fillStyle = "#fff";
    ctx.font = "9px Courier New";
    ctx.fillText(r.name, x + 7, y - 4);
  });
}

export default function XrayMap({ onToast }) {
  const canvasRef = useRef(null);
  const [data, setData] = useState(null);
  const [tDays, setTDays] = useState(60);
  const [busy, setBusy] = useState(false);

  async function run() {
    setBusy(true);
    try {
      const res = await getJSON(ENDPOINTS.xrayMap, {
        method: "POST",
        body: JSON.stringify({ start_x: 100, end_x: 244, t_days: tDays })
      });
      setData(res);
      onToast(
        `X-RAY MAP: ${res.critical_count} CRITICAL / ${res.warning_count} WARNING`,
        res.critical_count ? "err" : "ok"
      );
    } catch (e) {
      onToast("X-RAY OFFLINE: " + e.message, "err");
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    run();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    drawMap(canvasRef.current, data);
  }, [data]);

  const critical = data ? data.results.filter((r) => r.level === "critical") : [];
  const warning = data ? data.results.filter((r) => r.level === "warning") : [];

  return (
    <div className="adv-layout">
      <div className="adv-main">
        <canvas ref={canvasRef} width="520" height="280" />
        <div className="plot-legend">
          <span className="lg lg-green">SAFE</span>
          <span className="lg lg-orange">NOTICE</span>
          <span className="lg lg-yellow">WARN</span>
          <span className="lg lg-red">CRITICAL</span>
          <span className="grout-controls" style={{ marginLeft: "auto" }}>
            <span>t={tDays}d</span>
            <input type="range" min="7" max="365" step="1" value={tDays}
              onChange={(e) => setTDays(Number(e.target.value))} />
            <button className="btn chunky btn-apply" onClick={run} disabled={busy}>
              {busy ? "MAPPING..." : "RE-SCAN STRAIN MAP"}
            </button>
          </span>
        </div>
        <div className="adv-table-wrap">
          <table className="adv-table">
            <thead>
              <tr><th>ASSET</th><th>TYPE</th><th>STATION</th><th>SETTLEMENT</th><th>STRAIN</th><th>STRESS</th><th>LEVEL</th></tr>
            </thead>
            <tbody>
              {data && data.results.map((r) => (
                <tr key={r.id}>
                  <td>{r.name}</td>
                  <td>{r.asset_type}</td>
                  <td>{Number(r.station_m).toFixed(1)}m</td>
                  <td>{r.settlement_mm}mm</td>
                  <td>{r.strain_ue}ue</td>
                  <td>{r.stress_mpa}MPa</td>
                  <td className={`sev-${r.level}`}>{r.level.toUpperCase()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
      <div className="adv-side">
        <div className="twin-hud">
          <div className="twin-hud-title">X-RAY.EXE // SPATIAL STRAIN</div>
          <div className="twin-hud-row"><span>CRITICAL</span><b className="ar-hot">{data ? data.critical_count : "--"}</b></div>
          <div className="twin-hud-row"><span>WARNING</span><b className="sev-warning">{data ? data.warning_count : "--"}</b></div>
          <div className="twin-hud-row"><span>MAX SETTLE</span><b>{data ? data.max_settlement_mm + "mm" : "--"}</b></div>
        </div>
        {critical.concat(warning).map((r, i) => (
          <div className={`alert-row sev-${r.level}`} key={i}>
            <span className="alert-desc">{r.name} - settle {r.settlement_mm}mm strain {r.strain_ue}ue</span>
          </div>
        ))}
        <div className="twin-hud">
          <div className="twin-hud-title">SAFETY CONE MODEL</div>
          <div className="twin-hud-row"><span>RADIUS</span><b>{data && data.worst ? data.worst.safety_cone.radius_m + "m" : "--"}</b></div>
          <div className="twin-hud-row"><span>TRIGGER</span><b>&gt;150ue / 10mm</b></div>
        </div>
      </div>
    </div>
  );
}
