import { useEffect, useMemo, useRef, useState } from "react";
import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  LineChart,
  Line,
  Legend
} from "recharts";

const TOOLTIP_STYLE = {
  background: "#101020",
  border: "1px solid #333",
  color: "#cfc",
  fontSize: 10,
  fontFamily: '"Courier New", "Lucida Console", monospace',
  padding: "4px 8px"
};

const KPI_CONFIG = [
  { key: "pen", label: "PENETRATION SPEED", unit: "mm/min", color: "#00ffff", decimals: 1 },
  { key: "thrust", label: "THRUST FORCE", unit: "kN", color: "#ff8800", decimals: 0 },
  { key: "soil", label: "SOIL VOLUME", unit: "m³", color: "#ff00ff", decimals: 0 }
];

function walk(prev, spread) {
  return prev + (Math.random() - 0.5) * spread;
}

function seedHistory(base, n = 24, spreadRatio = 0.05) {
  const arr = [];
  let v = base;
  for (let i = 0; i < n; i += 1) {
    v = walk(v, base * spreadRatio);
    arr.push(Math.max(base * 0.6, Math.min(base * 1.4, v)));
  }
  return arr;
}

const CREW = Array.from({ length: 24 }, (_, i) => {
  const surface = 24 + Math.round(11 * Math.sin(((i - 7) / 24) * Math.PI * 2));
  const tunnel = 14 + Math.round(9 * Math.sin(((i - 6) / 24) * Math.PI * 2 + 0.6));
  return {
    time: `${String((6 + i) % 24).padStart(2, "0")}:00`,
    surface: Math.max(4, surface),
    tunnel: Math.max(2, tunnel)
  };
});

const COST = { planned: { used: 412, total: 500 }, actual: { used: 438, total: 500 } };

const COST_ROWS = [
  { label: "MATERIALS", used: 148, total: 170 },
  { label: "LABOR", used: 96, total: 120 },
  { label: "EQUIPMENT", used: 154, total: 165 },
  { label: "GROUT & LOG", used: 40, total: 45 }
];

