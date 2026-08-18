/**
 * FORGE3D Innovation #2: 3D Geological Stratigraphy Viewer
 * Renders soil layers, boreholes, and tunnel alignment in Three.js
 */
import { useEffect, useRef, useState, useMemo } from "react";
import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import { ENDPOINTS, getJSON } from "../api";

const TUNNEL_DEPTH = 20;
const TUNNEL_RADIUS = 3.2;
const LAYER_WIDTH = 80;
const SCALE = 0.4;

function hexToRGB(hex) {
  const r = parseInt(hex.slice(1, 3), 16) / 255;
  const g = parseInt(hex.slice(3, 5), 16) / 255;
  const b = parseInt(hex.slice(5, 7), 16) / 255;
  return new THREE.Color(r, g, b);
}

function buildGeologyGroup(profile) {
  const group = new THREE.Group();

  if (!profile || !profile.interpolated_layers) return group;

  const layers = profile.interpolated_layers;

  // Build soil layers as stacked boxes
  layers.forEach((layer, i) => {
    const thickness = (layer.bottom_depth_m - layer.top_depth_m) * SCALE;
    const yPos = -((layer.top_depth_m + layer.bottom_depth_m) / 2) * SCALE;
    const color = hexToRGB(layer.color_hex);

    // Main layer mesh
    const geo = new THREE.BoxGeometry(LAYER_WIDTH, thickness, 60);
    const mat = new THREE.MeshStandardMaterial({
      color: color,
      roughness: 0.85,
      metalness: 0.05,
      transparent: true,
      opacity: 0.88,
    });
    const mesh = new THREE.Mesh(geo, mat);
    mesh.position.set(0, yPos, 0);
    mesh.name = `layer-${layer.name}`;
    group.add(mesh);

    // Layer boundary lines
    const lineGeo = new THREE.BufferGeometry();
    const lineVerts = new Float32Array([
      -LAYER_WIDTH / 2, yPos + thickness / 2, 30,
      LAYER_WIDTH / 2, yPos + thickness / 2, 30,
    ]);
    lineGeo.setAttribute("position", new THREE.BufferAttribute(lineVerts, 3));
    const lineMat = new THREE.LineBasicMaterial({ color: 0xff00ff, linewidth: 2 });
    const line = new THREE.Line(lineGeo, lineMat);
    group.add(line);

    // Layer label (sprite)
    const canvas = document.createElement("canvas");
    canvas.width = 256;
    canvas.height = 64;
    const ctx = canvas.getContext("2d");
    ctx.fillStyle = "rgba(0,0,0,0.7)";
    ctx.fillRect(0, 0, 256, 64);
    ctx.fillStyle = "#00ffff";
    ctx.font = "bold 20px Courier New";
    ctx.fillText(layer.name, 10, 25);
    ctx.fillStyle = "#ffffff";
    ctx.font = "14px Courier New";
    ctx.fillText(`Es=${layer.es_mpa}MPa  γ=${layer.gamma_kn_m3}kN/m³`, 10, 50);

    const texture = new THREE.CanvasTexture(canvas);
    const spriteMat = new THREE.SpriteMaterial({ map: texture, transparent: true });
    const sprite = new THREE.Sprite(spriteMat);
    sprite.position.set(LAYER_WIDTH / 2 + 8, yPos, 20);
    sprite.scale.set(16, 4, 1);
    group.add(sprite);
  });

  // Tunnel cylinder through layers
  const tunnelGeo = new THREE.CylinderGeometry(
    TUNNEL_RADIUS * SCALE,
    TUNNEL_RADIUS * SCALE,
    60,
    32,
    1,
    true
  );
  const tunnelMat = new THREE.MeshStandardMaterial({
    color: 0x6a0dad,
    emissive: 0x6a0dad,
    emissiveIntensity: 0.3,
    transparent: true,
    opacity: 0.6,
    side: THREE.DoubleSide,
  });
  const tunnel = new THREE.Mesh(tunnelGeo, tunnelMat);
  tunnel.rotation.x = Math.PI / 2;
  tunnel.position.set(0, -TUNNEL_DEPTH * SCALE, 0);
  tunnel.name = "tunnel-alignment";
  group.add(tunnel);

  // Borehole markers
  if (profile.boreholes) {
    profile.boreholes.forEach((bh) => {
      const bhGroup = new THREE.Group();
      bhGroup.name = `borehole-${bh.borehole_id}`;

      // Vertical borehole line
      const bhGeo = new THREE.CylinderGeometry(0.15, 0.15, bh.total_depth_m * SCALE, 8);
      const bhMat = new THREE.MeshStandardMaterial({
        color: 0x00ffff,
        emissive: 0x00ffff,
        emissiveIntensity: 0.5,
      });
      const bhMesh = new THREE.Mesh(bhGeo, bhMat);
      bhMesh.position.y = -(bh.total_depth_m * SCALE) / 2;
      bhGroup.add(bhMesh);

      // Borehole cap
      const capGeo = new THREE.ConeGeometry(0.4, 1.0, 8);
      const capMat = new THREE.MeshStandardMaterial({
        color: 0xff00ff,
        emissive: 0xff00ff,
        emissiveIntensity: 0.7,
      });
      const cap = new THREE.Mesh(capGeo, capMat);
      cap.position.y = 0.5;
      bhGroup.add(cap);

      bhGroup.position.set(bh.x_enu, 0, bh.y_enu * 0.5);
      group.add(bhGroup);
    });
  }

  return group;
}

