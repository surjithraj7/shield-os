/**
 * FORGE3D Innovation #8: Multi-User Annotations
 * Collaborative notes on 3D twin rings and assets
 */
import { useState, useEffect } from "react";
import { ENDPOINTS, getJSON } from "../api";

const SEVERITY_COLORS = {
  note: "#00ffff",
  warning: "#ffaa00",
  critical: "#ff0044",
  info: "#00cc66",
};

export default function Annotations({ ringNo, onToast }) {
  const [annotations, setAnnotations] = useState([]);
  const [newNote, setNewNote] = useState("");
  const [severity, setSeverity] = useState("note");
  const [showForm, setShowForm] = useState(false);

  useEffect(() => {
    // Load annotations from localStorage (per-ring)
    const key = `annotations_ring_${ringNo}`;
    const saved = localStorage.getItem(key);
    if (saved) {
      try {
        setAnnotations(JSON.parse(saved));
      } catch (e) {
        setAnnotations([]);
      }
    } else {
      setAnnotations([]);
    }
  }, [ringNo]);

  const saveAnnotations = (notes) => {
    const key = `annotations_ring_${ringNo}`;
    localStorage.setItem(key, JSON.stringify(notes));
  };

  const addAnnotation = () => {
    if (!newNote.trim()) return;
    const annotation = {
      id: Date.now(),
      text: newNote.trim(),
      severity,
      author: "operator",
      timestamp: new Date().toISOString(),
      ring_no: ringNo,
    };
    const updated = [...annotations, annotation];
    setAnnotations(updated);
    saveAnnotations(updated);
    setNewNote("");
    setShowForm(false);
    if (onToast) onToast("ANNOTATION ADDED", "ok");
  };

  const deleteAnnotation = (id) => {
    const updated = annotations.filter((a) => a.id !== id);
    setAnnotations(updated);
    saveAnnotations(updated);
  };

  return (
    <div className="annotations-panel">
      <div className="twin-hud">
        <div className="twin-hud-title">
          ANNOTATIONS - RING {ringNo}
          <button
            onClick={() => setShowForm(!showForm)}
            style={{
              float: "right",
              background: "#ff00ff",
              color: "#fff",
              border: "none",
              padding: "2px 8px",
              cursor: "pointer",
              fontFamily: "Courier New",
              fontSize: "10px",
            }}
          >
            {showForm ? "CANCEL" : "+ ADD"}
          </button>
        </div>

        {showForm && (
          <div style={{ padding: "8px", borderBottom: "1px solid #333" }}>
            <select
              value={severity}
              onChange={(e) => setSeverity(e.target.value)}
              style={{
                width: "100%",
                padding: "4px",
                background: "#1a1a2a",
                color: "#fff",
                border: "1px solid #444",
                marginBottom: "4px",
                fontFamily: "Courier New",
              }}
            >
              <option value="note">NOTE</option>
              <option value="info">INFO</option>
              <option value="warning">WARNING</option>
              <option value="critical">CRITICAL</option>
            </select>
            <textarea
              value={newNote}
              onChange={(e) => setNewNote(e.target.value)}
              placeholder="Enter annotation..."
              rows={3}
              style={{
                width: "100%",
                padding: "4px",
                background: "#1a1a2a",
                color: "#fff",
                border: "1px solid #444",
                resize: "vertical",
                fontFamily: "Courier New",
                fontSize: "11px",
              }}
            />
            <button
              onClick={addAnnotation}
              style={{
                width: "100%",
                padding: "6px",
                background: "#00cc66",
                color: "#fff",
                border: "none",
                cursor: "pointer",
                fontFamily: "Courier New",
                fontWeight: "bold",
                marginTop: "4px",
              }}
            >
              SAVE ANNOTATION
            </button>
          </div>
        )}

        <div style={{ maxHeight: "200px", overflowY: "auto" }}>
          {annotations.length === 0 && (
            <div className="twin-hud-row">
              <span>NO ANNOTATIONS</span>
            </div>
          )}
          {annotations.map((a) => (
            <div
              key={a.id}
              className="twin-hud-row"
              style={{
                borderLeft: `3px solid ${SEVERITY_COLORS[a.severity]}`,
                padding: "4px 8px",
                position: "relative",
              }}
            >
              <div style={{ fontSize: "10px", color: SEVERITY_COLORS[a.severity] }}>
                [{a.severity.toUpperCase()}] {a.author}
              </div>
              <div style={{ fontSize: "11px", color: "#fff" }}>{a.text}</div>
              <div style={{ fontSize: "9px", color: "#666" }}>
                {new Date(a.timestamp).toLocaleString()}
              </div>
              <button
                onClick={() => deleteAnnotation(a.id)}
                style={{
                  position: "absolute",
                  top: "2px",
                  right: "2px",
                  background: "none",
                  border: "none",
                  color: "#ff4444",
                  cursor: "pointer",
                  fontSize: "10px",
                }}
              >
                X
              </button>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
