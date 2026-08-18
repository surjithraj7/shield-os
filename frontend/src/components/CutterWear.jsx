/**
 * FORGE3D Innovation #3: Predictive Cutter Wear AI Dashboard
 * Real-time cutter health monitoring, wear prediction, maintenance scheduling
 */
import { useEffect, useRef, useState } from "react";
import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import { ENDPOINTS, getJSON } from "../api";

const CUTTER_POSITIONS = [
  0.3, 0.6, 0.9, 1.2, 1.5, 1.8, 2.1, 2.4, 2.7, 3.0, 3.2, 3.0
];

const HEALTH_COLORS = {
  good: 0x00cc66,
  moderate: 0xffaa00,
  worn: 0xff4444,
  critical: 0xff0044,
};

function buildCutterModel(cutters) {
  const group = new THREE.Group();
  group.name = "cutter-model";

  // Base plate
  const baseGeo = new THREE.CylinderGeometry(3.4, 3.4, 0.3, 48);
  const baseMat = new THREE.MeshStandardMaterial({ color: 0x333344, roughness: 0.5, metalness: 0.8 });
  const base = new THREE.Mesh(baseGeo, baseMat);
  base.rotation.x = Math.PI / 2;
  group.add(base);

  // Hub
  const hubGeo = new THREE.CylinderGeometry(0.8, 0.8, 1.0, 24);
  const hubMat = new THREE.MeshStandardMaterial({ color: 0x666677, metalness: 0.9, roughness: 0.3 });
  const hub = new THREE.Mesh(hubGeo, hubMat);
  hub.rotation.x = Math.PI / 2;
  hub.position.z = 0.5;
  group.add(hub);

  // Individual cutters
  if (cutters) {
    cutters.forEach((c) => {
      const angle = (c.cutter_id / 12) * Math.PI * 2;
      const x = Math.cos(angle) * c.position_radius_m;
      const y = Math.sin(angle) * c.position_radius_m;

      // Cutter disc
      const discGeo = new THREE.TorusGeometry(0.25, 0.08, 8, 24);
      const color = HEALTH_COLORS[c.wear_category] || 0x00cc66;
      const discMat = new THREE.MeshStandardMaterial({
        color: color,
        emissive: color,
        emissiveIntensity: 0.4,
      });
      const disc = new THREE.Mesh(discGeo, discMat);
      disc.position.set(x, y, 0.3);
      disc.rotation.y = Math.PI / 2;
      disc.name = `cutter-${c.cutter_id}`;
      group.add(disc);

      // Wear indicator ring (scaled by remaining life)
      const lifeRadius = 0.3 * (c.remaining_life_pct / 100);
      const ringGeo = new THREE.RingGeometry(lifeRadius, lifeRadius + 0.05, 16);
      const ringMat = new THREE.MeshBasicMaterial({
        color: color,
        side: THREE.DoubleSide,
      });
      const ring = new THREE.Mesh(ringGeo, ringMat);
      ring.position.set(x, y, 0.5);
      ring.name = `ring-${c.cutter_id}`;
      group.add(ring);
    });
  }

  return group;
}

