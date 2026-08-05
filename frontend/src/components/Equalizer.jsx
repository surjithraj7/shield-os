export const METRICS = [
  { key: "thrust_kn", label: "THRUST", scale: 20000, digits: 0 },
  { key: "torque_knm", label: "TORQUE", scale: 6000, digits: 0 },
  { key: "screw_rpm", label: "SCREW", scale: 16, digits: 1 },
  { key: "advance_speed_mm_min", label: "ADVANCE", scale: 80, digits: 1 },
  { key: "grouting_pressure_mpa", label: "GROUT", scale: 1, digits: 2 }
];

export default function Equalizer({ values, station, ring, playing }) {
  return (
    <>
      <div className="eq">
        {METRICS.map((m) => {
          const v = values[m.key] ?? 0;
          const pct = Math.max(4, Math.min(100, (v / m.scale) * 100));
          return (
            <div className="eq-col" key={m.key}>
              <span className="eq-val">{Number(v).toFixed(m.digits)}</span>
              <div className="eq-bar-wrap">
                <div className="eq-bar" style={{ height: `${pct}%` }} />
              </div>
              <span className="eq-name">{m.label}</span>
            </div>
          );
        })}
      </div>
      <div className="eq-footer">
        <span id="eq-station">STATION: {station}</span>
        <span id="eq-ring">RING: {ring}</span>
        <span className={`led ${playing ? "" : "paused"}`}>{playing ? "LIVE" : "PAUSE"}</span>
      </div>
    </>
  );
}
