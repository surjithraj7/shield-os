import { useCallback, useEffect, useMemo, useState } from "react";
import { ENDPOINTS, getJSON } from "../api";

const TYPE_LABELS = {
  settlement: "Settlement",
  convergence: "Convergence",
  vibration: "Vibration",
  water_pressure: "Pore Pressure",
  groundwater_level: "Groundwater",
  temperature: "Temperature",
  humidity: "Humidity",
  gas_ch4: "Methane",
  gas_co: "CO",
  crack_width: "Crack Width",
  seepage: "Seepage",
  strain: "Strain",
  tbm_thrust: "TBM Thrust",
  tbm_torque: "TBM Torque",
  tbm_face_pressure: "Face Pressure"
};

function badgeClass(value) {
  if (value === "online" || value === "active") return "shm-status ok";
  if (value === "stale" || value === "never_seen") return "shm-status warn";
  return "shm-status warn";
}

export default function IotMonitor({ auth, onToast }) {
  const [sensors, setSensors] = useState([]);
  const [health, setHealth] = useState(null);
  const [readings, setReadings] = useState([]);
  const [alerts, setAlerts] = useState(null);
  const [filter, setFilter] = useState("all");
  const [count, setCount] = useState(1);
  const [anomaly, setAnomaly] = useState(false);
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const canOperate = auth && ["admin", "operator"].includes(auth.role);

  const load = useCallback(async () => {
    try {
      const [sensorRows, healthRow, readingRows, alertSummary] = await Promise.all([
        getJSON(ENDPOINTS.iotSensors),
        getJSON(ENDPOINTS.iotHealth),
        getJSON(`${ENDPOINTS.iotReadings}?limit=120`),
        getJSON(ENDPOINTS.alertsSummary)
      ]);
      setSensors(sensorRows);
      setHealth(healthRow);
      setReadings(readingRows);
      setAlerts(alertSummary);
      setError(null);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
    const id = setInterval(load, 10000);
    return () => clearInterval(id);
  }, [load]);

  const latestBySensor = useMemo(() => {
    const map = {};
    readings.forEach((r) => {
      if (!map[r.sensor_id]) map[r.sensor_id] = r;
    });
    return map;
  }, [readings]);

  const visible = sensors.filter((s) => filter === "all" || s.sensor_type === filter);
  const simulatedCount = sensors.filter((s) => s.source === "simulated").length;
  const criticalOpen = alerts?.by_severity?.CRITICAL || 0;

  async function runSimulation() {
    if (!canOperate) {
      onToast("LOGIN AS OPERATOR OR ADMIN TO RUN THE SIMULATOR", "err");
      return;
    }
    setBusy(true);
    try {
      const qs = new URLSearchParams({
        count: String(Math.max(1, Math.min(100, Number(count) || 1))),
        anomaly: anomaly ? "true" : "false"
      });
      if (filter !== "all") qs.set("sensor_type", filter);
      const res = await getJSON(`${ENDPOINTS.iotSimulate}?${qs.toString()}`, { method: "POST" });
      onToast(
        `SIMULATED: ${res.readings_created} readings / ${res.alerts_created} new alerts (clearly labelled simulated)`,
        "ok"
      );
      await load();
    } catch (e) {
      onToast("SIMULATION FAILED: " + e.message, "err");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="adv-layout">
      <div className="adv-main">
        <div className="adv-cards">
          <div className="adv-card">
            <div className="adv-card-title">REGISTERED SENSORS</div>
            <div className="adv-card-big">{sensors.length}</div>
            <div className="adv-card-small">online {health?.connectivity_counts?.online || 0} / total</div>
          </div>
          <div className="adv-card">
            <div className="adv-card-title">SIMULATED FEEDS</div>
            <div className="adv-card-big">{simulatedCount}</div>
            <div className="adv-card-small">explicitly labelled simulated</div>
          </div>
          <div className="adv-card">
            <div className="adv-card-title">ACTIVE ALERTS</div>
            <div className="adv-card-big">{alerts?.active ?? "--"}</div>
            <div className="adv-card-small">open / acknowledged / investigating</div>
          </div>
          <div className="adv-card">
            <div className="adv-card-title">CRITICAL RECORDS</div>
            <div className="adv-card-big">{criticalOpen}</div>
            <div className="adv-card-small">requires engineering review</div>
          </div>
        </div>

        <div className="iot-toolbar">
          <label>
            TYPE
            <select value={filter} onChange={(e) => setFilter(e.target.value)}>
              <option value="all">ALL</option>
              {Object.keys(TYPE_LABELS).map((key) => (
                <option key={key} value={key}>{TYPE_LABELS[key]}</option>
              ))}
            </select>
          </label>
          <label>
            COUNT
            <input
              type="number"
              min="1"
              max="100"
              value={count}
              onChange={(e) => setCount(e.target.value)}
            />
          </label>
          <label className="iot-check">
            <input type="checkbox" checked={anomaly} onChange={(e) => setAnomaly(e.target.checked)} />
            INJECT ANOMALY
          </label>
          <button className="btn chunky" type="button" onClick={runSimulation} disabled={busy || !canOperate}>
            {busy ? "SIMULATING..." : canOperate ? "RUN SIMULATOR" : "READ ONLY"}
          </button>
          <span className="iot-source">SOURCE: SIMULATED DEMO DATA</span>
        </div>

        {error && <div className="login-error">IoT API OFFLINE: {error}</div>}

        <div className="adv-table-wrap">
          <table className="adv-table">
            <thead>
              <tr>
                <th>SENSOR</th>
                <th>TYPE</th>
                <th>LATEST</th>
                <th>UNIT</th>
                <th>CONNECTIVITY</th>
                <th>SOURCE</th>
                <th>LAST SEEN</th>
              </tr>
            </thead>
            <tbody>
              {loading && (
                <tr><td colSpan="7">LOADING SENSOR REGISTRY...</td></tr>
              )}
              {!loading && visible.length === 0 && (
                <tr><td colSpan="7">NO REGISTERED SENSORS FOR THIS TYPE</td></tr>
              )}
              {visible.map((sensor) => {
                const latest = latestBySensor[sensor.sensor_id];
                const connectivity = sensor.health?.connectivity || "unknown";
                return (
                  <tr key={sensor.sensor_id}>
                    <td>{sensor.sensor_id}</td>
                    <td>{TYPE_LABELS[sensor.sensor_type] || sensor.sensor_type}</td>
                    <td>{latest ? latest.value : "--"}</td>
                    <td>{sensor.unit}</td>
                    <td className={badgeClass(connectivity)}>{String(connectivity).toUpperCase()}</td>
                    <td>{sensor.source.toUpperCase()}</td>
                    <td>{sensor.health?.last_seen_at ? sensor.health.last_seen_at.slice(0, 19).replace("T", " ") : "NEVER"}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
      <div className="adv-side">
        <div className="twin-hud">
          <div className="twin-hud-title">INGESTION PIPELINE</div>
          <div className="twin-hud-row"><span>TRANSPORT</span><b>HTTP / WI-FI GATEWAY</b></div>
          <div className="twin-hud-row"><span>VALIDATION</span><b>UNIT + RANGE + TIME</b></div>
          <div className="twin-hud-row"><span>DEDUPE</span><b>EVENT ID</b></div>
          <div className="twin-hud-row"><span>ALERTS</span><b>{alerts?.active ?? "--"}</b></div>
        </div>
        <div className="twin-hud">
          <div className="twin-hud-title">DATA PROVENANCE</div>
          <div className="twin-hud-row"><span>REAL HARDWARE</span><b>NOT CONNECTED</b></div>
          <div className="twin-hud-row"><span>SIMULATOR</span><b>AVAILABLE</b></div>
          <div className="twin-hud-row"><span>AI RISK</span><b>RULES + Z-SCORE</b></div>
        </div>
      </div>
    </div>
  );
}
