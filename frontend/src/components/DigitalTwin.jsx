import { useEffect, useRef, useState } from "react";
import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import { ENDPOINTS, getJSON, twinWS } from "../api";
import {
  MuckFlowEffect,
  GroutEffect,
  DustCloudEffect,
  WaterSeepageEffect,
  ParticleEffectsManager,
} from "../effects/ParticleEffects";

const RING_LEN = 1.6;
const RING_RADIUS = 3.2;

const RISK_COLORS = {
  low: 0x00cc66,
  notice: 0xff8800,
  warning: 0xffff00,
  high: 0xff2d6f
};

function riskOf(t) {
  if (t.risk) return t.risk;
  const mm = t.monitored_mm != null ? t.monitored_mm : t.predicted_mm;
  if (mm >= 30) return "high";
  if (mm >= 20) return "warning";
  if (mm >= 10) return "notice";
  return "low";
}

function buildTwinGroup(snapshot) {
  const group = new THREE.Group();
  const rows = (snapshot && snapshot.tunnel ? snapshot.tunnel : []).slice().reverse();

  rows.slice(0, 160).forEach((r, i) => {
    const z = -2 - i * RING_LEN;
    const geo = new THREE.CylinderGeometry(RING_RADIUS, RING_RADIUS, RING_LEN * 0.94, 24, 1, true);
    const mat = new THREE.MeshStandardMaterial({
      color: RISK_COLORS[riskOf(r)],
      emissive: RISK_COLORS[riskOf(r)],
      emissiveIntensity: 0.35,
      transparent: true,
      opacity: 0.8,
      side: THREE.DoubleSide
    });
    const ring = new THREE.Mesh(geo, mat);
    ring.rotation.x = Math.PI / 2;
    ring.position.set(0, 0, z);
    ring.name = `R${r.ring_no}`;
    group.add(ring);
  });

  const cutter = new THREE.Group();
  cutter.name = "cutterhead";

  const face = new THREE.Mesh(
    new THREE.CylinderGeometry(RING_RADIUS, RING_RADIUS, 0.5, 48, 1, true),
    new THREE.MeshStandardMaterial({ color: 0x8a8a9a, roughness: 0.5, metalness: 0.6 })
  );
  face.rotation.x = Math.PI / 2;
  face.position.z = 0;
  cutter.add(face);

  const hub = new THREE.Mesh(
    new THREE.CylinderGeometry(1.0, 1.0, 1.4, 24),
    new THREE.MeshStandardMaterial({ color: 0xff00ff, emissive: 0xff00ff, emissiveIntensity: 0.6 })
  );
  hub.rotation.x = Math.PI / 2;
  hub.position.z = 0.2;
  cutter.add(hub);

  [1.6, 2.4].forEach((rad) => {
    const torus = new THREE.Mesh(
      new THREE.TorusGeometry(rad, 0.14, 10, 32),
      new THREE.MeshStandardMaterial({ color: 0xc0c0c0, metalness: 0.8, roughness: 0.3 })
    );
    torus.rotation.y = Math.PI / 2;
    torus.position.z = 0.35;
    cutter.add(torus);
  });

  const spokes = new THREE.Mesh(
    new THREE.CylinderGeometry(0.12, 0.12, RING_RADIUS * 1.8, 8),
    new THREE.MeshStandardMaterial({ color: 0xc0c0c0, metalness: 0.7, roughness: 0.4 })
  );
  spokes.rotation.x = Math.PI / 2;
  spokes.position.z = 0.35;
  cutter.add(spokes);

  const shield = new THREE.Mesh(
    new THREE.CylinderGeometry(RING_RADIUS, RING_RADIUS, 6.5, 32, 1, true),
    new THREE.MeshStandardMaterial({
      color: 0x6a0dad,
      emissive: 0x6a0dad,
      emissiveIntensity: 0.2,
      transparent: true,
      opacity: 0.55,
      side: THREE.DoubleSide
    })
  );
  shield.rotation.x = Math.PI / 2;
  shield.position.z = 3.5;
  cutter.add(shield);

  group.add(cutter);

  const beacon = new THREE.Mesh(
    new THREE.SphereGeometry(0.5, 20, 16),
    new THREE.MeshStandardMaterial({
      color: 0x00ffff,
      emissive: 0x00ffff,
      emissiveIntensity: 0.9
    })
  );
  beacon.position.set(0, RING_RADIUS + 1.2, -2);
  group.add(beacon);

  const rail1 = new THREE.Mesh(
    new THREE.CylinderGeometry(0.08, 0.08, 46, 6),
    new THREE.MeshStandardMaterial({ color: 0x008080 })
  );
  rail1.rotation.x = Math.PI / 2;
  rail1.position.set(-RING_RADIUS - 0.5, 0, -20);
  group.add(rail1);

  const rail2 = rail1.clone();
  rail2.position.x = RING_RADIUS + 0.5;
  group.add(rail2);

  return group;
}

