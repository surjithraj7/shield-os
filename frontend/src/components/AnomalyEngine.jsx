import { useEffect, useState } from "react";
import { ENDPOINTS, getJSON } from "../api";

const SOURCE_LABELS = {
  settlement: "Settlement",
  thrust: "Thrust",
  torque: "Torque",
  advance_speed: "Advance Speed",
  grouting_pressure: "Grout Pressure"
};

export default function AnomalyEngine({ onToast }) {
  const [scan, setScan] = useState(null);
  const [busy, setBusy] = useState(false);

  async function run() {
    setBusy(true);
    try {
      const res = await getJSON(`${ENDPOINTS.anomalyScan}?window=10&z_threshold=2.5`);
      setScan(res);
      onToast(`ANOMALY SCAN COMPLETE - ${res.total_flagged} FLAGGED`, res.total_flagged ? "ok" : "ok");
    } catch (e) {
      onToast("ANOMALY SCAN FAILED: " + e.message, "err");
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    run();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const maxFlagged = scan ? Math.max(1, ...Object.values(scan.sources).map((s) => s.flagged_count)) : 1;

  return (
    <div className="adv-layout">
      <div className="adv-main">
        <div className="twin-hud">
          <div className="twin-hud-title">ML ANOMALY ENGINE // ROLLING Z-SCORE</div>
          <div className="anomaly-bars">
            {scan &&
              Object.entries(scan.sources).map(([key, s]) => (
                <div className="bar-row" key={key}>
                  <span className="bar-label">{SOURCE_LABELS[key] || key}</span>
                  <span className="bar-track">
                    <span
                      className={`bar-fill ${s.flagged_count ? "hot" : ""}`}
                      style={{ width: `${(s.flagged_count / maxFlagged) * 100}%` }}
                    />
                  </span>
                  <span className="bar-val">{s.flagged_count}</span>
                </div>
              ))}
          </div>
          <div className="anomaly-summary">
            <span>TOTAL FLAGGED: <b>{scan ? scan.total_flagged : "--"}</b></span>
            <span>METHOD: rolling-zscore (window {scan ? scan.window : "--"}, z&gt;{scan ? scan.z_threshold : "--"})</span>
          </div>
        </div>
        <div className="adv-table-wrap">
          <table className="adv-table">
            <thead>
              <tr><th>SOURCE</th><th>SEVERITY</th><th>VALUE</th><th>LOCAL MEAN</th><th>Z-SCORE</th></tr>
            </thead>
            <tbody>
              {scan &&
                Object.entries(scan.sources)
                  .flatMap(([key, s]) => s.flagged.map((f) => ({ key, ...f })))
                  .sort((a, b) => Math.abs(b.zscore) - Math.abs(a.zscore))
                  .slice(0, 60)
                  .map((f, i) => (
                    <tr key={i}>
                      <td>{SOURCE_LABELS[f.key] || f.key}</td>
                      <td className={`sev-${f.severity}`}>{f.severity.toUpperCase()}</td>
                      <td>{Number(f.value).toFixed(2)}</td>
                      <td>{Number(f.mean).toFixed(2)}</td>
                      <td className={Math.abs(f.zscore) >= 3 ? "ar-hot" : ""}>{Number(f.zscore).toFixed(2)}</td>
                    </tr>
                  ))}
            </tbody>
          </table>
        </div>
      </div>
      <div className="adv-side">
        <div className="twin-hud">
          <div className="twin-hud-title">DETECTION PRE-ALARM</div>
          <div className="twin-hud-row"><span>MODEL</span><b>UNSUPERVISED</b></div>
          <div className="twin-hud-row"><span>PRECURSOR</span><b>&gt; STATIC THRESHOLDS</b></div>
          <div className="twin-hud-row"><span>WINDOW</span><b>{scan ? scan.window : "--"} RINGS</b></div>
        </div>
        <button className="btn chunky btn-apply adv-run" onClick={run} disabled={busy}>
          {busy ? "SCANNING..." : "RUN ANOMALY SCAN"}
        </button>
      </div>
    </div>
  );
}
