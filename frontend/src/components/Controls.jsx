import { useState } from "react";
import { ENDPOINTS, getJSON } from "../api";

export default function Controls({ shield, onToast }) {
  const [rate, setRate] = useState(42);
  const [thrust, setThrust] = useState(12500);
  const [torque, setTorque] = useState(3800);
  const [playing, setPlaying] = useState(true);
  const [alarm, setAlarm] = useState(true);
  const [busy, setBusy] = useState(false);

  function step(dir) {
    if (!shield.length) return;
    const rows = shield.slice().reverse();
    const cur = rows[0];
    const idx = rows.findIndex((r) => r.ring_no === cur.ring_no);
    const next = rows[(idx + dir + rows.length) % rows.length];
    onToast(`RING ${next.ring_no} @ ${Number(next.chainage_m).toFixed(1)}m`);
  }

  async function apply() {
    setBusy(true);
    try {
      const r = await getJSON(ENDPOINTS.evaluate, {
        method: "POST",
        body: JSON.stringify({
          monitored_mm: 4.4,
          shield: { face_pressure_kpa: 300, volume_loss_pct: 0.13 },
          engine: { calibration_immediate: 1.0, calibration_consolidation: 1.0 }
        })
      });
      onToast(
        `MODEL: pred ${Number(r.predicted_value_mm).toFixed(2)}mm vs mon ${Number(r.monitored_value_mm).toFixed(2)}mm [${r.alert_color.toUpperCase()}]`,
        r.passes_5pct_threshold ? "ok" : "err"
      );
    } catch (e) {
      onToast("EVALUATE FAILED: " + e.message, "err");
    } finally {
      setBusy(false);
    }
  }

  const sliders = [
    { label: "ADVANCE RATE (mm/min)", value: rate, set: setRate, min: 0, max: 80, step: 1 },
    { label: "THRUST SETPOINT (kN)", value: thrust, set: setThrust, min: 0, max: 20000, step: 100 },
    { label: "TORQUE LIMIT (kNm)", value: torque, set: setTorque, min: 0, max: 6000, step: 50 }
  ];

  return (
    <>
      {sliders.map((s) => (
        <div className="ctl-row" key={s.label}>
          <span className="ctl-label">{s.label}</span>
          <input
            type="range"
            min={s.min}
            max={s.max}
            step={s.step}
            value={s.value}
            onChange={(e) => s.set(Number(e.target.value))}
          />
          <span className="ctl-value">{s.value}</span>
        </div>
      ))}
      <div className="ctl-row ctl-buttons">
        <button className="btn chunky" title="Previous ring" onClick={() => step(-1)}>&#9198;</button>
        <button className="btn chunky btn-play" title="Play / Pause" onClick={() => setPlaying((p) => !p)}>
          {playing ? "\u25B8" : "\u25BA"}
        </button>
        <button className="btn chunky" title="Next ring" onClick={() => step(1)}>&#9197;</button>
        <button className="btn chunky btn-apply" title="Apply settings to model" onClick={apply} disabled={busy}>
          {busy ? "..." : "APPLY"}
        </button>
      </div>
      <div className="ctl-row">
        <label className="switch">
          <input type="checkbox" checked={alarm} onChange={(e) => setAlarm(e.target.checked)} />
          <span className="switch-label">ALARM SYSTEM</span>
        </label>
        <span className="ctl-value">{alarm ? "ON" : "OFF"}</span>
      </div>
    </>
  );
}