function heatColor(t) {
  const stops = [
    [0.0, [10, 40, 20]],
    [0.25, [0, 204, 102]],
    [0.5, [255, 136, 0]],
    [0.75, [255, 255, 0]],
    [1.0, [255, 45, 111]]
  ];
  const i = t <= 0 ? 0 : t >= 1 ? stops.length - 2 : 0;
  const a = stops[i];
  const b = stops[i + 1];
  const f = (t - a[0]) / Math.max(1e-9, b[0] - a[0]);
  return `rgb(${Math.round(a[1][0] + (b[1][0] - a[1][0]) * f)},${Math.round(a[1][1] + (b[1][1] - a[1][1]) * f)},${Math.round(a[1][2] + (b[1][2] - a[1][2]) * f)})`;
}

const MAP_SCALE = 1.7;
const stationToZ = (s) => -(2 + s * MAP_SCALE);

function buildHeatmapTexture(xray) {
  const map = xray.map;
  const CW = 320;
  const CH = 200;
  const c = document.createElement("canvas");
  c.width = CW;
  c.height = CH;
  const ctx = c.getContext("2d");
  ctx.fillStyle = "#0a0a1a";
  ctx.fillRect(0, 0, CW, CH);
  if (!map) return new THREE.CanvasTexture(c);

  const { stations_m, y_m, surface_mm } = map;
  const maxMM = Math.max(1, xray.max_settlement_mm);
  const nX = stations_m.length; // rows -> world z (station)
  const nY = y_m.length; // columns -> world x (transverse)
  const cellW = CW / (nY - 1);
  const cellH = CH / (nX - 1);
  for (let j = 0; j < nX - 1; j++) {
    for (let i = 0; i < nY - 1; i++) {
      const v = (surface_mm[j][i] + surface_mm[j][i + 1]) / 2;
      ctx.fillStyle = heatColor(v / maxMM);
      ctx.fillRect(i * cellW, CH - (j + 1) * cellH, cellW + 0.5, cellH + 0.5);
    }
  }
  return new THREE.CanvasTexture(c);
}

function buildOverlayGroup(xray) {
  const group = new THREE.Group();
  group.name = "xray-overlay";
  if (!xray || !xray.map) return group;

  const texture = buildHeatmapTexture(xray);
  const planeMat = new THREE.MeshBasicMaterial({
    map: texture,
    transparent: true,
    opacity: 0.55,
    depthWrite: false
  });
  const xSpan = (xray.map.y_m[xray.map.y_m.length - 1] - xray.map.y_m[0]) || 80;
  const zSpan = (stationToZ(xray.end_x - xray.start_x) - stationToZ(0)) || -244;
  const plane = new THREE.Mesh(new THREE.PlaneGeometry(xSpan, Math.abs(zSpan)), planeMat);
  plane.rotation.x = -Math.PI / 2;
  plane.position.set(0, -RING_RADIUS - 1, stationToZ(0) - Math.abs(zSpan) / 2);
  group.add(plane);

  const RISK_COLOR = { safe: 0x00cc66, warning: 0xffff00, critical: 0xff2d6f };
  xray.results.forEach((r) => {
    const sphere = new THREE.Mesh(
      new THREE.SphereGeometry(r.level === "critical" ? 1.0 : 0.7, 16, 12),
      new THREE.MeshStandardMaterial({
        color: RISK_COLOR[r.level] || 0x00cc66,
        emissive: RISK_COLOR[r.level] || 0x00cc66,
        emissiveIntensity: 0.7
      })
    );
    sphere.position.set(r.y_enu || 0, r.z_enu != null ? r.z_enu : -6, stationToZ(r.station_m));
    sphere.name = `XRAY-${r.name}`;
    group.add(sphere);

    const cone = new THREE.Mesh(
      new THREE.CylinderGeometry(0.08, 0.08, r.safety_cone.height_m, 6, 1, true),
      new THREE.MeshBasicMaterial({
        color: RISK_COLOR[r.level] || 0x00cc66,
        transparent: true,
        opacity: 0.35
      })
    );
    cone.position.set(r.y_enu || 0, -3.2, stationToZ(r.station_m));
    group.add(cone);
  });

  return group;
}