export default function TbmDashboard({ shield }) {
  const mountRef = useRef(null);
  const controlsRef = useRef(null);
  const rpmRef = useRef(12);
  const glowRef = useRef(1.6);
  const autoRef = useRef(true);
  const gridVisibleRef = useRef(true);
  const wireframeRef = useRef(false);

  const [rpm, setRpm] = useState(12);
  const [glow, setGlow] = useState(1.6);
  const [autoOrbit, setAutoOrbit] = useState(true);
  const [showGrid, setShowGrid] = useState(true);
  const [wireframe, setWireframe] = useState(false);

  const init = useMemo(() => {
    const latest = shield?.[0] || {};
    const pen = Number(latest.advance_speed_mm_min) || 34;
    const thrust = Number(latest.thrust_kn) || 14200;
    return {
      pen: seedHistory(pen, 24, 0.05),
      thrust: seedHistory(thrust, 24, 0.03),
      soil: seedHistory(4820, 24, 0.004)
    };
  }, [shield]);

  const [history, setHistory] = useState(init);

  useEffect(() => {
    const id = setInterval(() => {
      setHistory((h) => {
        const step = (arr, ratio) => {
          const last = arr[arr.length - 1];
          const v = Math.max(last * 0.6, Math.min(last * 1.4, walk(last, last * ratio)));
          return [...arr.slice(1), v];
        };
        return {
          pen: step(h.pen, 0.06),
          thrust: step(h.thrust, 0.035),
          soil: step(h.soil, 0.005)
        };
      });
    }, 1300);
    return () => clearInterval(id);
  }, []);

  useEffect(() => {
    rpmRef.current = rpm;
  }, [rpm]);
  useEffect(() => {
    glowRef.current = glow;
  }, [glow]);
  useEffect(() => {
    autoRef.current = autoOrbit;
  }, [autoOrbit]);
  useEffect(() => {
    gridVisibleRef.current = showGrid;
  }, [showGrid]);
  useEffect(() => {
    wireframeRef.current = wireframe;
  }, [wireframe]);

  useEffect(() => {
    const mount = mountRef.current;
    if (!mount) return;

    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x07070f);

    const camera = new THREE.PerspectiveCamera(50, mount.clientWidth / mount.clientHeight, 0.1, 300);
    camera.position.set(16, 9, 22);

    const renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setSize(mount.clientWidth, mount.clientHeight);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    mount.appendChild(renderer.domElement);

    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.08;
    controls.target.set(0, 0, 1);
    controls.autoRotate = true;
    controls.autoRotateSpeed = 1.2;
    controls.maxPolarAngle = Math.PI * 0.62;
    controls.update();
    controlsRef.current = controls;

    scene.add(new THREE.AmbientLight(0x30304a, 1.1));
    const key = new THREE.DirectionalLight(0xffffff, 1.4);
    key.position.set(18, 26, 14);
    scene.add(key);
    const rim = new THREE.DirectionalLight(0x00ffff, 0.5);
    rim.position.set(-14, -8, -10);
    scene.add(rim);
    const glowLight = new THREE.PointLight(0xff7700, 2.4, 60, 1.6);
    glowLight.position.set(0, 0, 10);
    scene.add(glowLight);
    const tailLight = new THREE.PointLight(0x00ffff, 0.6, 40);
    tailLight.position.set(-12, 4, -12);
    scene.add(tailLight);

    const grid = new THREE.GridHelper(60, 48, 0xff7711, 0x3a3a5a);
    grid.position.y = -7;
    scene.add(grid);

    const group = new THREE.Group();
    scene.add(group);
    const glowMats = [];

    const bodyMat = new THREE.MeshStandardMaterial({ color: 0x3a4152, metalness: 0.9, roughness: 0.28 });
    const body = new THREE.Mesh(new THREE.CylinderGeometry(3, 3, 11, 48, 1, true), bodyMat);
    body.rotation.x = Math.PI / 2;
    group.add(body);

    const capMat = new THREE.MeshStandardMaterial({ color: 0x2b3040, metalness: 0.85, roughness: 0.4, side: THREE.DoubleSide });
    const cap = new THREE.Mesh(new THREE.CircleGeometry(3, 48), capMat);
    cap.position.z = -5.5;
    cap.rotation.y = Math.PI;
    group.add(cap);

    const rearMat = new THREE.MeshStandardMaterial({ color: 0x20242e, metalness: 0.8, roughness: 0.5 });
    const rear = new THREE.Mesh(new THREE.CylinderGeometry(2.7, 3, 4, 48, 1, true), rearMat);
    rear.rotation.x = Math.PI / 2;
    rear.position.z = -7.5;
    group.add(rear);

    const ringMat = new THREE.MeshStandardMaterial({ color: 0x008080, emissive: 0x008080, emissiveIntensity: 0.55, metalness: 0.7, roughness: 0.3 });
    [-3.4, 0, 3.4].forEach((z) => {
      const ring = new THREE.Mesh(new THREE.TorusGeometry(3.02, 0.14, 12, 48), ringMat);
      ring.rotation.y = Math.PI / 2;
      ring.position.z = z;
      group.add(ring);
    });

    const collar = new THREE.Mesh(
      new THREE.TorusGeometry(3.08, 0.18, 12, 48),
      new THREE.MeshStandardMaterial({ color: 0x555d6e, metalness: 0.85, roughness: 0.3 })
    );
    collar.rotation.y = Math.PI / 2;
    collar.position.z = 5.25;
    group.add(collar);

    const spindle = new THREE.Mesh(
      new THREE.CylinderGeometry(0.35, 0.35, 2.2, 16),
      new THREE.MeshStandardMaterial({ color: 0x555d6e, metalness: 0.9, roughness: 0.3 })
    );
    spindle.rotation.x = Math.PI / 2;
    spindle.position.z = 1.4;
    group.add(spindle);

    const cutter = new THREE.Group();
    cutter.position.z = 5.5;

    const faceMat = new THREE.MeshStandardMaterial({ color: 0xff8822, emissive: 0xff6600, emissiveIntensity: glowRef.current, metalness: 0.4, roughness: 0.35, side: THREE.DoubleSide });
    glowMats.push(faceMat);
    cutter.add(new THREE.Mesh(new THREE.CircleGeometry(2.9, 48), faceMat));

    const rimMat = new THREE.MeshStandardMaterial({ color: 0xffaa33, emissive: 0xff6600, emissiveIntensity: glowRef.current, metalness: 0.5, roughness: 0.3 });
    glowMats.push(rimMat);
    const rimTorus = new THREE.Mesh(new THREE.TorusGeometry(3.05, 0.3, 16, 64), rimMat);
    rimTorus.position.z = 0.15;
    cutter.add(rimTorus);

    const hubMat = new THREE.MeshStandardMaterial({ color: 0xffdd88, emissive: 0xff7700, emissiveIntensity: glowRef.current, metalness: 0.5, roughness: 0.3 });
    glowMats.push(hubMat);
    const hub = new THREE.Mesh(new THREE.CylinderGeometry(1.05, 1.05, 0.5, 32), hubMat);
    hub.rotation.x = Math.PI / 2;
    hub.position.z = 0.2;
    cutter.add(hub);

    const armMat = new THREE.MeshStandardMaterial({ color: 0xff9933, emissive: 0xff6600, emissiveIntensity: glowRef.current, metalness: 0.55, roughness: 0.35 });
    glowMats.push(armMat);
    const spokes = 6;
    for (let i = 0; i < spokes; i += 1) {
      const a = (i / spokes) * Math.PI * 2;
      const arm = new THREE.Mesh(new THREE.BoxGeometry(2.5, 0.5, 0.16), armMat);
      arm.position.set(Math.cos(a) * 1.35, Math.sin(a) * 1.35, 0.55);
      arm.rotation.z = a;
      cutter.add(arm);
    }

    const toolMat = new THREE.MeshStandardMaterial({ color: 0xcccccc, emissive: 0xff5500, emissiveIntensity: 0.9, metalness: 0.8, roughness: 0.3 });
    const toolCount = 10;
    for (let i = 0; i < toolCount; i += 1) {
      const a = (i / toolCount) * Math.PI * 2;
      const tool = new THREE.Mesh(new THREE.CylinderGeometry(0.22, 0.22, 0.7, 12), toolMat);
      tool.position.set(Math.cos(a) * 2.35, Math.sin(a) * 2.35, 0.6);
      tool.rotation.x = Math.PI / 2;
      cutter.add(tool);
    }

    group.add(cutter);

    const clock = new THREE.Clock();
    let raf = 0;
    function animate() {
      raf = requestAnimationFrame(animate);
      const dt = Math.min(clock.getDelta(), 0.1);
      cutter.rotation.z += dt * (rpmRef.current / 60) * Math.PI * 2;
      glowMats.forEach((m) => {
        m.emissiveIntensity = glowRef.current;
      });
      controls.autoRotate = autoRef.current;
      grid.visible = gridVisibleRef.current;
      bodyMat.wireframe = wireframeRef.current;
      controls.update();
      renderer.render(scene, camera);
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
      controls.dispose();
      group.traverse((c) => {
        if (c.isMesh) {
          c.geometry.dispose();
          if (Array.isArray(c.material)) c.material.forEach((m) => m.dispose());
          else c.material.dispose();
        }
      });
      mount.removeChild(renderer.domElement);
      renderer.dispose();
    };
  }, []);

  function resetView() {
    const c = controlsRef.current;
    if (!c) return;
    c.target.set(0, 0, 1);
    c.object.position.set(16, 9, 22);
    c.update();
  }

  function cur(key) {
    return history[key][history[key].length - 1];
  }

  function deltaPct(key) {
    const arr = history[key];
    const last = arr[arr.length - 1];
    const prev = arr[arr.length - 3];
    return prev ? ((last - prev) / prev) * 100 : 0;
  }

  const sparkData = (key) => history[key].map((v, i) => ({ i, v }));
  const crewNow = CREW[CREW.length - 1];

  return (
    <div className="tbm-dash">
      <div className="tbm-kpi-row">
        {KPI_CONFIG.map((k) => (
          <div key={k.key} className="tbm-kpi" style={{ borderTopColor: k.color }}>
            <div className="tbm-kpi-title">{k.label}</div>
            <div className="tbm-kpi-val">
              {cur(k.key).toLocaleString(undefined, { maximumFractionDigits: k.decimals, minimumFractionDigits: k.decimals })}
              <span className="tbm-kpi-unit">{k.unit}</span>
            </div>
            <div className={`tbm-kpi-delta ${deltaPct(k.key) >= 0 ? "up" : "down"}`}>
              {deltaPct(k.key) >= 0 ? "▲" : "▼"} {Math.abs(deltaPct(k.key)).toFixed(1)}% Δ LIVE
            </div>
            <div className="tbm-kpi-spark">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={sparkData(k.key)} margin={{ top: 2, right: 0, bottom: 0, left: 0 }}>
                  <defs>
                    <linearGradient id={`spark-${k.key}`} x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor={k.color} stopOpacity={0.85} />
                      <stop offset="100%" stopColor={k.color} stopOpacity={0.05} />
                    </linearGradient>
                  </defs>
                  <Area type="monotone" dataKey="v" stroke={k.color} strokeWidth={1.6} fill={`url(#spark-${k.key})`} isAnimationActive={false} />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>
        ))}
      </div>

      <div className="tbm-main">
        <div className="tbm-panel">
          <div className="tbm-panel-title">CREW.EXE - PERSONNEL COUNT</div>
          <div className="tbm-chart">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={CREW} margin={{ top: 6, right: 8, bottom: 0, left: -16 }}>
                <CartesianGrid stroke="#2a2a4a" strokeDasharray="3 3" />
                <XAxis dataKey="time" tick={{ fontSize: 8, fill: "#7c7" }} tickLine={false} axisLine={{ stroke: "#333" }} />
                <YAxis tick={{ fontSize: 8, fill: "#7c7" }} tickLine={false} axisLine={{ stroke: "#333" }} allowDecimals={false} width={30} />
                <Tooltip contentStyle={TOOLTIP_STYLE} labelStyle={{ color: "#ff0" }} itemStyle={{ color: "#cfc", fontSize: 10 }} />
                <Legend wrapperStyle={{ fontSize: 9, color: "#7c7" }} iconType="plainline" />
                <Line type="monotone" dataKey="surface" name="SURFACE" stroke="#00ffff" strokeWidth={1.8} dot={false} />
                <Line type="monotone" dataKey="tunnel" name="TUNNEL" stroke="#ff8800" strokeWidth={1.8} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
          <div className="tbm-panel-foot">
            <span>TOTAL ON SITE: <b>{crewNow.surface + crewNow.tunnel}</b></span>
            <span>SHIFT: DAY</span>
          </div>
        </div>

        <div className="tbm-panel">
          <div className="tbm-panel-title">FINANCE.EXE - CONSTRUCTION COST</div>
          <div className="tbm-cost-dual">
            <div className="tbm-cost-block">
              <div className="tbm-cost-head">
                <span className="tbm-cost-label">PLANNED BUDGET</span>
                <span className="tbm-cost-val">${COST.planned.used}M / ${COST.planned.total}M</span>
              </div>
              <div className="tbm-cost-track">
                <div className="tbm-cost-fill" style={{ width: `${(COST.planned.used / COST.planned.total) * 100}%` }} />
              </div>
              <div className="tbm-cost-meta"><span>ALLOCATED {(COST.planned.used / COST.planned.total * 100).toFixed(1)}%</span></div>
            </div>
            <div className="tbm-cost-block">
              <div className="tbm-cost-head">
                <span className="tbm-cost-label">ACTUAL SPENT</span>
                <span className="tbm-cost-val">${COST.actual.used}M / ${COST.actual.total}M</span>
              </div>
              <div className="tbm-cost-track">
                <div className="tbm-cost-fill warn" style={{ width: `${(COST.actual.used / COST.actual.total) * 100}%` }} />
              </div>
              <div className="tbm-cost-meta">
                <span>INCURRED {(COST.actual.used / COST.actual.total * 100).toFixed(1)}%</span>
                <b className="tbm-overrun">OVER RUN +{COST.actual.used - COST.planned.used}M</b>
              </div>
            </div>
          </div>
          <div className="tbm-cost-table">
            {COST_ROWS.map((r) => (
              <div className="tbm-cost-row" key={r.label}>
                <span className="tbm-cost-row-label">{r.label}</span>
                <div className="tbm-cost-track small">
                  <div className="tbm-cost-fill" style={{ width: `${(r.used / r.total) * 100}%` }} />
                </div>
                <span className="tbm-cost-row-val">${r.used}M</span>
              </div>
            ))}
          </div>
        </div>

        <div className="tbm-panel tbm-twin">
          <div className="tbm-panel-title">TWIN-3D.EXE - TBM MODEL EDITOR</div>
          <div className="tbm-twin-row">
            <div className="tbm-3d">
              <div ref={mountRef} className="tbm-3d-mount" />
            </div>
            <div className="tbm-editor">
              <div className="tbm-ctrl">
                <label>CUTTER RPM <b>{rpm}</b></label>
                <input type="range" min="0" max="60" value={rpm} onChange={(e) => setRpm(Number(e.target.value))} />
              </div>
              <div className="tbm-ctrl">
                <label>GLOW <b>{glow.toFixed(1)}</b></label>
                <input type="range" min="0" max="3" step="0.1" value={glow} onChange={(e) => setGlow(Number(e.target.value))} />
              </div>
              <div className="tbm-ctrl tbm-toggle">
                <label>CAMERA ORBIT</label>
                <input type="checkbox" checked={autoOrbit} onChange={(e) => setAutoOrbit(e.target.checked)} />
              </div>
              <div className="tbm-ctrl tbm-toggle">
                <label>GROUND GRID</label>
                <input type="checkbox" checked={showGrid} onChange={(e) => setShowGrid(e.target.checked)} />
              </div>
              <div className="tbm-ctrl tbm-toggle">
                <label>WIREFRAME</label>
                <input type="checkbox" checked={wireframe} onChange={(e) => setWireframe(e.target.checked)} />
              </div>
              <button className="btn chunky" onClick={resetView}>RESET VIEW</button>
            </div>
          </div>
          <div className="tbm-twin-hint">DRAG ROTATE // SCROLL ZOOM // SLIDERS EDIT THE MODEL LIVE</div>
        </div>
      </div>
    </div>
  );
}
