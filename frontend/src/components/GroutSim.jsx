import { useEffect, useRef, useState } from "react";
import { ENDPOINTS, getJSON } from "../api";

const T_HOURS = [0, 0.5, 1, 2, 3, 4, 5, 6, 7, 8, 10, 12, 16, 20, 24, 36, 48];

function drawCurves(canvas, series) {
  const ctx = canvas.getContext("2d");
  const W = canvas.width;
  const H = canvas.height;
  ctx.clearRect(0, 0, W, H);
  ctx.fillStyle = "#0a0a1a";
  ctx.fillRect(0, 0, W, H);

  ctx.strokeStyle = "#1f1f3a";
  ctx.lineWidth = 1;
  for (let gx = 0; gx <= W; gx += 50) {
    ctx.beginPath(); ctx.moveTo(gx, 0); ctx.lineTo(gx, H); ctx.stroke();
  }
  for (let gy = 0; gy <= H; gy += 30) {
    ctx.beginPath(); ctx.moveTo(0, gy); ctx.lineTo(W, gy); ctx.stroke();
  }

  if (!series) {
    ctx.fillStyle = "#0f0";
    ctx.font = "12px Courier New";
    ctx.fillText("NO GROUT DATA - START BACKEND", 40, H / 2);
    return;
  }

  const tMax = Math.max(...series.t_hours);
  const X = (t) => 34 + (t / tMax) * (W - 70);
  const seriesDefs = [
    { key: "hardening_fraction", color: "#ff00ff", label: "HARDENING 0-1", norm: (v) => v },
    { key: "stiffness_mpa", color: "#ffff00", label: "E(t) MPa", norm: (v) => v / 12 },
    { key: "effective_volume_loss_pct", color: "#ff8800", label: "EFF LOSS %", norm: (v) => v / 0.13 }
  ];

  seriesDefs.forEach((def) => {
    ctx.strokeStyle = def.color;
    ctx.lineWidth = 2;
    ctx.beginPath();
    series.t_hours.forEach((t, i) => {
      const x = X(t);
      const y = H - 16 - def.norm(series[def.key][i]) * (H - 40);
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    });
    ctx.stroke();
  });

  ctx.fillStyle = "#fff";
  ctx.font = "9px Courier New";
  ctx.fillText("0h", 34, H - 4);
  ctx.fillText(tMax + "h", W - 40, H - 4);
}

export default function GroutSim({ onToast }) {
  const canvasRef = useRef(null);
  const [series, setSeries] = useState(null);
  const [impact, setImpact] = useState(null);
  const [tHours, setTHours] = useState(6);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let cancelled = false;
    getJSON(ENDPOINTS.groutHydration, {
      method: "POST",
      body: JSON.stringify({ t_hours: T_HOURS })
    })
      .then((r) => { if (!cancelled) setSeries(r); })
      .catch(() => {});
    return () => { cancelled = true; };
  }, []);

  useEffect(() => {
    drawCurves(canvasRef.current, series);
  }, [series, tHours]);

  async function runImpact() {
    setBusy(true);
    try {
      const res = await getJSON(ENDPOINTS.groutImpact, {
        method: "POST",
        body: JSON.stringify({ station: -30, t_grout_hours: tHours })
      });
      setImpact(res);
      onToast(`GROUT-SIM @${tHours}h: E=${res.stiffness_mpa}MPa, REDUCTION ${Number(res.reduction_pct).toFixed(1)}%`, "ok");
    } catch (e) {
      onToast("GROUT-SIM FAILED: " + e.message, "err");
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    runImpact();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const idx = series ? series.t_hours.indexOf(tHours) : -1;
  const live = idx >= 0 ? {
    visc: series.viscosity_pas[idx],
    stiff: series.stiffness_mpa[idx],
    hard: series.hardening_fraction[idx]
  } : null;

  return (
    <div className="adv-layout">
      <div className="adv-main">
        <canvas ref={canvasRef} width="520" height="240" />
        <div className="plot-legend">
          <span className="lg lg-pink">HARDENING</span>
          <span className="lg lg-yellow">STIFFNESS E(t)</span>
          <span className="lg lg-orange">EFF LOSS</span>
        </div>
        <div className="grout-controls">
          <span>GROUT AGE: {tHours}h</span>
          <input type="range" min="0" max="24" step="1" value={tHours}
            onChange={(e) => setTHours(Number(e.target.value))} />
          <button className="btn chunky btn-apply" onClick={runImpact} disabled={busy}>
            {busy ? "SIMULATING..." : "RUN HYDRATION IMPACT"}
          </button>
        </div>
        <div className="grout-grid">
          <div className="grout-cell">
            <span>VISCOSITY</span>
            <b>{live ? Number(live.visc).toFixed(1) : "--"} Pa.s</b>
            <small>{tHours < 4 ? "LIQUID / PUMPABLE" : "GELING"}</small>
          </div>
          <div className="grout-cell">
            <span>STIFFNESS E(t)</span>
            <b>{impact ? Number(impact.stiffness_mpa).toFixed(1) : "--"} MPa</b>
            <small>EARLY-AGE BACKFILL STIFFNESS</small>
          </div>
          <div className="grout-cell">
            <span>HARDENING</span>
            <b>{live ? Number(live.hard * 100).toFixed(0) : "--"}%</b>
            <small>DEGREE OF BACKFILL SUPPORT</small>
          </div>
          <div className="grout-cell">
            <span>PEAK REDUCTION</span>
            <b>{impact ? Number(impact.reduction_pct).toFixed(1) : "--"}%</b>
            <small>{impact ? Number(impact.reduction_mm).toFixed(2) + "mm vs STATIC" : "vs STATIC LOSS"}</small>
          </div>
        </div>
      </div>
      <div className="adv-side">
        <div className="twin-hud">
          <div className="twin-hud-title">TWO-COMPONENT BACKFILL</div>
          <div className="twin-hud-row"><span>WINDOW</span><b>{series ? series.pumpable_window_hours : "--"}h</b></div>
          <div className="twin-hud-row"><span>GEL TIME</span><b>{series ? series.gel_time_hours : "--"}h</b></div>
          <div className="twin-hud-row"><span>E FINAL</span><b>{series ? series.final_stiffness_mpa : "--"} MPa</b></div>
          <div className="twin-hud-row"><span>EFF LOSS</span><b>{impact ? Number(impact.effective_volume_loss_pct).toFixed(3) + "%" : "--"}</b></div>
        </div>
        <div className="twin-hud">
          <div className="twin-hud-title">PHASE MODEL</div>
          <div className="twin-hud-row"><span>LIQUID</span><b>0-{series ? series.pumpable_window_hours : "--"}h</b></div>
          <div className="twin-hud-row"><span>GELATION</span><b>+{series ? series.gel_time_hours : "--"}h</b></div>
          <div className="twin-hud-row"><span>HARDENED</span><b>&gt;24h</b></div>
        </div>
      </div>
    </div>
  );
}
