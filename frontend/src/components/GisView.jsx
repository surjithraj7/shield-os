/**
 * FORGE3D Innovation #5: GIS Integration
 * Map view with tunnel alignment, UTM/WGS84 coordinates, spatial context
 */
import { useEffect, useRef, useState } from "react";
import { ENDPOINTS, getJSON } from "../api";

// Simple 2D map canvas renderer (no external dependencies)
function drawMap(canvas, alignment, points) {
  const ctx = canvas.getContext("2d");
  const w = canvas.width;
  const h = canvas.height;

  // Background
  ctx.fillStyle = "#0a1628";
  ctx.fillRect(0, 0, w, h);

  // Grid
  ctx.strokeStyle = "#1a2a4a";
  ctx.lineWidth = 0.5;
  for (let i = 0; i < w; i += 30) {
    ctx.beginPath();
    ctx.moveTo(i, 0);
    ctx.lineTo(i, h);
    ctx.stroke();
  }
  for (let j = 0; j < h; j += 30) {
    ctx.beginPath();
    ctx.moveTo(0, j);
    ctx.lineTo(w, j);
    ctx.stroke();
  }

  if (!points || points.length === 0) return;

  // Calculate bounds
  const lats = points.map((p) => p.wgs84.lat);
  const lons = points.map((p) => p.wgs84.lon);
  const minLat = Math.min(...lats);
  const maxLat = Math.max(...lats);
  const minLon = Math.min(...lons);
  const maxLon = Math.max(...lons);

  const latRange = maxLat - minLat || 0.01;
  const lonRange = maxLon - minLon || 0.01;
  const padding = 50;

  function toCanvas(lat, lon) {
    const x = padding + ((lon - minLon) / lonRange) * (w - 2 * padding);
    const y = h - padding - ((lat - minLat) / latRange) * (h - 2 * padding);
    return [x, y];
  }

  // Draw tunnel alignment line
  ctx.beginPath();
  ctx.strokeStyle = "#ff00ff";
  ctx.lineWidth = 3;
  points.forEach((p, i) => {
    const [x, y] = toCanvas(p.wgs84.lat, p.wgs84.lon);
    if (i === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  });
  ctx.stroke();

  // Draw chainage markers
  ctx.fillStyle = "#00ffff";
  ctx.font = "10px Courier New";
  points.forEach((p, i) => {
    if (i % 5 === 0) {
      const [x, y] = toCanvas(p.wgs84.lat, p.wgs84.lon);
      ctx.beginPath();
      ctx.arc(x, y, 4, 0, Math.PI * 2);
      ctx.fill();
      ctx.fillText(`${p.chainage_m.toFixed(0)}m`, x + 8, y - 8);
    }
  });

  // Draw origin point
  const [ox, oy] = toCanvas(alignment.origin_wgs84.lat, alignment.origin_wgs84.lon);
  ctx.beginPath();
  ctx.arc(ox, oy, 8, 0, Math.PI * 2);
  ctx.fillStyle = "#ff00ff";
  ctx.fill();
  ctx.strokeStyle = "#ffffff";
  ctx.lineWidth = 2;
  ctx.stroke();
  ctx.fillStyle = "#ffffff";
  ctx.font = "bold 12px Courier New";
  ctx.fillText("ORIGIN", ox + 12, oy + 4);

  // Compass rose
  const cx = w - 40;
  const cy = 40;
  ctx.strokeStyle = "#ff00ff";
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.moveTo(cx, cy - 20);
  ctx.lineTo(cx, cy + 20);
  ctx.moveTo(cx - 20, cy);
  ctx.lineTo(cx + 20, cy);
  ctx.stroke();
  ctx.fillStyle = "#ff00ff";
  ctx.font = "bold 14px Courier New";
  ctx.fillText("N", cx - 4, cy - 24);

  // Coordinate labels
  ctx.fillStyle = "#00ffff";
  ctx.font = "10px Courier New";
  ctx.fillText(`LAT: ${alignment.origin_wgs84.lat.toFixed(4)}°`, 10, h - 30);
  ctx.fillText(`LON: ${alignment.origin_wgs84.lon.toFixed(4)}°`, 10, h - 16);
  ctx.fillText(`UTM: ${alignment.origin_utm.zone}${alignment.origin_utm.letter} ${alignment.origin_utm.easting_m.toFixed(0)}E ${alignment.origin_utm.northing_m.toFixed(0)}N`, w - 300, h - 16);
}

export default function GisView({ onToast }) {
  const canvasRef = useRef(null);
  const [gisData, setGisData] = useState(null);
  const [selectedPoint, setSelectedPoint] = useState(null);

  useEffect(() => {
    let cancelled = false;
    async function loadGIS() {
      try {
        const res = await getJSON("/api/gis/data");
        if (cancelled) return;
        setGisData(res);

        // Draw map
        const canvas = canvasRef.current;
        if (canvas && res) {
          canvas.width = canvas.clientWidth;
          canvas.height = canvas.clientHeight;
          drawMap(canvas, res.alignment, res.points);
        }
      } catch (e) {
        if (onToast) onToast("GIS API OFFLINE", "err");
      }
    }
    loadGIS();
    return () => { cancelled = true; };
  }, [onToast]);

  const handleCanvasClick = (e) => {
    if (!gisData || !gisData.points) return;
    const canvas = canvasRef.current;
    const rect = canvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    // Find nearest point (simplified)
    const idx = Math.floor((x / canvas.width) * gisData.points.length);
    if (idx >= 0 && idx < gisData.points.length) {
      setSelectedPoint(gisData.points[idx]);
    }
  };

  return (
    <div className="geo-layout">
      <div style={{ flex: 1, display: "flex", flexDirection: "column" }}>
        <canvas
          ref={canvasRef}
          onClick={handleCanvasClick}
          style={{
            width: "100%",
            flex: 1,
            cursor: "crosshair",
            border: "1px solid #333",
          }}
        />
      </div>
      <div className="twin-panel" style={{ width: "280px" }}>
        <div className="twin-hud">
          <div className="twin-hud-title">GIS COORDINATES</div>
          {gisData && (
            <>
              <div className="twin-hud-row">
                <span>PROJECTION</span>
                <b>UTM {gisData.alignment.origin_utm.zone}{gisData.alignment.origin_utm.letter}</b>
              </div>
              <div className="twin-hud-row">
                <span>ORIGIN LAT</span>
                <b>{gisData.alignment.origin_wgs84.lat.toFixed(4)}°</b>
              </div>
              <div className="twin-hud-row">
                <span>ORIGIN LON</span>
                <b>{gisData.alignment.origin_wgs84.lon.toFixed(4)}°</b>
              </div>
              <div className="twin-hud-row">
                <span>EASTING</span>
                <b>{gisData.alignment.origin_utm.easting_m.toFixed(0)}m</b>
              </div>
              <div className="twin-hud-row">
                <span>NORTHING</span>
                <b>{gisData.alignment.origin_utm.northing_m.toFixed(0)}m</b>
              </div>
              <div className="twin-hud-row">
                <span>AZIMUTH</span>
                <b>{gisData.alignment.azimuth_deg}°</b>
              </div>
              <div className="twin-hud-row">
                <span>DEPTH</span>
                <b>{gisData.alignment.depth_m}m</b>
              </div>
              <div className="twin-hud-row">
                <span>LENGTH</span>
                <b>{gisData.alignment.chainage_end_m}m</b>
              </div>
            </>
          )}
        </div>

        {selectedPoint && (
          <div className="twin-hud">
            <div className="twin-hud-title">SELECTED POINT</div>
            <div className="twin-hud-row"><span>CHAINAGE</span><b>{selectedPoint.chainage_m}m</b></div>
            <div className="twin-hud-row"><span>LAT</span><b>{selectedPoint.wgs84.lat.toFixed(6)}°</b></div>
            <div className="twin-hud-row"><span>LON</span><b>{selectedPoint.wgs84.lon.toFixed(6)}°</b></div>
            <div className="twin-hud-row"><span>EASTING</span><b>{selectedPoint.utm.easting_m.toFixed(1)}m</b></div>
            <div className="twin-hud-row"><span>NORTHING</span><b>{selectedPoint.utm.northing_m.toFixed(1)}m</b></div>
          </div>
        )}

        <div className="twin-hud">
          <div className="twin-hud-title">ALIGNMENT POINTS</div>
          <div style={{ maxHeight: "150px", overflowY: "auto" }}>
            {gisData && gisData.points &&
              gisData.points.filter((_, i) => i % 10 === 0).map((p, i) => (
                <div
                  key={i}
                  className="twin-hud-row"
                  style={{ cursor: "pointer" }}
                  onClick={() => setSelectedPoint(p)}
                >
                  <span>{p.chainage_m}m</span>
                  <b>{p.wgs84.lat.toFixed(3)}°</b>
                </div>
              ))
            }
          </div>
        </div>
      </div>
    </div>
  );
}
