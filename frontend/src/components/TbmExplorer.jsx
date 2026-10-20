import { useRef, useEffect, useState, useCallback } from "react";
import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import { GLTFExporter } from "three/examples/jsm/exporters/GLTFExporter.js";

const SUBSYSTEMS = ["Cutterhead", "Main Drive", "Shield & Screw", "Thrust Ring", "Concrete Ring", "Backup Gantry"];

const SUBSYSTEM_DATA = {
  Cutterhead: {
    slots: [{ name: "Disc Cutter", qty: 62 }, { name: "Ripper", qty: 8 }, { name: "Scrapers", qty: 4 }, { name: "Flushing Nozzle", qty: 16 }],
    maintenance: 800,
    sensor: "Proximity Sensor (x24) / Vibration Sensor (x12)",
    failure: "Disc Cutter Spalling",
    failureRate: 0.04,
    condition: 0.72,
    angle: -10,
    initialPos: -2.8,
    explodedPos: -11,
    color: "#00f0ff",
  },
  "Main Drive": {
    slots: [
      { name: "Main Bearing", qty: 1 },
      { name: "Motor", qty: 8 },
      { name: "Gearbox", qty: 2 },
      { name: "Coupling", qty: 2 },
    ],
    maintenance: 5000,
    sensor: "Temperature Sensor (x16) / Oil Debris Sensor (x4)",
    failure: "Main Bearing Failure",
    failureRate: 0.01,
    condition: 0.88,
    initialPos: -0.4,
    explodedPos: -7.5,
    color: "#ff00e5",
  },
  "Shield & Screw": {
    slots: [
      { name: "Segmental Lining", qty: 6 },
      { name: "Grout Port", qty: 6 },
      { name: "Screw Conveyor", qty: 1 },
      { name: "Seal System", qty: 1 },
    ],
    maintenance: 1500,
    sensor: "Pressure Sensor (x6) / Proximity Sensor (x3)",
    failure: "Shield Seal Degradation",
    failureRate: 0.02,
    condition: 0.81,
    initialPos: 2,
    explodedPos: -2.5,
    color: "#7c3aed",
  },
  "Thrust Ring": {
    slots: [
      { name: "Hydraulic Jack", qty: 14 },
      { name: "Thrust Frame", qty: 1 },
      { name: "Swivel Joint", qty: 2 },
    ],
    maintenance: 3000,
    sensor: "Pressure Sensor (x14) / Displacement Sensor (x7)",
    failure: "Jack Cylinder Leak",
    failureRate: 0.015,
    condition: 0.92,
    initialPos: 4,
    explodedPos: 3,
    color: "#ff8800",
  },
  "Concrete Ring": {
    slots: [{ name: "Segment", qty: 6 }, { name: "Bolt", qty: 12 }, { name: "Gasket", qty: 6 }],
    maintenance: 200,
    sensor: "Strain Gauge (x12) / Inclinometer (x2)",
    failure: "Segmental Lining Crack",
    failureRate: 0.008,
    condition: 0.95,
    initialPos: 6,
    explodedPos: 8.5,
    color: "#ffcc00",
  },
  "Backup Gantry": {
    slots: [
      { name: "Trailing Gear", qty: 1 },
      { name: "Segment Erector", qty: 1 },
      { name: "Grout Pump", qty: 1 },
      { name: "Transformer", qty: 1 },
    ],
    maintenance: 1000,
    sensor: "Current Sensor (x8) / Vibration Sensor (x4)",
    failure: "Erector Arm Malfunction",
    failureRate: 0.025,
    condition: 0.65,
    initialPos: 8,
    explodedPos: 13.5,
    color: "#ff2d6f",
  },
};

const SECTION_ANGLE = Math.PI / 24;