export default function CutterWear({ onToast }) {
  const mountRef = useRef(null);
  const holderRef = useRef(null);
  const [wearData, setWearData] = useState(null);
  const [loading, setLoading] = useState(false);
  const sceneRef = useRef(null);
  const cutterRef = useRef(null);

  // Initialize Three.js scene
  useEffect(() => {
    const holder = holderRef.current;
    const mount = mountRef.current;
    if (!holder || !mount) return;

    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x0a0a1a);
    scene.fog = new THREE.Fog(0x0a0a1a, 30, 60);
    sceneRef.current = scene;

    const camera = new THREE.PerspectiveCamera(55, mount.clientWidth / mount.clientHeight, 0.1, 200);
    camera.position.set(5, 4, 8);

    const renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setSize(mount.clientWidth, mount.clientHeight);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    mount.appendChild(renderer.domElement);

    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.update();

    scene.add(new THREE.AmbientLight(0x404060, 0.8));
    const sun = new THREE.DirectionalLight(0xffffff, 1.2);
    sun.position.set(5, 10, 5);
    scene.add(sun);

    const grid = new THREE.GridHelper(20, 20, 0xff00ff, 0x008080);
    grid.position.y = -2;
    scene.add(grid);

    const cutterGroup = new THREE.Group();
    cutterGroup.name = "cutter-model";
    scene.add(cutterGroup);
    cutterRef.current = cutterGroup;

    let raf = 0;
    function animate() {
      raf = requestAnimationFrame(animate);
      controls.update();
      renderer.render(scene, camera);
    }
    animate();

    function onResize() {
      camera.aspect = mount.clientWidth / mount.clientHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(mount.clientWidth, mount.clientHeight);
    }
    window.addEventListener("resize", onResize);

    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener("resize", onResize);
      controls.dispose();
      mount.removeChild(renderer.domElement);
      renderer.dispose();
    };
  }, []);

  // Run wear prediction
  const runPrediction = async () => {
    setLoading(true);
    try {
      const res = await getJSON("/api/cutter/wear", {
        method: "POST",
        body: JSON.stringify({
          ring_no: 120,
          chainage_m: 192.0,
          thrust_kn: 12000,
          torque_knm: 2000,
          advance_speed_mm_min: 45,
          ucS_mpa: 30,
          cerchar_ai: 1.5,
          n_cutters: 12,
        }),
      });
      setWearData(res);

      // Update 3D model
      const scene = sceneRef.current;
      if (scene) {
        const old = scene.getObjectByName("cutter-model");
        if (old) scene.remove(old);
        const group = buildCutterModel(res.cutters);
        scene.add(group);
        cutterRef.current = group;
      }

      if (onToast) onToast("CUTTER WEAR ANALYSIS COMPLETE", "ok");
    } catch (e) {
      if (onToast) onToast("CUTTER WEAR API OFFLINE", "err");
    }
    setLoading(false);
  };

  // Auto-run on mount
  useEffect(() => {
    runPrediction();
  }, []);

  return (
    <div className="geo-layout">
      <div className="twin-3d" ref={holderRef}>
        <div ref={mountRef} className="twin-3d-mount" />
        <div className="twin-3d-label">CUTTER WEAR 3D MODEL</div>
      </div>
      <div className="twin-panel">
        <div className="twin-hud">
          <div className="twin-hud-title">CUTTER WEAR AI</div>
          <button
            onClick={runPrediction}
            disabled={loading}
            style={{
              width: "100%",
              padding: "8px",
              background: loading ? "#333" : "#ff00ff",
              color: "#fff",
              border: "none",
              cursor: loading ? "wait" : "pointer",
              fontFamily: "Courier New",
              fontWeight: "bold",
              marginBottom: "8px",
            }}
          >
            {loading ? "ANALYZING..." : "RUN WEAR PREDICTION"}
          </button>
        </div>

        {wearData && (
          <>
            <div className="twin-hud">
              <div className="twin-hud-title">OVERALL HEALTH</div>
              <div className="twin-hud-row">
                <span>FLEET HEALTH</span>
                <b style={{ color: wearData.overall_health_pct > 50 ? "#00cc66" : "#ff4444" }}>
                  {wearData.overall_health_pct}%
                </b>
              </div>
              <div className="twin-hud-row">
                <span>WORST CUTTER</span>
                <b>#{wearData.worst_cutter_id} @ {wearData.worst_cutter_health_pct}%</b>
              </div>
              <div className="twin-hud-row">
                <span>RINGS TO MAINT.</span>
                <b>{wearData.estimated_rings_to_maintenance}</b>
              </div>
            </div>

            <div className="twin-hud">
              <div className="twin-hud-title">RECOMMENDATION</div>
              <div style={{ padding: "6px", color: "#fff", fontSize: "11px", lineHeight: "1.4" }}>
                {wearData.maintenance_recommendation}
              </div>
            </div>

            {wearData.alerts && wearData.alerts.length > 0 && (
              <div className="twin-hud">
                <div className="twin-hud-title">ALERTS</div>
                {wearData.alerts.map((a, i) => (
                  <div
                    key={i}
                    className={`twin-hud-row`}
                    style={{ color: a.severity === "critical" ? "#ff0044" : "#ffaa00" }}
                  >
                    <b>{a.message}</b>
                  </div>
                ))}
              </div>
            )}

            <div className="twin-hud">
              <div className="twin-hud-title">CUTTER DETAILS</div>
              <div style={{ maxHeight: "200px", overflowY: "auto" }}>
                {wearData.cutters.map((c) => (
                  <div key={c.cutter_id} className="twin-hud-row" style={{ fontSize: "10px" }}>
                    <span>
                      #{c.cutter_id} ({c.position_radius_m.toFixed(1)}m)
                    </span>
                    <b style={{ color: HEALTH_COLORS[c.wear_category] }}>
                      {c.remaining_life_pct}%
                    </b>
                  </div>
                ))}
              </div>
            </div>
          </>
        )}

        <div className="twin-legend">
          <span className="lg lg-green">GOOD</span>
          <span className="lg lg-orange">MODERATE</span>
          <span className="lg lg-yellow">WORN</span>
          <span className="lg lg-red">CRITICAL</span>
        </div>
      </div>
    </div>
  );
}
