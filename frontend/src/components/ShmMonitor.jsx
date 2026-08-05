import { useEffect, useState } from "react";
import { ENDPOINTS, getJSON } from "../api";

const TYPE_LABELS = {
  seepage: "Seepage",
  segment_displacement: "Segment Disp.",
  lining_strain: "Lining Strain"
};

const UNITS = {
  seepage: "m3/day",
  segment_displacement: "mm",
  lining_strain: "ue"
};

export default function ShmMonitor({ onToast }) {
  const [summary, setSummary] = useState(null);
  const [readings, setReadings] = useState([]);
  const [filter, setFilter] = useState("all");

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const [s, r] = await Promise.all([
          getJSON(ENDPOINTS.shmSummary),
          getJSON(`${ENDPOINTS.shmReadings}?limit=60`)
        ]);
        if (cancelled) return;
        setSummary(s);
        setReadings(r);
      } catch (e) {
        if (!cancelled) onToast("SHM OFFLINE: " + e.message, "err");
      }
    }
    load();
    const id = setInterval(load, 5000);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, [onToast]);

  const stats = summary ? summary.stats : {};
  const filtered = readings.filter((r) => filter === "all" || r.sensor_type === filter);

  return (
    <div className="adv-layout">
      <div className="adv-main">
        <div className="adv-cards">
          {Object.entries(TYPE_LABELS).map(([key, label]) => {
            const s = stats[key] || {};
            const unit = UNITS[key];
            return (
              <div className={`adv-card ${filter === key ? "sel" : ""}`} key={key} onClick={() => setFilter(filter === key ? "all" : key)}>
                <div className="adv-card-title">{label}</div>
                <div className="adv-card-big">{s.latest != null ? s.latest : "--"} <span>{unit}</span></div>
                <div className="adv-card-small">mean {s.mean != null ? s.mean : "--"} · count {s.count || 0}</div>
                {s.count > 0 && (
                  <svg viewBox="0 0 100 24" className="adv-spark" preserveAspectRatio="none">
                    <polyline
                      points={readings.filter((r) => r.sensor_type === key).slice(0, 40).map((r, i) => `${(i / 40) * 100},${24 - ((r.measured_value - (s.min || 0)) / Math.max(1e-6, s.max - s.min || 1)) * 22 - 1}`).join(" ")}
                      fill="none" stroke="#ff00ff" strokeWidth="1.5"
                    />
                  </svg>
                )}
              </div>
            );
          })}
        </div>
        <div className="adv-table-wrap">
          <table className="adv-table">
            <thead>
              <tr><th>SENSOR</th><th>TYPE</th><th>VALUE</th><th>UNIT</th><th>STATUS</th></tr>
            </thead>
            <tbody>
              {filtered.slice(0, 40).map((r) => (
                <tr key={r.id}>
                  <td>{r.sensor_id}</td>
                  <td>{TYPE_LABELS[r.sensor_type] || r.sensor_type}</td>
                  <td>{r.measured_value}</td>
                  <td>{r.unit}</td>
                  <td className={`shm-status ${r.status === "normal" ? "ok" : "warn"}`}>{r.status.toUpperCase()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
      <div className="adv-side">
        <div className="twin-hud">
          <div className="twin-hud-title">SHM SYSTEM // POST-CONSTRUCTION</div>
          <div className="twin-hud-row"><span>SEEPAGE</span><b>{summary ? summary.sensor_type_counts.seepage : "--"}</b></div>
          <div className="twin-hud-row"><span>SEGMENT</span><b>{summary ? summary.sensor_type_counts.segment_displacement : "--"}</b></div>
          <div className="twin-hud-row"><span>STRAIN</span><b>{summary ? summary.sensor_type_counts.lining_strain : "--"}</b></div>
          <div className="twin-hud-row"><span>ALERTS</span><b className="ar-hot">{summary ? summary.total_alerts : "--"}</b></div>
        </div>
        <div className="twin-hud">
          <div className="twin-hud-title">LIFE-CYCLE PHASE</div>
          <div className="twin-hud-row"><span>MODE</span><b>OPERATIONAL</b></div>
          <div className="twin-hud-row"><span>DOMAIN</span><b>SEEPAGE/SEGMENT/STRAIN</b></div>
        </div>
      </div>
    </div>
  );
}
