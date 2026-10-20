import { useCallback, useEffect, useState } from "react";
import { ENDPOINTS, getJSON } from "../api";

export function classify(mm, thresholds) {
  if (mm >= thresholds.red) return "critical";
  if (mm >= thresholds.yellow) return "warning";
  if (mm >= thresholds.orange) return "notice";
  return "safe";
}

const SEV_CLASS = {
  LOW: "safe",
  MODERATE: "notice",
  HIGH: "warning",
  CRITICAL: "critical"
};

function timeLabel(value) {
  if (!value) return "--:--";
  return value.slice(11, 16);
}

export default function AlertsLog({ auth, onToast }) {
  const [alerts, setAlerts] = useState([]);
  const [summary, setSummary] = useState(null);
  const [source, setSource] = useState("PERSISTED ALERTS");
  const [error, setError] = useState(null);
  const [busyId, setBusyId] = useState(null);

  const canOperate = auth && ["admin", "operator"].includes(auth.role);

  const load = useCallback(async () => {
    try {
      const [rows, sum] = await Promise.all([
        getJSON(`${ENDPOINTS.alerts}?limit=80`),
        getJSON(ENDPOINTS.alertsSummary)
      ]);
      setAlerts(rows);
      setSummary(sum);
      setSource("PERSISTED ALERTS");
      setError(null);
    } catch (e) {
      setSource("API OFFLINE");
      setError(e.message);
    }
  }, []);

  useEffect(() => {
    load();
    const id = setInterval(load, 10000);
    return () => clearInterval(id);
  }, [load]);

  async function act(alert, action) {
    if (!canOperate) {
      onToast("LOGIN AS OPERATOR OR ADMIN TO CHANGE ALERT STATE", "err");
      return;
    }
    const note = action === "resolve"
      ? window.prompt("Resolution note (recorded in the audit log):", "Verified on site")
      : "";
    if (action === "resolve" && note == null) return;
    setBusyId(alert.id);
    try {
      await getJSON(`${ENDPOINTS.alerts}/${alert.id}/${action}`, {
        method: "POST",
        body: JSON.stringify({ note: note || "" })
      });
      onToast(`ALERT #${alert.id} ${action.toUpperCase()}D`, "ok");
      await load();
    } catch (e) {
      onToast(`${action.toUpperCase()} FAILED: ${e.message}`, "err");
    } finally {
      setBusyId(null);
    }
  }

  return (
    <>
      <div className="alert-legend">
        <span className="lg lg-green">LOW</span>
        <span className="lg lg-orange">MODERATE</span>
        <span className="lg lg-yellow">HIGH</span>
        <span className="lg lg-red">CRITICAL</span>
        <span className="iot-source">{source}</span>
      </div>
      {error && <div className="login-error">ALERT API: {error}</div>}
      <div className="alert-list">
        {alerts.length === 0 && (
          <div className="alert-row sev-notice">
            <span className="alert-desc">NO PERSISTED ALERTS. RUN THE IoT SIMULATOR TO CREATE A LABELLED DEMO EVENT.</span>
          </div>
        )}
        {alerts.slice(0, 60).map((alert) => (
          <div className={`alert-row sev-${SEV_CLASS[alert.severity] || "notice"}`} key={alert.id}>
            <span className="alert-time">{timeLabel(alert.created_at)}</span>
            <span className="alert-desc">
              <b>#{alert.id} {alert.severity}</b> {alert.title} - {alert.message}
              <br />
              <span className="iot-meta">
                STATUS {alert.status.toUpperCase()} | OCCURRENCES {alert.occurrence_count} | SOURCE {alert.source.toUpperCase()}
                {alert.acknowledged_by ? ` | ACK ${alert.acknowledged_by}` : ""}
                {alert.resolved_by ? ` | RESOLVED ${alert.resolved_by}` : ""}
              </span>
              {canOperate && alert.status !== "resolved" && (
                <span className="iot-actions">
                  <button type="button" disabled={busyId === alert.id} onClick={() => act(alert, "acknowledge")}>
                    ACK
                  </button>
                  <button type="button" disabled={busyId === alert.id} onClick={() => act(alert, "resolve")}>
                    RESOLVE
                  </button>
                </span>
              )}
            </span>
          </div>
        ))}
      </div>
      <div className="eq-footer">
        <span>ACTIVE: {summary ? summary.active : "--"} | TOTAL: {summary ? summary.total : "--"}</span>
        <span>DB-BACKED INCIDENT LOG</span>
      </div>
    </>
  );
}
