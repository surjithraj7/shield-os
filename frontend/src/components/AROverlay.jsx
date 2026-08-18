/**
 * FORGE3D Innovation #11: AR Overlay Mode
 * Camera-based field inspection with augmented reality markers
 * Uses WebRTC getUserMedia for camera access
 */
import { useState, useRef, useEffect, useCallback } from "react";

/**
 * AR Overlay Component
 * Displays camera feed with overlaid TBM data and inspection markers
 */
export default function AROverlay({ onToast }) {
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const [cameraActive, setCameraActive] = useState(false);
  const [markers, setMarkers] = useState([]);
  const [selectedMarker, setSelectedMarker] = useState(null);
  const [inspectionData, setInspectionData] = useState({
    ring_no: 120,
    chainage_m: 192.0,
    notes: "",
    status: "pending",
  });
  const animFrameRef = useRef(null);

  const startCamera = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: "environment", width: { ideal: 1280 }, height: { ideal: 720 } },
      });
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        videoRef.current.play();
        setCameraActive(true);
        if (onToast) onToast("CAMERA ACTIVE - AR MODE ENABLED", "ok");
      }
    } catch (err) {
      console.error("Camera access denied:", err);
      if (onToast) onToast("CAMERA ACCESS DENIED", "err");
    }
  }, [onToast]);

  const stopCamera = useCallback(() => {
    if (videoRef.current && videoRef.current.srcObject) {
      videoRef.current.srcObject.getTracks().forEach((t) => t.stop());
      videoRef.current.srcObject = null;
    }
    setCameraActive(false);
    if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current);
  }, []);

  // Overlay drawing loop
  useEffect(() => {
    if (!cameraActive) return;

    const canvas = canvasRef.current;
    const video = videoRef.current;
    if (!canvas || !video) return;

    const ctx = canvas.getContext("2d");

    function drawOverlay() {
      animFrameRef.current = requestAnimationFrame(drawOverlay);

      // Draw video frame
      canvas.width = video.videoWidth || 640;
      canvas.height = video.videoHeight || 480;
      ctx.drawImage(video, 0, 0);

      // Semi-transparent overlay
      ctx.fillStyle = "rgba(0, 0, 0, 0.3)";
      ctx.fillRect(0, 0, canvas.width, canvas.height);

      // HUD elements
      ctx.fillStyle = "#ff00ff";
      ctx.font = "bold 16px Courier New";
      ctx.fillText("SHIELD-OS AR MODE", 20, 30);

      ctx.fillStyle = "#00ffff";
      ctx.font = "12px Courier New";
      ctx.fillText(`RING: ${inspectionData.ring_no}`, 20, 55);
      ctx.fillText(`CHAINAGE: ${inspectionData.chainage_m}m`, 20, 75);

      // Crosshair
      const cx = canvas.width / 2;
      const cy = canvas.height / 2;
      ctx.strokeStyle = "#ff00ff";
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.moveTo(cx - 30, cy);
      ctx.lineTo(cx + 30, cy);
      ctx.moveTo(cx, cy - 30);
      ctx.lineTo(cx, cy + 30);
      ctx.stroke();
      ctx.beginPath();
      ctx.arc(cx, cy, 20, 0, Math.PI * 2);
      ctx.stroke();

      // Inspection markers
      markers.forEach((m, i) => {
        const mx = (m.x / 100) * canvas.width;
        const my = (m.y / 100) * canvas.height;

        ctx.beginPath();
        ctx.arc(mx, my, 12, 0, Math.PI * 2);
        ctx.fillStyle = m.color || "#00cc66";
        ctx.fill();
        ctx.strokeStyle = "#ffffff";
        ctx.lineWidth = 2;
        ctx.stroke();

        ctx.fillStyle = "#ffffff";
        ctx.font = "bold 10px Courier New";
        ctx.fillText(m.label || `M${i + 1}`, mx - 8, my + 4);
      });

      // Status bar
      ctx.fillStyle = "rgba(0, 0, 0, 0.7)";
      ctx.fillRect(0, canvas.height - 40, canvas.width, 40);
      ctx.fillStyle = "#00ff88";
      ctx.font = "11px Courier New";
      ctx.fillText(`STATUS: ${inspectionData.status.toUpperCase()} | TAP TO ADD MARKER`, 20, canvas.height - 15);
    }

    drawOverlay();

    return () => {
      if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current);
    };
  }, [cameraActive, markers, inspectionData]);

  const handleCanvasClick = (e) => {
    const canvas = canvasRef.current;
    const rect = canvas.getBoundingClientRect();
    const x = ((e.clientX - rect.left) / rect.width) * 100;
    const y = ((e.clientY - rect.top) / rect.height) * 100;

    const newMarker = {
      id: Date.now(),
      x,
      y,
      label: `M${markers.length + 1}`,
      color: "#00cc66",
      timestamp: new Date().toISOString(),
      notes: "",
    };
    setMarkers([...markers, newMarker]);
    if (onToast) onToast(`MARKER ${newMarker.label} ADDED`, "ok");
  };

  const captureSnapshot = () => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const dataUrl = canvas.toDataURL("image/png");
    const a = document.createElement("a");
    a.href = dataUrl;
    a.download = `ar-capture-ring${inspectionData.ring_no}-${Date.now()}.png`;
    a.click();
    if (onToast) onToast("SNAPSHOT CAPTURED", "ok");
  };

  return (
    <div className="ar-overlay" style={{ display: "flex", flexDirection: "column", height: "100%" }}>
      <div style={{ display: "flex", gap: "4px", padding: "4px", background: "#111" }}>
        <button
          onClick={cameraActive ? stopCamera : startCamera}
          style={{
            flex: 1,
            padding: "8px",
            background: cameraActive ? "#ff0044" : "#00cc66",
            color: "#fff",
            border: "none",
            cursor: "pointer",
            fontFamily: "Courier New",
            fontWeight: "bold",
          }}
        >
          {cameraActive ? "STOP CAMERA" : "START AR CAMERA"}
        </button>
        <button
          onClick={captureSnapshot}
          disabled={!cameraActive}
          style={{
            padding: "8px 16px",
            background: cameraActive ? "#ff00ff" : "#333",
            color: "#fff",
            border: "none",
            cursor: cameraActive ? "pointer" : "not-allowed",
            fontFamily: "Courier New",
            fontWeight: "bold",
          }}
        >
          CAPTURE
        </button>
      </div>

      <div style={{ position: "relative", flex: 1, background: "#000" }}>
        <video
          ref={videoRef}
          style={{ display: "none" }}
          playsInline
          muted
        />
        <canvas
          ref={canvasRef}
          onClick={handleCanvasClick}
          style={{
            width: "100%",
            height: "100%",
            objectFit: "cover",
            cursor: "crosshair",
          }}
        />
        {!cameraActive && (
          <div
            style={{
              position: "absolute",
              inset: 0,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              color: "#666",
              fontFamily: "Courier New",
              fontSize: "14px",
            }}
          >
            CLICK "START AR CAMERA" TO BEGIN
          </div>
        )}
      </div>

      <div style={{ padding: "4px", background: "#111", maxHeight: "120px", overflowY: "auto" }}>
        <div style={{ fontSize: "10px", color: "#ff00ff", marginBottom: "4px" }}>
          MARKERS: {markers.length}
        </div>
        {markers.map((m) => (
          <div
            key={m.id}
            style={{
              display: "flex",
              justifyContent: "space-between",
              padding: "2px 4px",
              fontSize: "10px",
              color: "#fff",
              borderBottom: "1px solid #333",
            }}
          >
            <span>{m.label}</span>
            <span style={{ color: "#666" }}>{m.timestamp}</span>
            <button
              onClick={() => setMarkers(markers.filter((x) => x.id !== m.id))}
              style={{
                background: "none",
                border: "none",
                color: "#ff4444",
                cursor: "pointer",
                fontSize: "10px",
              }}
            >
              DEL
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
