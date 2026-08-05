import { useEffect, useState } from "react";
import { ENDPOINTS, getJSON } from "../api";

export default function ExperienceTransfer({ onToast }) {
  const [geo, setGeo] = useState(1.05);
  const [result, setResult] = useState(null);
  const [history, setHistory] = useState([]);
  const [busy, setBusy] = useState(false);

  async function run(saveHistory) {
    setBusy(true);
    try {
      const res = await getJSON(ENDPOINTS.experienceRecommend, {
        method: "POST",
        body: JSON.stringify({
          source_line: "Beijing Metro Line 12",
          source_segment: "A",
          target_line: "Beijing Metro Line 12",
          target_segment: "B",
          geology_factor: geo,
          save_history: saveHistory
        })
      });
      setResult(res);
      if (saveHistory) {
        const h = await getJSON(ENDPOINTS.experienceHistory);
        setHistory(h);
        onToast("TRANSFER SAVED TO EXPERIENCE LIBRARY", "ok");
      } else {
        onToast("TRANSFER MODEL GENERATED (SEG A -> SEG B)", "ok");
      }
    } catch (e) {
      onToast("TRANSFER FAILED: " + e.message, "err");
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    getJSON(ENDPOINTS.experienceHistory)
      .then(setHistory)
      .catch(() => {});
    run(false);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const params = result ? result.params : null;

  return (
    <div className="adv-layout">
      <div className="adv-main">
        <div className="twin-hud">
          <div className="twin-hud-title">A/B/C EXPERIENCE TRANSFER LIBRARY</div>
          <div className="transfer-flow">
            <span className="tf-node">SEG A (LEFT)</span>
            <span className="tf-arrow">&#10142; ML TRANSFER &#10142;</span>
            <span className="tf-node">SEG B (RIGHT)</span>
          </div>
          <div className="transfer-controls">
            <label className="editor-num">
              <span>GEOLOGY FACTOR</span>
              <input type="number" step="0.05" min="0.5" max="2" value={geo} onChange={(e) => setGeo(Number(e.target.value))} />
            </label>
            <button className="btn chunky btn-apply" onClick={() => run(false)} disabled={busy}>
              {busy ? "RUNNING..." : "GENERATE MODEL"}
            </button>
            <button className="btn chunky" onClick={() => run(true)} disabled={busy}>
              SAVE TO LIBRARY
            </button>
          </div>
        </div>
        <div className="adv-table-wrap">
          <table className="adv-table">
            <thead>
              <tr><th>PARAMETER</th><th>RECOMMENDED</th><th>BAND LO</th><th>BAND HI</th><th>SAMPLES</th></tr>
            </thead>
            <tbody>
              {params &&
                Object.entries(params).map(([key, p]) => (
                  <tr key={key}>
                    <td>{p.label}</td>
                    <td className="rec-val">{p.median}</td>
                    <td>{p.band_lo}</td>
                    <td>{p.band_hi}</td>
                    <td>{p.confidence_samples}</td>
                  </tr>
                ))}
            </tbody>
          </table>
        </div>
      </div>
      <div className="adv-side">
        <div className="twin-hud">
          <div className="twin-hud-title">TRANSFER MODEL</div>
          <div className="twin-hud-row"><span>SOURCE</span><b>SEG A (LEFT)</b></div>
          <div className="twin-hud-row"><span>TARGET</span><b>SEG B (RIGHT)</b></div>
          <div className="twin-hud-row"><span>GEOLOGY</span><b>x{geo.toFixed(2)}</b></div>
          <div className="twin-hud-row"><span>SAMPLES</span><b>{result ? result.recommendation.source_samples : "--"}</b></div>
        </div>
        <div className="twin-hud">
          <div className="twin-hud-title">LIBRARY ({history.length})</div>
          <div className="editor-list">
            {history.length === 0 && <div className="editor-empty">EMPTY - SAVE A MODEL</div>}
            {history.map((h) => (
              <div className="editor-item" key={h.id}>
                <span className="editor-item-name">{h.source_segment}&rarr;{h.target_segment} #{h.id}</span>
                <span className="editor-item-type">{h.created_at.slice(0, 16).replace("T", " ")}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
