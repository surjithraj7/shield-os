import { useState } from "react";
import { API_BASE, ENDPOINTS, getAuthToken, getJSON } from "../api";

export default function ReportGenerator({ onToast }) {
  const [busy, setBusy] = useState(false);
  const [summary, setSummary] = useState(null);

  async function fetchSummary() {
    const [shm, spatial, anomaly] = await Promise.all([
      getJSON(ENDPOINTS.shmSummary).catch(() => null),
      getJSON(ENDPOINTS.spatialClearances).catch(() => null),
      getJSON(ENDPOINTS.anomalyScan).catch(() => null)
    ]);
    setSummary({ shm, spatial, anomaly });
  }

  function downloadHtml() {
    setBusy(true);
    fetch(API_BASE + ENDPOINTS.reportRegulatory, {
      headers: { Authorization: getAuthToken() ? `Bearer ${getAuthToken()}` : "" }
    })
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.blob();
      })
      .then((blob) => {
        const a = document.createElement("a");
        a.href = URL.createObjectURL(blob);
        a.download = "shield_regulatory_report.html";
        a.click();
        URL.revokeObjectURL(a.href);
        onToast("REGULATORY REPORT EXPORTED (OPEN IN BROWSER / PRINT TO PDF)", "ok");
        fetchSummary();
      })
      .catch((e) => onToast("REPORT FAILED: " + e.message, "err"))
      .finally(() => setBusy(false));
  }

  return (
    <div className="report-layout">
      <div className="twin-hud">
        <div className="twin-hud-title">AUTO-REGULATORY REPORTING ENGINE</div>
        <div className="report-copy">
          One-click generation of a compliance report covering settlement validation vs the &lt;5%
          error target (Beijing Metro Line 12 benchmark: predicted 4.2 mm vs monitored 4.4 mm),
          alarm distribution, structural health monitoring, spatial clearance envelopes and ML
          anomaly screening.
        </div>
        <div className="report-actions">
          <button className="btn chunky btn-apply report-export" onClick={downloadHtml} disabled={busy}>
            {busy ? "GENERATING..." : "EXPORT COMPLIANCE REPORT (HTML)"}
          </button>
          <button className="btn chunky" onClick={() => { fetchSummary(); onToast("SUMMARY REFRESHED", "ok"); }}>
            REFRESH SUMMARY
          </button>
        </div>
      </div>

      <div className="adv-cards">
        <div className="adv-card">
          <div className="adv-card-title">SHM ALERTS</div>
          <div className="adv-card-big">{summary && summary.shm ? summary.shm.total_alerts : "--"}</div>
          <div className="adv-card-small">post-construction sensors</div>
        </div>
        <div className="adv-card">
          <div className="adv-card-title">CRITICAL CLEARANCES</div>
          <div className="adv-card-big">{summary && summary.spatial ? summary.spatial.critical_count : "--"}</div>
          <div className="adv-card-small">spatial envelope</div>
        </div>
        <div className="adv-card">
          <div className="adv-card-title">ML ANOMALIES</div>
          <div className="adv-card-big">{summary && summary.anomaly ? summary.anomaly.total_flagged : "--"}</div>
          <div className="adv-card-small">pre-alarm screening</div>
        </div>
      </div>

      <div className="report-note">
        TIP: open the exported .html in a browser and use Print &rarr; Save as PDF for a signed,
        print-ready regulatory deliverable.
      </div>
    </div>
  );
}