function createSectionMaterial(angle, color) {
  const c = new THREE.Color(color);
  const canvas = document.createElement("canvas");
  canvas.width = 256;
  canvas.height = 16;
  const ctx = canvas.getContext("2d");
  ctx.fillStyle = `rgb(${Math.floor(c.r * 60)}, ${Math.floor(c.g * 60)}, ${Math.floor(c.b * 60)})`;
  ctx.fillRect(0, 0, 256, 16);
  ctx.fillStyle = `rgb(${Math.floor(c.r * 255)}, ${Math.floor(c.g * 255)}, ${Math.floor(c.b * 255)})`;
  ctx.font = "10px monospace";
  ctx.fillText(`${(angle * (180 / Math.PI)).toFixed(1)}°`, 4, 12);
  const tex = new THREE.CanvasTexture(canvas);
  tex.wrapS = THREE.RepeatWrapping;
  tex.rotation = angle;
  return new THREE.MeshStandardMaterial({ color: c, map: tex, side: THREE.DoubleSide, transparent: true, opacity: 0.75 });
}

function buildTbmGroup(mode) {
  const group = new THREE.Group();
  const step = SECTION_ANGLE;

  for (const [name, data] of Object.entries(SUBSYSTEM_DATA)) {
    const subGroup = new THREE.Group();
    subGroup.name = name;
    subGroup.userData = {
      isTbmSubpart: true,
      slot: name,
      originalColor: new THREE.Color(data.color),
    };

    const baseX = data.initialPos;
    const sections = mode === "exploded" ? 1 : 2;

    for (let i = 0; i < sections; i++) {
      const angle = i * step;
      const material = createSectionMaterial(angle, data.color);
      const shape = new THREE.Shape();
      const radius = 3.2;
      const arcHeight = 0.18;
      shape.moveTo(-radius, 0);
      shape.absarc(0, 0, radius, Math.PI, 0, false);
      shape.lineTo(radius - arcHeight, -arcHeight);
      shape.absarc(0, -arcHeight, radius - arcHeight, 0, Math.PI, true);
      shape.lineTo(-radius, 0);

      const extrudeSettings = { depth: mode === "exploded" ? 1.5 : 2.4, bevelEnabled: false };
      const geometry = new THREE.ExtrudeGeometry(shape, extrudeSettings);
      const mesh = new THREE.Mesh(geometry, material);
      mesh.rotation.y = angle;
      mesh.position.x = baseX;
      subGroup.add(mesh);
    }

    group.add(subGroup);
  }
  return group;
}

function createLabel(text, color) {
  const canvas = document.createElement("canvas");
  canvas.width = 512;
  canvas.height = 64;
  const ctx = canvas.getContext("2d");
  ctx.fillStyle = "rgba(0,0,0,0.8)";
  ctx.roundRect(0, 0, 512, 64, 8);
  ctx.fill();
  ctx.strokeStyle = color;
  ctx.lineWidth = 2;
  ctx.roundRect(2, 2, 508, 60, 7);
  ctx.stroke();
  ctx.fillStyle = color;
  ctx.font = "bold 28px 'JetBrains Mono', monospace";
  ctx.textAlign = "center";
  ctx.fillText(text.toUpperCase(), 256, 42);

  const texture = new THREE.CanvasTexture(canvas);
  const material = new THREE.SpriteMaterial({ map: texture, transparent: true, depthTest: false });
  const sprite = new THREE.Sprite(material);
  sprite.scale.set(5, 0.625, 1);
  sprite.visible = false;
  return sprite;
}

