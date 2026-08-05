import { useEffect, useState } from "react";
import { ENDPOINTS, getJSON } from "../api";

const LEVEL_LABELS = { safe: "SAFE", warning: "WARN", critical: "CRITICAL" };

export default function SpatialPlanner({ onToast }) {
  const [data, setData] = useState(null);
  const [assets, setAssets] = useState([]);
  const [startX, setStartX] = useState(100);
  const [endX, setEndX] = useState(244);
  const [depth, setDepth] = useState(20);

  async function load() {
    try {
      const [c, a] = await Promise.all([
        getJSON(`${ENDPOINTS.spatialClearances}?start_x=${startX}&end_x=${endX}&depth_m=${depth}`),
        getJSON(ENDPOINTS.spatialAssets)
      ]);
      setData(c);
      setAssets(a);
    } catch (e) {
      onToast("SPATIAL CHECK FAILED: " + e.message, "err");
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function removeAsset(id) {
    try {
      await getJSON(`${ENDPOINTS.spatialAssets}/${id}`, { method: "DELETE" });
      onToast(`ASSET #${id} REMOVED`, "ok");
      load();
    } catch (e) {
      onToast("DELETE FAILED: " + e.message, "err");
    }
  }

  async function addAsset() {
    const name = window.prompt("Asset name:", "New Utility");
    if (!name) return;
    const lat = window.prompt("Lateral offset (m):", "3.0");
    const ch = window.prompt("Chainage x (m):", "160");
    try {
      await getJSON(ENDPOINTS.spatialAssets, {
        method: "POST",
        body: JSON.stringify({
          name,
          asset_type: "utility",
          x_enu: Number(ch),
          y_enu: Number(lat),
          z_enu: -10,
          radius_m: 0.5,
          clearance_limit_m: 3.0,
          note: "User added"
        })
      });
      onToast(`ASSET "${name}" ADDED`, "ok");
      load();
    } catch (e) {
      onToast("ADD FAILED: " + e.message, "err");
    }
  }

  const results = data ? data.results : [];

  return (
    <div className="adv-layout">
      <div className="adv-main">
        <div className="adv-cards">
          <div className={`adv-card ${data && data.critical_count ? "hot" : ""}`} onClick={() => load()}>
            <div className="adv-card-title">CRITICAL</div>
            <div className="adv-card-big">{data ? data.critical_count : "--"}</div>
            <div className="adv-card-small">&le;60% of clearance limit</div>
          </div>
          <div className={`adv-card ${data && data.warning_count ? "warn" : ""}`} onClick={() => load()}>
            <div className="adv-card-title">WARNING</div>
            <div className="adv-card-big">{data ? data.warning_count : "--"}</div>
            <div className="adv-card-small">&le;clearance limit</div>
          </div>
          <div className="adv-card" onClick={() => load()}>
            <div className="adv-card-title">SAFE</div>
            <div className="adv-card-big">{data ? data.safe_count : "--"}</div>
            <div className="adv-card-small">{assets.length} assets surveyed</div>
          </div>
        </div>

        <div className="spatial-controls">
          <label className="editor-num"><span>START X (m)</span><input type="number" value={startX} onChange={(e) => setStartX(Number(e.target.value))} /></label>
          <label className="editor-num"><span>END X (m)</span><input type="number" value={endX} onChange={(e) => setEndX(Number(e.target.value))} /></label>
          <label className="editor-num"><span>DEPTH (m)</span><input type="number" value={depth} onChange={(e) => setDepth(Number(e.target.value))} /></label>
          <button className="btn chunky btn-apply" onClick={load}>EVALUATE</button>
          <button className="btn chunky" onClick={addAsset}>ADD ASSET</button>
        </div>

        <div className="adv-table-wrap">
          <table className="adv-table">
            <thead>
              <tr><th>ASSET</th><th>TYPE</th><th>DIST (m)</th><th>CLR (m)</th><th>LIMIT (m)</th><th>LEVEL</th><th></th></tr>
            </thead>
            <tbody>
              {results.map((r) => (
                <tr key={r.id} className={`row-${r.level}`}>
                  <td>{r.name}</td>
                  <td>{r.asset_type}</td>
                  <td>{r.distance_m}</td>
                  <td className={r.level !== "safe" ? "ar-hot" : ""}>{r.clearance_m}</td>
                  <td>{r.clearance_limit_m}</td>
                  <td className={`sev-${r.level}`}>{LEVEL_LABELS[r.level]}</td>
                  <td>
                    <button className="btn chunky editor-mini editor-mini-del" onClick={() => removeAsset(r.id)}>DEL</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
      <div className="adv-side">
        <div className="twin-hud">
          <div className="twin-hud-title">SHIELD VECTOR PATH</div>
          <div className="twin-hud-row"><span>START</span><b>{data ? `(${data.centerline.start.map((v) => Number(v).toFixed(0)).join(", ")})` : "--"}</b></div>
          <div className="twin-hud-row"><span>END</span><b>{data ? `(${data.centerline.end.map((v) => Number(v).toFixed(0)).join(", ")})` : "--"}</b></div>
          <div className="twin-hud-row"><span>LENGTH</span><b>{data ? `${data.centerline.length_m}m` : "--"}</b></div>
        </div>
        <div className="twin-hud">
          <div className="twin-hud-title">NEAREST ASSET</div>
          {data && data.nearest ? (
            <>
              <div className="twin-hud-row"><span>{data.nearest.name}</span><b className={data.nearest.level !== "safe" ? "ar-hot" : ""}>{data.nearest.clearance_m}m</b></div>
              <div className="twin-hud-row"><span>LEVEL</span><b>{LEVEL_LABELS[data.nearest.level]}</b></div>
            </>
          ) : (
            <div className="editor-empty">NO ASSETS</div>
          )}
        </div>
      </div>
    </div>
  );
}