export default function DigitalTwin({ onToast }) {
  const mountRef = useRef(null);
  const holderRef = useRef(null);
  const [snapshot, setSnapshot] = useState(null);
  const [xray, setXray] = useState(null);
  const [link, setLink] = useState("LINK: SYNCING...");
  const sceneRef = useRef(null);
  const twinRef = useRef(null);
  const overlayRef = useRef(null);
  const particlesRef = useRef(null);

  useEffect(() => {
    const holder = holderRef.current;
    const mount = mountRef.current;
    if (!holder || !mount) return;

    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x0a0a1a);
    scene.fog = new THREE.Fog(0x0a0a1a, 40, 90);
    sceneRef.current = scene;

    const camera = new THREE.PerspectiveCamera(55, mount.clientWidth / mount.clientHeight, 0.1, 300);
    camera.position.set(16, 14, 26);
    camera.lookAt(0, 0, -8);

    const renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setSize(mount.clientWidth, mount.clientHeight);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.shadowMap.enabled = true;
    mount.appendChild(renderer.domElement);

    const controls = new OrbitControls(camera, renderer.domElement);
    controls.target.set(0, 0, -8);
    controls.enableDamping = true;
    controls.maxPolarAngle = Math.PI / 2 - 0.02;
    controls.minDistance = 6;
    controls.maxDistance = 70;
    controls.update();

    const lights = [];
    lights.push(new THREE.AmbientLight(0x404060, 0.8));
    const sun = new THREE.DirectionalLight(0xffffff, 1.2);
    sun.position.set(20, 30, 20);
    sun.castShadow = true;
    scene.add(sun);
    lights.push(sun);
    const pink = new THREE.PointLight(0xff00ff, 1.4, 60);
    pink.position.set(-12, 6, -4);
    scene.add(pink);
    lights.push(pink);

    const grid = new THREE.GridHelper(120, 48, 0xff00ff, 0x008080);
    grid.position.y = -RING_RADIUS - 1;
    scene.add(grid);

    const axes = new THREE.AxesHelper(4);
    axes.position.set(-RING_RADIUS - 3, 0, 6);
    scene.add(axes);

    // FORGE3D Innovation #4: Particle Effects
    const particleManager = new ParticleEffectsManager(scene);
    particleManager.addEffect("muck", MuckFlowEffect);
    particleManager.addEffect("grout", GroutEffect, {
      position: new THREE.Vector3(0, 0, 3.5),
    });
    particleManager.addEffect("dust", DustCloudEffect);
    particlesRef.current = particleManager;

    const twinGroup = new THREE.Group();
    twinGroup.name = "twin-group";
    scene.add(twinGroup);
    twinRef.current = twinGroup;

    const raycaster = new THREE.Raycaster();
    const mouse = new THREE.Vector2();
    let hoverName = null;
    const label = holder.querySelector(".twin-3d-label");

    function onPick(e) {
      const rect = renderer.domElement.getBoundingClientRect();
      mouse.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
      mouse.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;
      raycaster.setFromCamera(mouse, camera);
      const currentTwin = twinRef.current;
      if (currentTwin) {
        const hits = raycaster.intersectObjects(currentTwin.children, true);
        const ringHit = hits.find((h) => h.object && h.object.name && h.object.name.startsWith("R"));
        if (ringHit) {
          hoverName = ringHit.object.name;
        } else {
          hoverName = null;
        }
      } else {
        hoverName = null;
      }
    }
    renderer.domElement.addEventListener("pointermove", onPick);

    let raf = 0;
    const clock = new THREE.Clock();
    function animate() {
      raf = requestAnimationFrame(animate);
      const dt = clock.getDelta();
      const t = clock.getElapsedTime();
      const group = twinRef.current;
      if (group) {
        const cutter = group.getObjectByName("cutterhead");
        if (cutter) cutter.rotation.z = t * 0.6;
        const beacon = group.children.find((c) => c.type === "Mesh" && c.geometry.type === "SphereGeometry");
        if (beacon) beacon.position.y = RING_RADIUS + 1.2 + Math.sin(t * 2) * 0.4;
      }
      // Update particle effects
      if (particlesRef.current) {
        particlesRef.current.update(dt);
      }
      controls.update();
      renderer.render(scene, camera);
      label.textContent = hoverName ? `HOVER: ${hoverName}` : "DRAG TO ORBIT // SCROLL TO ZOOM";
    }
    animate();

    function onResize() {
      const w = mount.clientWidth;
      const h = mount.clientHeight;
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
      renderer.setSize(w, h);
    }
    window.addEventListener("resize", onResize);

    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener("resize", onResize);
      renderer.domElement.removeEventListener("pointermove", onPick);
      if (particlesRef.current) particlesRef.current.dispose();
      controls.dispose();
      mount.removeChild(renderer.domElement);
      renderer.dispose();
    };
  }, []);

  useEffect(() => {
    let cancelled = false;

    function updateTwinScene(data) {
      const scene = sceneRef.current;
      if (!scene) return;
      const old = scene.getObjectByName("twin-group");
      if (old) {
        scene.remove(old);
        old.traverse((child) => {
          if (child.isMesh) {
            child.geometry?.dispose();
            if (Array.isArray(child.material)) {
              child.material.forEach((m) => m.dispose());
            } else if (child.material) {
              child.material.dispose();
            }
          }
        });
      }
      const group = buildTwinGroup(data);
      group.name = "twin-group";
      scene.add(group);
      twinRef.current = group;
    }

    // Fetch initial REST snapshot immediately for instant UI render
    getJSON(ENDPOINTS.twinSnapshot)
      .then((snap) => {
        if (cancelled || !snap) return;
        setSnapshot(snap);
        setLink(`LINK: SYNC (R${snap.current_ring} @ ${Number(snap.chainage_m).toFixed(1)}m)`);
        updateTwinScene(snap);
      })
      .catch(() => {
        if (!cancelled) setLink("LINK: SYNCING...");
      });

    // WebSocket live stream for digital twin - FORGE3D Innovation #1
    twinWS.connect();

    const unsub = twinWS.on("twin_update", (data) => {
      if (cancelled) return;
      setSnapshot(data);
      setLink(`LINK: LIVE (R${data.current_ring} @ ${Number(data.chainage_m).toFixed(1)}m)`);
      updateTwinScene(data);
    });

    // Fallback to polling if WebSocket fails
    const fallbackPoll = setInterval(async () => {
      if (twinWS.connected) return;
      try {
        const snap = await getJSON(ENDPOINTS.twinSnapshot);
        if (cancelled) return;
        setSnapshot(snap);
        setLink(`LINK: POLL (R${snap.current_ring} @ ${Number(snap.chainage_m).toFixed(1)}m)`);
        updateTwinScene(snap);
      } catch (e) {
        if (!cancelled) setLink("LINK: OFFLINE - STATIC MODEL");
      }
    }, 6000);

    return () => {
      cancelled = true;
      unsub();
      clearInterval(fallbackPoll);
    };
  }, [onToast]);

  useEffect(() => {
    let cancelled = false;
    async function loadXray() {
      try {
        const res = await getJSON(ENDPOINTS.xrayMap, {
          method: "POST",
          body: JSON.stringify({ start_x: 100, end_x: 244, t_days: 60 })
        });
        if (cancelled) return;
        setXray(res);
        const scene = sceneRef.current;
        if (scene) {
          if (overlayRef.current) {
            scene.remove(overlayRef.current);
          }
          const overlay = buildOverlayGroup(res);
          scene.add(overlay);
          overlayRef.current = overlay;
        }
      } catch (e) {
        /* X-RAY offline - no overlay */
      }
    }
    loadXray();
    const id = setInterval(loadXray, 45000);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, [onToast]);

  const s = snapshot ? snapshot.settlement : null;
  const m = snapshot ? snapshot.metrics : {};

  return (
    <>
      <div className="twin-layout">
        <div className="twin-3d" ref={holderRef}>
          <div ref={mountRef} className="twin-3d-mount" />
          <div className="twin-3d-label">BOOTING TWIN...</div>
        </div>
        <div className="twin-panel">
          <div className="twin-hud">
            <div className="twin-hud-title">CYBER TWIN</div>
            <div className="twin-hud-status">{link}</div>
            <div className="twin-hud-row"><span>RING</span><b>{snapshot ? snapshot.current_ring : "----"}</b></div>
            <div className="twin-hud-row"><span>CHAINAGE</span><b>{snapshot ? Number(snapshot.chainage_m).toFixed(1) + "m" : "----"}</b></div>
            <div className="twin-hud-row"><span>THRUST</span><b>{m.thrust_kn != null ? Number(m.thrust_kn).toFixed(0) + "kN" : "--"}</b></div>
            <div className="twin-hud-row"><span>TORQUE</span><b>{m.torque_knm != null ? Number(m.torque_knm).toFixed(0) + "kNm" : "--"}</b></div>
            <div className="twin-hud-row"><span>ADVANCE</span><b>{m.advance_speed_mm_min != null ? Number(m.advance_speed_mm_min).toFixed(1) + "mm/min" : "--"}</b></div>
            <div className="twin-hud-row"><span>GROUT</span><b>{m.grouting_pressure_mpa != null ? Number(m.grouting_pressure_mpa).toFixed(2) + "MPa" : "--"}</b></div>
            <div className="twin-hud-row"><span>FACE PRESS</span><b>{m.face_pressure_kpa != null ? Number(m.face_pressure_kpa).toFixed(0) + "kPa" : "--"}</b></div>
            <div className="twin-hud-row"><span>SCREW</span><b>{m.screw_rpm != null ? Number(m.screw_rpm).toFixed(1) + "rpm" : "--"}</b></div>
          </div>
          <div className="twin-hud">
            <div className="twin-hud-title">SETTLEMENT PREDICTED vs MONITORED</div>
            {s ? (
              <>
                <div className="twin-hud-row"><span>PREDICTED</span><b>{Number(s.predicted_mm).toFixed(2)}mm</b></div>
                <div className="twin-hud-row"><span>MONITORED</span><b>{s.monitored_mm != null ? Number(s.monitored_mm).toFixed(2) + "mm" : "--"}</b></div>
                <div className="twin-hud-row"><span>DELTA</span><b>{Number(s.difference_mm).toFixed(2)}mm</b></div>
                <div className="twin-hud-row"><span>ERR %</span><b>{Number(s.relative_error_pct).toFixed(2)}%</b></div>
                <div className={`twin-risk risk-${riskOf(s)}`}>
                  RISK: {s.risk.toUpperCase()}
                </div>
              </>
            ) : (
              <div className="twin-hud-row"><span>NO DATA</span><b>--</b></div>
            )}
          </div>
          <div className="twin-hud">
            <div className="twin-hud-title">X-RAY SPATIAL OVERLAY</div>
            <div className="twin-hud-row"><span>CRITICAL</span><b className="ar-hot">{xray ? xray.critical_count : "--"}</b></div>
            <div className="twin-hud-row"><span>WARNING</span><b className="sev-warning">{xray ? xray.warning_count : "--"}</b></div>
            <div className="twin-hud-row"><span>MAX SETTLE</span><b>{xray ? xray.max_settlement_mm + "mm" : "--"}</b></div>
          </div>
          <div className="twin-legend">
            <span className="lg lg-green">LOW</span>
            <span className="lg lg-orange">NOTICE</span>
            <span className="lg lg-yellow">WARN</span>
            <span className="lg lg-red">HIGH</span>
          </div>
        </div>
      </div>
    </>
  );
}