export default function TbmExplorer({ onToast }) {
  const containerRef = useRef(null);
  const sceneRef = useRef({});
  const [autoRotate, setAutoRotate] = useState(true);
  const [showLabels, setShowLabels] = useState(true);
  const [selectedSystem, setSelectedSystem] = useState(null);
  const [hoveredSystem, setHoveredSystem] = useState(null);
  const [subsystemFilter, setSubsystemFilter] = useState(() => Object.fromEntries(SUBSYSTEMS.map((s) => [s, true])));
  const [explodeLevel, setExplodeLevel] = useState(0);

  const toggleSubsystem = useCallback((name) => {
    setSubsystemFilter((prev) => ({ ...prev, [name]: !prev[name] }));
  }, []);

  const toggleAll = useCallback(() => {
    setSubsystemFilter((prev) => {
      const allOn = Object.values(prev).every(Boolean);
      return Object.fromEntries(Object.keys(prev).map((k) => [k, !allOn]));
    });
  }, []);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const scene = new THREE.Scene();
    scene.fog = new THREE.FogExp2(0x050510, 0.02);
    const camera = new THREE.PerspectiveCamera(60, container.clientWidth / container.clientHeight, 0.1, 1000);
    camera.position.set(-15, 10, 20);

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setSize(container.clientWidth, container.clientHeight);
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.25;
    container.appendChild(renderer.domElement);

    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.05;
    controls.autoRotate = true;
    controls.autoRotateSpeed = 0.4;
    controls.target.set(2.5, 0, 0);

    scene.add(new THREE.AmbientLight(0x404050, 2));
    scene.add(new THREE.HemisphereLight(0x99bbff, 0x334422, 2));

    const keys = ["x", "y", "z", "w"];
    const dirs = [new THREE.Vector3(1, 0, 0), new THREE.Vector3(0, 1, 0), new THREE.Vector3(0, 0, 1), new THREE.Vector3(-1, -1, -1)];
    dirs.forEach((dir, i) => {
      const l = new THREE.DirectionalLight(0xffffff, 2);
      l.position.copy(dir.multiplyScalar(15));
      l.castShadow = true;
      l.shadow.mapSize.width = 2048;
      l.shadow.mapSize.height = 2048;
      scene.add(l);
    });

    const groundGeom = new THREE.PlaneGeometry(200, 200);
    const groundMat = new THREE.MeshStandardMaterial({ color: 0x0a0a1a, roughness: 0.9, metalness: 0.1 });
    const ground = new THREE.Mesh(groundGeom, groundMat);
    ground.rotation.x = -Math.PI / 2;
    ground.position.y = -4;
    ground.receiveShadow = true;
    scene.add(ground);

    const gridHelper = new THREE.GridHelper(100, 50, 0x00f0ff, 0x00f0ff);
    gridHelper.position.y = -3.99;
    gridHelper.material.opacity = 0.08;
    gridHelper.material.transparent = true;
    scene.add(gridHelper);

    const tubeRadius = 3.2;
    const tubeLength = 26;
    const tubeSegments = 128;
    const radialSegments = 48;
    const tubeGeom = new THREE.CylinderGeometry(tubeRadius, tubeRadius, tubeLength, radialSegments, tubeSegments, true);
    const tubeMat = new THREE.MeshPhysicalMaterial({
      color: 0x12122a,
      roughness: 0.15,
      metalness: 0.9,
      transparent: true,
      opacity: 0.35,
      side: THREE.DoubleSide,
      depthWrite: false,
      envMapIntensity: 0.5,
    });
    const tube = new THREE.Mesh(tubeGeom, tubeMat);
    tube.rotation.z = Math.PI / 2;
    tube.position.x = tubeLength / 2 - 3;
    scene.add(tube);

    const frameCount = 30;
    const frameGroup = new THREE.Group();
    for (let i = 0; i < frameCount; i++) {
      const angle = (i / frameCount) * Math.PI * 2;
      const x = (i / frameCount) * tubeLength - 3;
      const frameGeom = new THREE.TorusGeometry(tubeRadius + 0.05, 0.04, 8, 32);
      const frameMat = new THREE.MeshStandardMaterial({ color: 0x00f0ff, transparent: true, opacity: 0.2 });
      const frame = new THREE.Mesh(frameGeom, frameMat);
      frame.rotation.y = Math.PI / 2;
      frame.position.x = x;
      frameGroup.add(frame);
    }
    scene.add(frameGroup);

    let tbmGroup = buildTbmGroup("normal");
    scene.add(tbmGroup);

    const highlightGeom = new THREE.BoxGeometry(5, 8, 8);
    const highlightMat = new THREE.MeshBasicMaterial({ color: 0x00f0ff, wireframe: true, transparent: true, opacity: 0 });
    const highlightBox = new THREE.Mesh(highlightGeom, highlightMat);
    highlightBox.visible = false;
    scene.add(highlightBox);

    const outlineMat = new THREE.MeshBasicMaterial({ color: 0x00f0ff, transparent: true, opacity: 0.5, side: THREE.BackSide });
    let outlineMesh = null;

    const labels = {};
    SUBSYSTEMS.forEach((name) => {
      const label = createLabel(name, SUBSYSTEM_DATA[name].color);
      label.position.set(SUBSYSTEM_DATA[name].initialPos, 5.5, 0);
      scene.add(label);
      labels[name] = label;
    });

    sceneRef.current = {
      scene,
      camera,
      renderer,
      controls,
      tbmGroup,
      labels,
      highlightBox,
      outlineMat,
      raycaster: new THREE.Raycaster(),
      mouse: new THREE.Vector2(),
      container,
    };

    const onResize = () => {
      if (!container) return;
      camera.aspect = container.clientWidth / container.clientHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(container.clientWidth, container.clientHeight);
    };
    window.addEventListener("resize", onResize);

    let raf;
    const animate = () => {
      raf = requestAnimationFrame(animate);
      controls.update();

      for (const [name, label] of Object.entries(labels)) {
        const sub = tbmGroup.children.find((c) => c.name === name);
        if (sub && sub.children.length > 0) {
          const bbox = new THREE.Box3().setFromObject(sub);
          const center = bbox.getCenter(new THREE.Vector3());
          label.position.x = center.x;
          label.position.y = bbox.max.y + 1.5;
          label.position.z = center.z;
        }
      }
      renderer.render(scene, camera);
    };
    animate();

    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener("resize", onResize);
      controls.dispose();
      renderer.dispose();
      if (container.contains(renderer.domElement)) {
        container.removeChild(renderer.domElement);
      }
    };
  }, []);

  useEffect(() => {
    const { controls } = sceneRef.current;
    if (controls) controls.autoRotate = autoRotate;
  }, [autoRotate]);

  useEffect(() => {
    const { labels } = sceneRef.current;
    if (!labels) return;
    Object.values(labels).forEach((l) => {
      l.visible = showLabels;
    });
  }, [showLabels]);

  useEffect(() => {
    const { tbmGroup } = sceneRef.current;
    if (!tbmGroup) return;
    tbmGroup.children.forEach((sub) => {
      const data = SUBSYSTEM_DATA[sub.name];
      if (data) sub.visible = subsystemFilter[sub.name];
    });
  }, [subsystemFilter]);

  useEffect(() => {
    const { tbmGroup, highlightBox } = sceneRef.current;
    if (!tbmGroup) return;

    const t = explodeLevel;
    SUBSYSTEMS.forEach((name) => {
      const data = SUBSYSTEM_DATA[name];
      const sub = tbmGroup.children.find((c) => c.name === name);
      if (sub) {
        const startX = data.initialPos;
        const endX = data.explodedPos;
        sub.position.x = startX + (endX - startX) * t;
      }
    });

    if (selectedSystem) {
      const sub = tbmGroup.children.find((c) => c.name === selectedSystem);
      if (sub) {
        const bbox = new THREE.Box3().setFromObject(sub);
        const size = bbox.getSize(new THREE.Vector3());
        const center = bbox.getCenter(new THREE.Vector3());
        highlightBox.scale.set(size.x + 1, size.y + 1, size.z + 1);
        highlightBox.position.copy(center);
        highlightBox.visible = true;
        highlightBox.material.opacity = 0.15 + Math.sin(Date.now() * 0.005) * 0.05;
      }
    } else {
      highlightBox.visible = false;
    }
  }, [explodeLevel, selectedSystem]);

  useEffect(() => {
    const { tbmGroup, raycaster, mouse, container, camera, highlightBox, outlineMat } = sceneRef.current;
    if (!container || !tbmGroup) return;

    let currentOutline = outlineMat;

    const onPointerMove = (e) => {
      const rect = container.getBoundingClientRect();
      mouse.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
      mouse.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;

      raycaster.setFromCamera(mouse, camera);
      const meshes = [];
      tbmGroup.traverse((child) => {
        if (child.isMesh) meshes.push(child);
      });
      const intersects = raycaster.intersectObjects(meshes, false);

      if (intersects.length > 0) {
        let obj = intersects[0].object;
        while (obj.parent && !obj.userData.isTbmSubpart) obj = obj.parent;
        if (obj.userData.isTbmSubpart) {
          setHoveredSystem(obj.name);
          container.style.cursor = "pointer";
        }
      } else {
        setHoveredSystem(null);
        container.style.cursor = "default";
      }
    };

    const onClick = (e) => {
      const rect = container.getBoundingClientRect();
      mouse.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
      mouse.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;

      raycaster.setFromCamera(mouse, camera);
      const meshes = [];
      tbmGroup.traverse((child) => {
        if (child.isMesh) meshes.push(child);
      });
      const intersects = raycaster.intersectObjects(meshes, false);

      if (intersects.length > 0) {
        let obj = intersects[0].object;
        while (obj.parent && !obj.userData.isTbmSubpart) obj = obj.parent;
        if (obj.userData.isTbmSubpart) {
          setSelectedSystem(obj.name);
        }
      } else {
        setSelectedSystem(null);
      }
    };

    container.addEventListener("pointermove", onPointerMove);
    container.addEventListener("click", onClick);
    return () => {
      container.removeEventListener("pointermove", onPointerMove);
      container.removeEventListener("click", onClick);
    };
  }, []);

  const data = selectedSystem ? SUBSYSTEM_DATA[selectedSystem] : null;

  return (
    <div className="tbm-explorer-layout">
      <div className="tbm-canvas-wrap" ref={containerRef} />

      <div className="tbm-controls-panel glass-panel">
        <div className="tbm-section-title">CONTROLS</div>

        <div className="tbm-explode-row">
          <div className="tbm-explode-track">
            <div className="tbm-explode-fill" style={{ width: `${explodeLevel * 100}%` }} />
          </div>
          <input
            type="range"
            min="0"
            max="1"
            step="0.01"
            value={explodeLevel}
            onChange={(e) => setExplodeLevel(parseFloat(e.target.value))}
            className="tbm-explode-slider"
          />
          <span className="tbm-explode-val">{(explodeLevel * 100).toFixed(0)}%</span>
        </div>
        <div className="tbm-btn-row">
          <button
            className={`tbm-btn ${autoRotate ? "active" : ""}`}
            onClick={() => setAutoRotate((p) => !p)}
          >
            {autoRotate ? "◼ STOP" : "▶ ROTATE"}
          </button>
          <button
            className={`tbm-btn ${showLabels ? "active" : ""}`}
            onClick={() => setShowLabels((p) => !p)}
          >
            {showLabels ? "◼ LABELS" : "▶ LABELS"}
          </button>
          <button
            className="tbm-btn"
            onClick={() => {
              setExplodeLevel(0);
              setSelectedSystem(null);
              setSubsystemFilter(Object.fromEntries(SUBSYSTEMS.map((s) => [s, true])));
            }}
          >
            ↻ RESET
          </button>
        </div>
      </div>

      <div className="tbm-filter-panel glass-panel">
        <div className="tbm-section-title">SUBSYSTEMS</div>
        <button className="tbm-filter-all" onClick={toggleAll}>
          {Object.values(subsystemFilter).every(Boolean) ? "DESELECT ALL" : "SELECT ALL"}
        </button>
        {SUBSYSTEMS.map((name) => {
          const d = SUBSYSTEM_DATA[name];
          const isActive = subsystemFilter[name];
          const isSelected = selectedSystem === name;
          const isHovered = hoveredSystem === name;
          return (
            <button
              key={name}
              className={`tbm-filter-btn ${isActive ? "active" : ""} ${isSelected ? "selected" : ""} ${isHovered ? "hovered" : ""}`}
              style={{ "--accent": d.color }}
              onClick={() => {
                toggleSubsystem(name);
                setSelectedSystem(name);
              }}
            >
              <span className="tbm-filter-swatch" />
              <span className="tbm-filter-name">{name}</span>
              <span className="tbm-filter-pct">{(d.condition * 100).toFixed(0)}%</span>
            </button>
          );
        })}
      </div>

      <div className="tbm-hud-panel glass-panel">
        <div className="tbm-section-title">SUBSYSTEM DETAILS</div>
        {!data ? (
          <div className="tbm-hud-empty">CLICK A SUBSYSTEM</div>
        ) : (
          <>
            <div className="tbm-hud-row">
              <span className="tbm-hud-label">SUBSYSTEM</span>
              <span className="tbm-hud-val highlight">{selectedSystem}</span>
            </div>
            <div className="tbm-hud-row">
              <span className="tbm-hud-label">STATUS</span>
              <span className="tbm-hud-val status-green">NOMINAL</span>
            </div>
            <div className="tbm-hud-row">
              <span className="tbm-hud-label">HEALTH</span>
              <span className="tbm-hud-val">{(data.condition * 100).toFixed(1)}%</span>
            </div>
            <div className="tbm-hud-row">
              <span className="tbm-hud-label">CYCLES</span>
              <span className="tbm-hud-val">1,247</span>
            </div>
            <div className="tbm-hud-divider" />
            <div className="tbm-hud-row">
              <span className="tbm-hud-label">MAINT</span>
              <span className="tbm-hud-val">{data.maintenance.toLocaleString()} hrs</span>
            </div>
            <div className="tbm-hud-row">
              <span className="tbm-hud-label">SENSORS</span>
              <span className="tbm-hud-val small">{data.sensor}</span>
            </div>
            <div className="tbm-hud-row">
              <span className="tbm-hud-label">FAILURE</span>
              <span className="tbm-hud-val small">{data.failure}</span>
            </div>
            <div className="tbm-hud-row">
              <span className="tbm-hud-label">RATE</span>
              <span className="tbm-hud-val">{(data.failureRate * 100).toFixed(1)}%</span>
            </div>
            <div className="tbm-hud-divider" />
            <div className="tbm-hud-row">
              <span className="tbm-hud-label">CONDITION</span>
              <div className="tbm-hud-bar">
                <div className="tbm-hud-bar-fill" style={{ width: `${data.condition * 100}%`, background: data.color }} />
              </div>
            </div>
            <div className="tbm-hud-row">
              <span className="tbm-hud-label">CRITICALITY</span>
              <div className="tbm-hud-bar">
                <div className="tbm-hud-bar-fill" style={{ width: `${(1 - data.condition) * 100}%`, background: "#ff2d6f" }} />
              </div>
            </div>
            <div className="tbm-hud-divider" />
            <div className="tbm-hud-slots-title">COMPONENTS</div>
            {data.slots.map((slot) => (
              <div className="tbm-hud-slot" key={slot.name}>
                <span className="tbm-slot-name">{slot.name}</span>
                <span className="tbm-slot-qty">×{slot.qty}</span>
              </div>
            ))}
          </>
        )}
      </div>
    </div>
  );
}
