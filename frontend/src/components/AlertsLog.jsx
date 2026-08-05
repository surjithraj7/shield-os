export function classify(mm, thresholds) {
  if (mm >= thresholds.red) return "critical";
  if (mm >= thresholds.yellow) return "warning";
  if (mm >= thresholds.orange) return "notice";
  return "safe";
}

export default function AlertsLog({ calculated, thresholds, sources }) {
  const rows = [...sources];
  calculated.forEach((r) => {
    const mm = r.monitored_value_mm != null ? r.monitored_value_mm : r.predicted_value_mm;
    rows.push({
      time: (r.timestamp || "--:--").slice(11, 16),
      sev: classify(mm, thresholds),
      desc: `R${r.ring_no} @${Number(r.chainage_m).toFixed(1)}m settle ${Number(mm).toFixed(2)}mm err ${Number(r.relative_error_pct).toFixed(1)}%`
    });
  });

  return (
    <>
      <div className="alert-legend">
        <span className="lg lg-green">SAFE</span>
        <span className="lg lg-orange">NOTICE</span>
        <span className="lg lg-yellow">WARN</span>
        <span className="lg lg-red">CRITICAL</span>
      </div>
      <div className="alert-list">
        {rows.slice(0, 60).map((r, i) => (
          <div className={`alert-row sev-${r.sev}`} key={i}>
            <span className="alert-time">{r.time}</span>
            <span className="alert-desc">{r.desc}</span>
          </div>
        ))}
      </div>
      <div className="eq-footer">
        <span>SOURCES: {rows.length}</span>
      </div>
    </>
  );
}
