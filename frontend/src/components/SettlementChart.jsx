import { useEffect, useRef } from "react";

export default function SettlementChart({ calculated }) {
  const canvasRef = useRef(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    const W = canvas.width;
    const H = canvas.height;
    ctx.clearRect(0, 0, W, H);
    ctx.fillStyle = "#0a0a1a";
    ctx.fillRect(0, 0, W, H);

    ctx.strokeStyle = "#1f1f3a";
    ctx.lineWidth = 1;
    for (let gx = 0; gx <= W; gx += 40) {
      ctx.beginPath(); ctx.moveTo(gx, 0); ctx.lineTo(gx, H); ctx.stroke();
    }
    for (let gy = 0; gy <= H; gy += 30) {
      ctx.beginPath(); ctx.moveTo(0, gy); ctx.lineTo(W, gy); ctx.stroke();
    }

    const data = calculated.slice().reverse();
    if (data.length < 2) {
      ctx.fillStyle = "#0f0";
      ctx.font = "12px Courier New";
      ctx.fillText("NO DATA - START BACKEND & SEED DB", 40, H / 2);
      return;
    }

    const minRing = data[0].ring_no || 1;
    const maxRing = data[data.length - 1].ring_no || data.length;
    let maxMM = 8;
    data.forEach((d) => {
      const v = d.monitored_value_mm != null ? d.monitored_value_mm : d.predicted_value_mm;
      if (v > maxMM) maxMM = v;
    });
    maxMM = Math.max(8, Math.ceil(maxMM));

    const X = (r) => 40 + ((r - minRing) / Math.max(1, maxRing - minRing)) * (W - 70);
    const Y = (v) => H - 20 - (v / maxMM) * (H - 45);

    function polyline(getter, color) {
      ctx.strokeStyle = color;
      ctx.lineWidth = 2;
      ctx.beginPath();
      data.forEach((d, i) => {
        const x = X(d.ring_no);
        const y = Y(getter(d));
        if (i === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      });
      ctx.stroke();
    }
    polyline((d) => d.predicted_value_mm, "#ff00ff");
    polyline((d) => (d.monitored_value_mm != null ? d.monitored_value_mm : d.predicted_value_mm), "#ffff00");
    polyline((d) => d.consolidation_mm || 0, "#008080");

    ctx.fillStyle = "#fff";
    ctx.font = "10px Courier New";
    for (let i = 0; i <= 4; i++) {
      const m = (maxMM / 4) * i;
      ctx.fillText(Number(m).toFixed(1) + "mm", 4, Y(m) + 3);
    }
    ctx.fillText("R" + minRing, 40, H - 6);
    ctx.fillText("R" + maxRing, W - 66, H - 6);
  }, [calculated]);

  return (
    <>
      <canvas ref={canvasRef} id="settle-canvas" width="470" height="240" />
      <div className="plot-legend">
        <span className="lg lg-pink">PREDICTED</span>
        <span className="lg lg-yellow">MONITORED</span>
        <span className="lg lg-teal">CONSOLIDATION</span>
      </div>
    </>
  );
}
