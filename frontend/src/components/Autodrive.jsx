import { useEffect, useState } from "react";
import { ENDPOINTS, getJSON } from "../api";

export default function Autodrive({ onToast }) {
  const [advisory, setAdvisory] = useState(null);
  const [busy, setBusy] = useState(false);

  async function run() {
    setBusy(true);
    try {
      const res = await getJSON(ENDPOINTS.autodriveAdvisory);
      setAdvisory(res);
      const n = res.recommendations.length;
      onToast(
        `AUTODRIVE: ${n} ACTION${n === 1 ? "" : "S"} FOR ${res.mode} MODE`,
        res.exhausted ? "err" : "ok"
      );
    } catch (e) {
      onToast("AUTODRIVE OFFLINE: " + e.message, "err");
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    run();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const ctx = advisory ? advisory.context : null;
  const recs = advisory ? advisory.recommendations : [];

  return (
    <div className="adv-layout">
      <div className="adv-main">
        <div className="twin-hud">
          <div className="twin-hud-title">AUTODRIVE.AI // CLOSED-LOOP PREDICT-THEN-CONTROL</div>
          <div className="twin-hud-status">
            {advisory ? `MODE: ${advisory.mode} // ${advisory.status}` : "BOOTING..."}
          </div>
          <div className="autodrive-stats">
            <div className="autodrive-stat">
              <span>PREDICTED</span>
              <b>{advisory ? Number(advisory.predicted_mm).toFixed(2) : "--"}mm</b>
            </div>
            <div className="autodrive-stat">
              <span>TARGET</span>
              <b>{advisory ? Number(advisory.target_settlement_mm).toFixed(2) : "--"}mm</b>
            </div>
            <div className="autodrive-stat">
              <span>OVERSHOOT</span>
              <b className={advisory && advisory.overshoot_mm > 0 ? "ar-hot" : ""}>
                {advisory ? Number(advisory.overshoot_mm).toFixed(2) : "--"}mm
              </b>
            </div>
            <div className="autodrive-stat">
              <span>RISK</span>
              <b className={`sev-${advisory ? advisory.risk_level : "safe"}`}>
                {advisory ? advisory.risk_level.toUpperCase() : "--"}
              </b>
            </div>
          </div>
        </div>

        <div className="adv-table-wrap">
          <table className="adv-table">
            <thead>
              <tr><th>ACTUATOR</th><th>CURRENT</th><th>RECOMMENDED</th><th>DELTA</th><th>EXPECTED RECOVERY</th></tr>
            </thead>
            <tbody>
              {recs.length === 0 && (
                <tr><td colSpan="5" className="sev-safe">NO MITIGATION REQUIRED - SETTLEMENT WITHIN TARGET</td></tr>
              )}
              {recs.map((r, i) => (
                <tr key={i}>
                  <td>{r.label}</td>
                  <td>{Number(r.current).toFixed(2)} {r.unit}</td>
                  <td className="ar-hot">→ {Number(r.recommended).toFixed(2)} {r.unit}</td>
                  <td>{r.delta > 0 ? "+" : ""}{Number(r.delta).toFixed(2)} {r.unit}</td>
                  <td>{Number(r.expected_recovery_mm).toFixed(2)}mm</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {recs.length > 0 && (
          <div className="adv-cards">
            {recs.map((r, i) => (
              <div className="adv-card" key={i}>
                <div className="adv-card-title">{r.label}</div>
                <div className="adv-card-small">{r.advice}</div>
              </div>
            ))}
          </div>
        )}
      </div>
      <div className="adv-side">
        <div className="twin-hud">
          <div className="twin-hud-title">LIVE FEED // SENSOR.EXE</div>
          <div className="twin-hud-row"><span>RING</span><b>{ctx ? ctx.ring_no : "--"}</b></div>
          <div className="twin-hud-row"><span>CHAINAGE</span><b>{ctx ? Number(ctx.chainage_m).toFixed(1) + "m" : "--"}</b></div>
          <div className="twin-hud-row"><span>MONITORED</span><b>{ctx && ctx.monitored_mm != null ? Number(ctx.monitored_mm).toFixed(2) + "mm" : "--"}</b></div>
        </div>
        <div className="twin-hud">
          <div className="twin-hud-title">ACTUATOR HEADROOM</div>
          {advisory &&
            Object.entries(advisory.actuator_capacity_mm).map(([k, v]) => (
              <div className="twin-hud-row" key={k}>
                <span>{k.toUpperCase()}</span>
                <b>{Number(v).toFixed(2)}mm</b>
              </div>
            ))}
        </div>
        <button className="btn chunky btn-apply adv-run" onClick={run} disabled={busy}>
          {busy ? "RUNNING..." : "RE-RUN ADVISORY"}
        </button>
      </div>
    </div>
  );
}