export default function GeologyView({ onToast }) {
  const mountRef = useRef(null);
  const holderRef = useRef(null);
  const [profile, setProfile] = useState(null);
  const [selectedLayer, setSelectedLayer] = useState(null);
  const sceneRef = useRef(null);
  const geoRef = useRef(null);

  useEffect(() => {
    const holder = holderRef.current;
    const mount = mountRef.current;
    if (!holder || !mount) return;

    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x0a0a1a);
    scene.fog = new THREE.Fog(0x0a0a1a, 50, 120);
    sceneRef.current = scene;

    const camera = new THREE.PerspectiveCamera(55, mount.clientWidth / mount.clientHeight, 0.1, 400);
    camera.position.set(30, 20, 40);
    camera.lookAt(0, -10, 0);

    const renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setSize(mount.clientWidth, mount.clientHeight);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.shadowMap.enabled = true;
    mount.appendChild(renderer.domElement);

    const controls = new OrbitControls(camera, renderer.domElement);
    controls.target.set(0, -8, 0);
    controls.enableDamping = true;
    controls.update();

    // Lighting
    scene.add(new THREE.AmbientLight(0x404060, 0.8));
    const sun = new THREE.DirectionalLight(0xffffff, 1.0);
    sun.position.set(20, 30, 20);
    scene.add(sun);

    const grid = new THREE.GridHelper(80, 40, 0xff00ff, 0x008080);
    grid.position.y = 1;
    scene.add(grid);

    // Axes
    const axes = new THREE.AxesHelper(5);
    axes.position.set(-LAYER_WIDTH / 2 - 5, 0, 0);
    scene.add(axes);

    const geoGroup = new THREE.Group();
    geoGroup.name = "geology-group";
    scene.add(geoGroup);
    geoRef.current = geoGroup;

    // Raycaster for layer selection
    const raycaster = new THREE.Raycaster();
    const mouse = new THREE.Vector2();
    let hoverLayer = null;

    function onPick(e) {
      const rect = renderer.domElement.getBoundingClientRect();
      mouse.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
      mouse.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;
      raycaster.setFromCamera(mouse, camera);
      const hits = raycaster.intersectObjects(geoGroup.children, false);
      if (hits.length && hits[0].object.name?.startsWith("layer-")) {
        hoverLayer = hits[0].object.name.replace("layer-", "");
      } else {
        hoverLayer = null;
      }
    }
    renderer.domElement.addEventListener("pointermove", onPick);

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
      renderer.domElement.removeEventListener("pointermove", onPick);
      controls.dispose();
      mount.removeChild(renderer.domElement);
      renderer.dispose();
    };
  }, []);

  // Load geological profile
  useEffect(() => {
    let cancelled = false;
    async function loadProfile() {
      try {
        const res = await getJSON("/api/geology/profile");
        if (cancelled) return;
        setProfile(res);
        const scene = sceneRef.current;
        if (scene) {
          const old = scene.getObjectByName("geology-group");
          if (old) scene.remove(old);
          const group = buildGeologyGroup(res);
          group.name = "geology-group";
          scene.add(group);
          geoRef.current = group;
        }
      } catch (e) {
        if (onToast) onToast("GEOLOGY API OFFLINE", "err");
      }
    }
    loadProfile();
    return () => { cancelled = true; };
  }, [onToast]);

  return (
    <div className="geo-layout">
      <div className="twin-3d" ref={holderRef}>
        <div ref={mountRef} className="twin-3d-mount" />
        <div className="twin-3d-label">GEOLOGICAL STRATIGRAPHY VIEW</div>
      </div>
      <div className="twin-panel">
        <div className="twin-hud">
          <div className="twin-hud-title">SOIL STRATA</div>
          {profile && profile.interpolated_layers &&
            profile.interpolated_layers.map((layer, i) => (
              <div
                key={i}
                className="twin-hud-row"
                style={{ cursor: "pointer", borderLeft: `4px solid ${layer.color_hex}` }}
              >
                <span>{layer.name}</span>
                <b>{layer.top_depth_m}–{layer.bottom_depth_m}m</b>
              </div>
            ))
          }
        </div>
        <div className="twin-hud">
          <div className="twin-hud-title">TUNNEL AXIS</div>
          <div className="twin-hud-row"><span>DEPTH</span><b>{TUNNEL_DEPTH}m</b></div>
          <div className="twin-hud-row"><span>RADIUS</span><b>{TUNNEL_RADIUS}m</b></div>
        </div>
        <div className="twin-hud">
          <div className="twin-hud-title">BOREHOLES</div>
          {profile && profile.boreholes &&
            profile.boreholes.map((bh, i) => (
              <div key={i} className="twin-hud-row">
                <span>{bh.borehole_id}</span>
                <b>({bh.x_enu}, {bh.y_enu})</b>
              </div>
            ))
          }
        </div>
      </div>
    </div>
  );
}
