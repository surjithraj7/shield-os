import { useState } from "react";
import { classify } from "./AlertsLog";

export default function SearchDock({ data, thresholds, onResults, onToast }) {
  const [q, setQ] = useState("");

  function search() {
    const query = q.trim().toLowerCase();
    if (!query) {
      onResults(null);
      return;
    }
    const hits = [];
    const push = (sev, desc) => hits.push({ sev, desc });

    data.calculated.forEach((r) => {
      if (String(r.ring_no) === query || String(r.chainage_m).indexOf(query) !== -1) {
        push(classify(r.monitored_value_mm ?? r.predicted_value_mm, thresholds),
          `CALC R${r.ring_no} @${Number(r.chainage_m).toFixed(1)}m pred ${Number(r.predicted_value_mm).toFixed(2)}mm mon ${Number(r.monitored_value_mm).toFixed(2)}mm`);
      }
    });
    data.shield.forEach((r) => {
      if (String(r.ring_no) === query || String(r.chainage_m).indexOf(query) !== -1) {
        push("safe",
          `SHIELD R${r.ring_no} thrust ${Number(r.thrust_kn).toFixed(0)}kN speed ${Number(r.advance_speed_mm_min).toFixed(1)}mm/min grout ${Number(r.grouting_pressure_mpa).toFixed(2)}MPa`);
      }
    });
    data.monitoring.forEach((r) => {
      if (String(r.ring_no) === query || String(r.chainage_m).indexOf(query) !== -1 || r.sensor_id.toLowerCase().indexOf(query) !== -1) {
        push("notice", `MON ${r.sensor_id} R${r.ring_no} value ${Number(r.measured_value_mm).toFixed(2)}mm`);
      }
    });

    onResults({ query, hits });
  }

  return (
    <div className="searchdock">
      <input
        id="search-input"
        type="text"
        placeholder="SEARCH DATABASE... e.g. ring 12 / 102.4 / thrust"
        value={q}
        onChange={(e) => setQ(e.target.value)}
        onKeyDown={(e) => { if (e.key === "Enter") search(); }}
      />
      <button id="search-btn" onClick={search}>FIND</button>
    </div>
  );
}
