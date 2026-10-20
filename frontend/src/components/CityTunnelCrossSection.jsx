import { useEffect, useRef, useState, useCallback, useMemo } from "react";
import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";

const TUNNEL_DEPTH = 18;
const TUNNEL_RADIUS = 3.2;
const RING_LEN = 1.6;
const CITY_WIDTH = 120;
const CITY_DEPTH = 80;
const GROUND_Y = 0;

const GEO_LAYERS = [
  { name: "Topsoil", color: 0x5c4033, top: 0, bottom: -2, roughness: 0.95 },
  { name: "Fill Material", color: 0x8B7355, top: -2, bottom: -5, roughness: 0.9 },
  { name: "Soft Clay", color: 0x7B6B4F, top: -5, bottom: -10, roughness: 0.85 },
  { name: "Dense Sand", color: 0xC4A97D, top: -10, bottom: -16, roughness: 0.8 },
  { name: "Stiff Clay", color: 0x8B6914, top: -16, bottom: -24, roughness: 0.75 },
  { name: "Weathered Rock", color: 0x696969, top: -24, bottom: -32, roughness: 0.7 },
  { name: "Bedrock", color: 0x4a4a5a, top: -32, bottom: -42, roughness: 0.65 }
];

const BUILDING_DEFS = [
  { x: -40, z: -25, w: 8, d: 8, h: 32, type: "high-rise", risk: "low" },
  { x: -28, z: -25, w: 6, d: 6, h: 18, type: "residential", risk: "low" },
  { x: -18, z: -28, w: 10, d: 8, h: 45, type: "tower", risk: "medium" },
  { x: -5, z: -22, w: 7, d: 7, h: 12, type: "commercial", risk: "low" },
  { x: 6, z: -26, w: 9, d: 7, h: 28, type: "high-rise", risk: "high" },
  { x: 18, z: -24, w: 6, d: 6, h: 15, type: "residential", risk: "medium" },
  { x: 28, z: -27, w: 8, d: 8, h: 38, type: "tower", risk: "low" },
  { x: 38, z: -22, w: 7, d: 6, h: 10, type: "commercial", risk: "low" },
  { x: -35, z: -40, w: 6, d: 6, h: 22, type: "residential", risk: "low" },
  { x: -22, z: -42, w: 8, d: 7, h: 8, type: "low-rise", risk: "low" },
  { x: -8, z: -38, w: 7, d: 6, h: 14, type: "commercial", risk: "critical" },
  { x: 5, z: -40, w: 10, d: 8, h: 50, type: "skyscraper", risk: "high" },
  { x: 18, z: -38, w: 6, d: 5, h: 10, type: "low-rise", risk: "medium" },
  { x: 30, z: -42, w: 8, d: 7, h: 20, type: "residential", risk: "low" },
  { x: -42, z: -15, w: 5, d: 5, h: 6, type: "low-rise", risk: "low" },
  { x: 42, z: -15, w: 5, d: 5, h: 7, type: "low-rise", risk: "low" },
  { x: -15, z: -12, w: 6, d: 5, h: 9, type: "commercial", risk: "low" },
  { x: 20, z: -12, w: 7, d: 5, h: 11, type: "commercial", risk: "low" },
];

const RISK_COLORS = {
  low: 0x00cc66,
  medium: 0xff8800,
  high: 0xff2d6f,
  critical: 0xff0040,
  safe: 0x00cc66,
  notice: 0xff8800,
  warning: 0xffff00
};

const SENSOR_DEFS = [
  { type: "settlement", x: -15, y: 0.5, z: -20, status: "normal", label: "S-01" },
  { type: "settlement", x: 0, y: 0.5, z: -20, status: "warning", label: "S-02" },
  { type: "settlement", x: 15, y: 0.5, z: -20, status: "normal", label: "S-03" },
  { type: "inclinometer", x: -10, y: -8, z: -18, status: "normal", label: "INC-01" },
  { type: "inclinometer", x: 10, y: -8, z: -18, status: "alert", label: "INC-02" },
  { type: "piezometer", x: -20, y: -12, z: -22, status: "normal", label: "PZ-01" },
  { type: "piezometer", x: 20, y: -12, z: -22, status: "normal", label: "PZ-02" },
  { type: "tilt", x: -8, y: 8, z: -24, status: "warning", label: "T-01" },
  { type: "tilt", x: 8, y: 12, z: -26, status: "normal", label: "T-02" },
  { type: "vibration", x: 0, y: -TUNNEL_DEPTH, z: -15, status: "normal", label: "V-01" },
  { type: "pressure", x: 0, y: -TUNNEL_DEPTH + 3, z: -30, status: "normal", label: "PR-01" },
  { type: "crack", x: 6, y: 6, z: -26, status: "alert", label: "CR-01" },
];

const SENSOR_COLORS = {
  settlement: 0x00ffff,
  inclinometer: 0x00ff88,
  piezometer: 0x4488ff,
  tilt: 0xff8800,
  vibration: 0xff00ff,
  pressure: 0xffff00,
  crack: 0xff2d6f
};

const STATUS_COLORS = {
  normal: 0x00cc66,
  warning: 0xff8800,
  alert: 0xff2d6f,
  offline: 0x555555
};

function buildCitySurface() {
  const group = new THREE.Group();
  group.name = "city-surface";

  const groundGeo = new THREE.BoxGeometry(CITY_WIDTH, 0.6, CITY_DEPTH);
  const groundMat = new THREE.MeshStandardMaterial({ color: 0x3a3a3a, roughness: 0.9, metalness: 0.05 });
  const ground = new THREE.Mesh(groundGeo, groundMat);
  ground.position.set(0, -0.3, -CITY_DEPTH / 2 + 10);
  ground.receiveShadow = true;
  group.add(ground);

  const roadGeo = new THREE.BoxGeometry(CITY_WIDTH + 2, 0.05, 12);
  const roadMat = new THREE.MeshStandardMaterial({ color: 0x2a2a2a, roughness: 0.85 });
  const road = new THREE.Mesh(roadGeo, roadMat);
  road.position.set(0, 0.02, -15);
  road.receiveShadow = true;
  group.add(road);

  for (let i = -55; i <= 55; i += 8) {
    const lineGeo = new THREE.BoxGeometry(3, 0.06, 0.3);
    const lineMat = new THREE.MeshStandardMaterial({ color: 0xffff00, emissive: 0xffff00, emissiveIntensity: 0.3 });
    const line = new THREE.Mesh(lineGeo, lineMat);
    line.position.set(i, 0.06, -15);
    group.add(line);
  }

  const sideGeo = new THREE.BoxGeometry(CITY_WIDTH + 2, 0.4, 6);
  const sideMat = new THREE.MeshStandardMaterial({ color: 0x555555, roughness: 0.9 });
  const sideL = new THREE.Mesh(sideGeo, sideMat);
  sideL.position.set(0, -0.1, -30);
  group.add(sideL);
  const sideR = sideL.clone();
  sideR.position.z = -2;
  group.add(sideR);

  for (let i = -50; i <= 50; i += 12) {
    const trunkGeo = new THREE.CylinderGeometry(0.15, 0.2, 2, 6);
    const trunkMat = new THREE.MeshStandardMaterial({ color: 0x4a3728 });
    const trunk = new THREE.Mesh(trunkGeo, trunkMat);
    trunk.position.set(i, 1, -8);
    group.add(trunk);

    const canopyGeo = new THREE.SphereGeometry(1.2, 8, 6);
    const canopyMat = new THREE.MeshStandardMaterial({ color: 0x2d5a1e, roughness: 0.9 });
    const canopy = new THREE.Mesh(canopyGeo, canopyMat);
    canopy.position.set(i, 2.5, -8);
    canopy.scale.y = 0.7;
    group.add(canopy);
  }

  return group;
}

function buildBuildings() {
  const group = new THREE.Group();
  group.name = "buildings";

  BUILDING_DEFS.forEach((b, i) => {
    const bGroup = new THREE.Group();
    bGroup.name = `building-${i}`;

    const baseColor = RISK_COLORS[b.risk] || 0x888888;
    const bodyGeo = new THREE.BoxGeometry(b.w, b.h, b.d);
    const bodyMat = new THREE.MeshStandardMaterial({
      color: 0x8899aa,
      roughness: 0.6,
      metalness: 0.2,
      transparent: true,
      opacity: 0.85
    });
    const body = new THREE.Mesh(bodyGeo, bodyMat);
    body.position.y = b.h / 2;
    body.castShadow = true;
    body.receiveShadow = true;
    bGroup.add(body);

    const edgeGeo = new THREE.EdgesGeometry(bodyGeo);
    const edgeMat = new THREE.LineBasicMaterial({ color: baseColor, transparent: true, opacity: 0.6 });
    const edges = new THREE.LineSegments(edgeGeo, edgeMat);
    edges.position.y = b.h / 2;
    bGroup.add(edges);

    const floors = Math.floor(b.h / 3.5);
    for (let f = 0; f < floors; f++) {
      const winRow = Math.floor(b.w / 2);
      for (let wx = 0; wx < winRow; wx++) {
        const winGeo = new THREE.PlaneGeometry(0.8, 1.2);
        const winMat = new THREE.MeshStandardMaterial({
          color: 0x88ccff,
          emissive: 0x334466,
          emissiveIntensity: 0.4,
          transparent: true,
          opacity: 0.7
        });
        const win = new THREE.Mesh(winGeo, winMat);
        win.position.set(-b.w / 2 + 1.5 + wx * 2, 1.5 + f * 3.5, b.d / 2 + 0.01);
        bGroup.add(win);

        const winBack = win.clone();
        winBack.position.z = -b.d / 2 - 0.01;
        winBack.rotation.y = Math.PI;
        bGroup.add(winBack);
      }
    }

    const riskIndicatorGeo = new THREE.BoxGeometry(b.w + 0.4, 0.3, b.d + 0.4);
    const riskIndicatorMat = new THREE.MeshStandardMaterial({
      color: baseColor,
      emissive: baseColor,
      emissiveIntensity: 0.8,
      transparent: true,
      opacity: 0.6
    });
    const riskIndicator = new THREE.Mesh(riskIndicatorGeo, riskIndicatorMat);
    riskIndicator.position.y = b.h + 0.5;
    bGroup.add(riskIndicator);

    const foundationGeo = new THREE.BoxGeometry(b.w - 0.5, 2, b.d - 0.5);
    const foundationMat = new THREE.MeshStandardMaterial({ color: 0x555555, roughness: 0.8 });
    const foundation = new THREE.Mesh(foundationGeo, foundationMat);
    foundation.position.y = -1;
    bGroup.add(foundation);

    bGroup.position.set(b.x, 0, b.z);
    bGroup.userData = { ...b, index: i };
    group.add(bGroup);
  });

  return group;
}

function buildGeology() {
  const group = new THREE.Group();
  group.name = "geology";

  GEO_LAYERS.forEach((layer) => {
    const thickness = Math.abs(layer.bottom - layer.top);
    const yPos = (layer.top + layer.bottom) / 2;

    const geo = new THREE.BoxGeometry(CITY_WIDTH, thickness, CITY_DEPTH);
    const mat = new THREE.MeshStandardMaterial({
      color: layer.color,
      roughness: layer.roughness,
      metalness: 0.05,
      transparent: true,
      opacity: 0.82
    });
    const mesh = new THREE.Mesh(geo, mat);
    mesh.position.set(0, yPos, -CITY_DEPTH / 2 + 10);
    mesh.name = `geo-${layer.name}`;
    group.add(mesh);

    const labelCanvas = document.createElement("canvas");
    labelCanvas.width = 512;
    labelCanvas.height = 64;
    const ctx = labelCanvas.getContext("2d");
    ctx.fillStyle = "rgba(0,0,0,0.8)";
    ctx.fillRect(0, 0, 512, 64);
    ctx.fillStyle = "#00f0ff";
    ctx.font = "bold 28px Inter, sans-serif";
    ctx.fillText(layer.name.toUpperCase(), 12, 30);
    ctx.fillStyle = "#aaaacc";
    ctx.font = "20px JetBrains Mono, monospace";
    ctx.fillText(`${Math.abs(layer.top)}m — ${Math.abs(layer.bottom)}m`, 12, 55);

    const texture = new THREE.CanvasTexture(labelCanvas);
    const spriteMat = new THREE.SpriteMaterial({ map: texture, transparent: true });
    const sprite = new THREE.Sprite(spriteMat);
    sprite.position.set(-CITY_WIDTH / 2 - 12, yPos, -CITY_DEPTH / 2 + 10);
    sprite.scale.set(20, 2.5, 1);
    group.add(sprite);
  });

  const gwGeo = new THREE.PlaneGeometry(CITY_WIDTH, CITY_DEPTH);
  const gwMat = new THREE.MeshStandardMaterial({
    color: 0x2244aa,
    emissive: 0x112244,
    emissiveIntensity: 0.2,
    transparent: true,
    opacity: 0.15,
    side: THREE.DoubleSide
  });
  const gwPlane = new THREE.Mesh(gwGeo, gwMat);
  gwPlane.rotation.x = -Math.PI / 2;
  gwPlane.position.set(0, -12, -CITY_DEPTH / 2 + 10);
  gwPlane.name = "groundwater";
  group.add(gwPlane);

  return group;
}

function buildTunnelSegments(ringCount = 80) {
  const group = new THREE.Group();
  group.name = "tunnel-segments";

  for (let i = 0; i < ringCount; i++) {
    const z = -3 - i * RING_LEN;
    const segGeo = new THREE.CylinderGeometry(TUNNEL_RADIUS, TUNNEL_RADIUS, RING_LEN * 0.92, 24, 1, true);
    const segMat = new THREE.MeshStandardMaterial({
      color: 0x888899,
      roughness: 0.7,
      metalness: 0.15,
      transparent: true,
      opacity: 0.75,
      side: THREE.DoubleSide
    });
    const seg = new THREE.Mesh(segGeo, segMat);
    seg.rotation.x = Math.PI / 2;
    seg.position.set(0, -TUNNEL_DEPTH, z);
    seg.name = `ring-${80 - i}`;
    group.add(seg);

    if (i % 5 === 0) {
      const boltGeo = new THREE.CylinderGeometry(0.08, 0.08, 0.4, 6);
      const boltMat = new THREE.MeshStandardMaterial({ color: 0xcccccc, metalness: 0.8, roughness: 0.3 });
      for (let a = 0; a < 6; a++) {
        const angle = (a / 6) * Math.PI * 2;
        const bolt = new THREE.Mesh(boltGeo, boltMat);
        bolt.position.set(
          Math.cos(angle) * TUNNEL_RADIUS,
          -TUNNEL_DEPTH + Math.sin(angle) * TUNNEL_RADIUS,
          z
        );
        bolt.rotation.x = Math.PI / 2;
        group.add(bolt);
      }
    }
  }

  const innerGeo = new THREE.CylinderGeometry(TUNNEL_RADIUS - 0.4, TUNNEL_RADIUS - 0.4, ringCount * RING_LEN, 24, 1, true);
  const innerMat = new THREE.MeshStandardMaterial({
    color: 0x555566,
    roughness: 0.8,
    transparent: true,
    opacity: 0.15,
    side: THREE.BackSide
  });
  const inner = new THREE.Mesh(innerGeo, innerMat);
  inner.rotation.x = Math.PI / 2;
  inner.position.set(0, -TUNNEL_DEPTH, -3 - (ringCount * RING_LEN) / 2);
  group.add(inner);

  return group;
}

function buildTBM() {
  const group = new THREE.Group();
  group.name = "tbm";

  const cutterGroup = new THREE.Group();
  cutterGroup.name = "cutterhead";

  const faceGeo = new THREE.CylinderGeometry(TUNNEL_RADIUS, TUNNEL_RADIUS, 0.6, 48, 1, true);
  const faceMat = new THREE.MeshStandardMaterial({ color: 0x7a7a8a, roughness: 0.5, metalness: 0.6 });
  const face = new THREE.Mesh(faceGeo, faceMat);
  face.rotation.x = Math.PI / 2;
  cutterGroup.add(face);

  const hubGeo = new THREE.CylinderGeometry(1.0, 1.0, 1.6, 24);
  const hubMat = new THREE.MeshStandardMaterial({ color: 0xff00e5, emissive: 0xff00e5, emissiveIntensity: 0.5 });
  const hub = new THREE.Mesh(hubGeo, hubMat);
  hub.rotation.x = Math.PI / 2;
  hub.position.z = 0.3;
  cutterGroup.add(hub);

  [1.4, 2.2, 2.8].forEach((rad) => {
    const torusGeo = new THREE.TorusGeometry(rad, 0.1, 8, 32);
    const torusMat = new THREE.MeshStandardMaterial({ color: 0xaaaaaa, metalness: 0.8, roughness: 0.3 });
    const torus = new THREE.Mesh(torusGeo, torusMat);
    torus.rotation.y = Math.PI / 2;
    torus.position.z = 0.4;
    cutterGroup.add(torus);
  });

  const spokeCount = 8;
  for (let i = 0; i < spokeCount; i++) {
    const angle = (i / spokeCount) * Math.PI * 2;
    const spokeGeo = new THREE.CylinderGeometry(0.1, 0.1, TUNNEL_RADIUS - 0.5, 6);
    const spokeMat = new THREE.MeshStandardMaterial({ color: 0xaaaaaa, metalness: 0.7, roughness: 0.4 });
    const spoke = new THREE.Mesh(spokeGeo, spokeMat);
    spoke.rotation.z = angle;
    spoke.rotation.x = Math.PI / 2;
    spoke.position.z = 0.4;
    cutterGroup.add(spoke);
  }

  for (let i = 0; i < 12; i++) {
    const angle = (i / 12) * Math.PI * 2;
    const cutterGeo = new THREE.BoxGeometry(0.3, 0.2, 0.4);
    const cutterMat = new THREE.MeshStandardMaterial({ color: 0xdddd00, metalness: 0.7, roughness: 0.4 });
    const cutter = new THREE.Mesh(cutterGeo, cutterMat);
    cutter.position.set(Math.cos(angle) * (TUNNEL_RADIUS - 0.3), Math.sin(angle) * (TUNNEL_RADIUS - 0.3), 0.5);
    cutterGroup.add(cutter);
  }

  cutterGroup.position.set(0, -TUNNEL_DEPTH, -3);
  group.add(cutterGroup);

  const shieldGeo = new THREE.CylinderGeometry(TUNNEL_RADIUS + 0.1, TUNNEL_RADIUS + 0.1, 8, 32, 1, true);
  const shieldMat = new THREE.MeshStandardMaterial({
    color: 0x7c3aed,
    emissive: 0x7c3aed,
    emissiveIntensity: 0.15,
    transparent: true,
    opacity: 0.5,
    side: THREE.DoubleSide
  });
  const shield = new THREE.Mesh(shieldGeo, shieldMat);
  shield.rotation.x = Math.PI / 2;
  shield.position.set(0, -TUNNEL_DEPTH, 3);
  group.add(shield);

  const hydColors = [0xff4444, 0x44ff44, 0x4444ff, 0xffff44, 0xff44ff, 0x44ffff];
  for (let i = 0; i < 6; i++) {
    const angle = (i / 6) * Math.PI * 2;
    const hydGeo = new THREE.CylinderGeometry(0.12, 0.12, 4, 6);
    const hydMat = new THREE.MeshStandardMaterial({ color: hydColors[i], metalness: 0.6, roughness: 0.4 });
    const hyd = new THREE.Mesh(hydGeo, hydMat);
    hyd.position.set(Math.cos(angle) * 2.2, -TUNNEL_DEPTH + Math.sin(angle) * 2.2, 4);
    hyd.rotation.x = Math.PI / 2;
    group.add(hyd);
  }

  const screwGeo = new THREE.CylinderGeometry(0.25, 0.25, 12, 8);
  const screwMat = new THREE.MeshStandardMaterial({ color: 0xaaaaaa, metalness: 0.7, roughness: 0.4 });
  const screw = new THREE.Mesh(screwGeo, screwMat);
  screw.rotation.x = Math.PI / 2;
  screw.position.set(0, -TUNNEL_DEPTH - 1.5, 6);
  group.add(screw);

  const cabinGeo = new THREE.BoxGeometry(2, 1.5, 3);
  const cabinMat = new THREE.MeshStandardMaterial({ color: 0x334455, roughness: 0.6, metalness: 0.3 });
  const cabin = new THREE.Mesh(cabinGeo, cabinMat);
  cabin.position.set(0, -TUNNEL_DEPTH + 2, 7);
  group.add(cabin);

  const screenGeo = new THREE.PlaneGeometry(1.5, 1);
  const screenMat = new THREE.MeshStandardMaterial({ color: 0x00ff88, emissive: 0x00ff88, emissiveIntensity: 0.8 });
  const screen = new THREE.Mesh(screenGeo, screenMat);
  screen.position.set(0, -TUNNEL_DEPTH + 2.2, 5.49);
  group.add(screen);

  const beaconGeo = new THREE.SphereGeometry(0.4, 16, 12);
  const beaconMat = new THREE.MeshStandardMaterial({ color: 0x00f0ff, emissive: 0x00f0ff, emissiveIntensity: 0.9 });
  const beacon = new THREE.Mesh(beaconGeo, beaconMat);
  beacon.position.set(0, -TUNNEL_DEPTH + TUNNEL_RADIUS + 1, -3);
  beacon.name = "tbm-beacon";
  group.add(beacon);

  return group;
}

function buildSettlementHeatmap() {
  const group = new THREE.Group();
  group.name = "settlement-heatmap";

  const canvas = document.createElement("canvas");
  canvas.width = 400;
  canvas.height = 200;
  const ctx = canvas.getContext("2d");

  ctx.fillStyle = "rgba(0,0,0,0)";
  ctx.fillRect(0, 0, 400, 200);

  const tunnelZ = -15;
  for (let x = 0; x < 400; x++) {
    for (let y = 0; y < 200; y++) {
      const wx = (x / 400 - 0.5) * CITY_WIDTH;
      const wy = (y / 200 - 0.5) * CITY_DEPTH;
      const distFromTunnel = Math.abs(wy - tunnelZ);
      const distFromCenter = Math.abs(wx) * 0.3;
      const settle = Math.max(0, 1 - (distFromTunnel / 30)) * Math.max(0, 1 - (distFromCenter / 40));

      if (settle > 0.05) {
        let r, g, b;
        if (settle < 0.3) { r = 0; g = 204; b = 102; }
        else if (settle < 0.6) { r = 255; g = 136; b = 0; }
        else if (settle < 0.8) { r = 255; g = 255; b = 0; }
        else { r = 255; g = 45; b = 111; }

        ctx.fillStyle = `rgba(${r},${g},${b},${settle * 0.4})`;
        ctx.fillRect(x, y, 2, 2);
      }
    }
  }

  const texture = new THREE.CanvasTexture(canvas);
  const planeMat = new THREE.MeshBasicMaterial({ map: texture, transparent: true, depthWrite: false });
  const plane = new THREE.Mesh(new THREE.PlaneGeometry(CITY_WIDTH, CITY_DEPTH), planeMat);
  plane.rotation.x = -Math.PI / 2;
  plane.position.set(0, 0.15, -CITY_DEPTH / 2 + 10);
  group.add(plane);

  return group;
}

function buildSensorNetwork() {
  const group = new THREE.Group();
  group.name = "sensor-network";

  SENSOR_DEFS.forEach((sensor, i) => {
    const sGroup = new THREE.Group();
    sGroup.name = `sensor-${sensor.label}`;

    const color = SENSOR_COLORS[sensor.type] || 0xffffff;
    const statusColor = STATUS_COLORS[sensor.status] || 0x555555;

    const nodeGeo = new THREE.OctahedronGeometry(0.4, 0);
    const nodeMat = new THREE.MeshStandardMaterial({
      color: color,
      emissive: color,
      emissiveIntensity: 0.6,
      transparent: true,
      opacity: 0.9
    });
    const node = new THREE.Mesh(nodeGeo, nodeMat);
    sGroup.add(node);

    const ringGeo = new THREE.RingGeometry(0.6, 0.8, 16);
    const ringMat = new THREE.MeshBasicMaterial({
      color: statusColor,
      transparent: true,
      opacity: 0.5,
      side: THREE.DoubleSide
    });
    const ring = new THREE.Mesh(ringGeo, ringMat);
    ring.rotation.x = -Math.PI / 2;
    sGroup.add(ring);

    const labelCanvas = document.createElement("canvas");
    labelCanvas.width = 256;
    labelCanvas.height = 64;
    const ctx = labelCanvas.getContext("2d");
    ctx.fillStyle = "rgba(0,0,0,0.8)";
    ctx.fillRect(0, 0, 256, 64);
    ctx.fillStyle = "#" + color.toString(16).padStart(6, "0");
    ctx.font = "bold 24px JetBrains Mono, monospace";
    ctx.fillText(sensor.label, 10, 28);
    ctx.fillStyle = "#aaaacc";
    ctx.font = "16px Inter, sans-serif";
    ctx.fillText(sensor.type.toUpperCase(), 10, 52);

    const texture = new THREE.CanvasTexture(labelCanvas);
    const spriteMat = new THREE.SpriteMaterial({ map: texture, transparent: true });
    const sprite = new THREE.Sprite(spriteMat);
    sprite.position.set(0, 1.2, 0);
    sprite.scale.set(4, 1, 1);
    sGroup.add(sprite);

    sGroup.position.set(sensor.x, sensor.y, sensor.z);
    group.add(sGroup);

    const lineGeo = new THREE.BufferGeometry();
    const lineVerts = new Float32Array([
      sensor.x, sensor.y, sensor.z,
      sensor.x, Math.min(sensor.y + 5, 2), sensor.z
    ]);
    lineGeo.setAttribute("position", new THREE.BufferAttribute(lineVerts, 3));
    const lineMat = new THREE.LineBasicMaterial({ color: color, transparent: true, opacity: 0.3 });
    const line = new THREE.Line(lineGeo, lineMat);
    group.add(line);
  });

  const connectionPairs = [[0, 1], [1, 2], [3, 4], [5, 6], [7, 8], [9, 10]];
  connectionPairs.forEach(([a, b]) => {
    if (a < SENSOR_DEFS.length && b < SENSOR_DEFS.length) {
      const sa = SENSOR_DEFS[a];
      const sb = SENSOR_DEFS[b];
      const connGeo = new THREE.BufferGeometry();
      const connVerts = new Float32Array([
        sa.x, sa.y, sa.z,
        sb.x, sb.y, sb.z
      ]);
      connGeo.setAttribute("position", new THREE.BufferAttribute(connVerts, 3));
      const connMat = new THREE.LineBasicMaterial({ color: 0x00f0ff, transparent: true, opacity: 0.12 });
      group.add(new THREE.Line(connGeo, connMat));
    }
  });

  return group;
}

function buildGroundwaterTable() {
  const group = new THREE.Group();
  group.name = "gw-table";

  const gwGeo = new THREE.PlaneGeometry(CITY_WIDTH - 10, CITY_DEPTH - 20);
  const gwMat = new THREE.MeshStandardMaterial({
    color: 0x1a3366,
    emissive: 0x0a1a33,
    emissiveIntensity: 0.3,
    transparent: true,
    opacity: 0.2,
    side: THREE.DoubleSide
  });
  const gw = new THREE.Mesh(gwGeo, gwMat);
  gw.rotation.x = -Math.PI / 2;
  gw.position.set(0, -12, -CITY_DEPTH / 2 + 10);
  group.add(gw);

  return group;
}

export default function CityTunnelCrossSection({ onToast }) {
  const mountRef = useRef(null);
  const holderRef = useRef(null);
  const [hoveredBuilding, setHoveredBuilding] = useState(null);
  const [tbmData, setTbmData] = useState({
    chainage: 102.4, ring: 64, thrust: 14500, torque: 3200,
    rpm: 1.8, facePressure: 185, advanceRate: 42,
    status: "NORMAL", settlement: 4.2, predictedSettlement: 4.5
  });

  const sceneRef = useRef(null);
  const tbmRef = useRef(null);
  const cutterRef = useRef(null);

  useEffect(() => {
    const holder = holderRef.current;
    const mount = mountRef.current;
    if (!holder || !mount) return;

    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x060612);
    scene.fog = new THREE.FogExp2(0x060612, 0.006);
    sceneRef.current = scene;

    const camera = new THREE.PerspectiveCamera(50, mount.clientWidth / mount.clientHeight, 0.1, 500);
    camera.position.set(40, 30, 50);
    camera.lookAt(0, -8, -20);

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false });
    renderer.setSize(mount.clientWidth, mount.clientHeight);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.1;
    mount.appendChild(renderer.domElement);

    const controls = new OrbitControls(camera, renderer.domElement);
    controls.target.set(0, -8, -20);
    controls.enableDamping = true;
    controls.maxPolarAngle = Math.PI * 0.85;
    controls.minDistance = 8;
    controls.maxDistance = 120;
    controls.update();

    scene.add(new THREE.AmbientLight(0x334466, 0.7));
    const sun = new THREE.DirectionalLight(0xffeedd, 1.3);
    sun.position.set(30, 40, 25);
    sun.castShadow = true;
    sun.shadow.mapSize.set(2048, 2048);
    sun.shadow.camera.left = -60;
    sun.shadow.camera.right = 60;
    sun.shadow.camera.top = 40;
    sun.shadow.camera.bottom = -40;
    scene.add(sun);

    const cyanLight = new THREE.PointLight(0x00f0ff, 0.8, 50);
    cyanLight.position.set(-20, 5, -20);
    scene.add(cyanLight);

    const magentaLight = new THREE.PointLight(0xff00e5, 0.6, 50);
    magentaLight.position.set(20, -10, -25);
    scene.add(magentaLight);

    const tunnelLight = new THREE.PointLight(0x00ff88, 1.0, 30);
    tunnelLight.position.set(0, -TUNNEL_DEPTH, -5);
    scene.add(tunnelLight);

    const grid = new THREE.GridHelper(CITY_WIDTH, 60, 0x1a1a3a, 0x0d0d2a);
    grid.position.y = 0.01;
    scene.add(grid);

    scene.add(buildCitySurface());
    scene.add(buildBuildings());
    scene.add(buildGeology());

    const tunnel = buildTunnelSegments(80);
    scene.add(tunnel);

    const tbm = buildTBM();
    scene.add(tbm);
    tbmRef.current = tbm;
    cutterRef.current = tbm.getObjectByName("cutterhead");

    scene.add(buildSettlementHeatmap());
    scene.add(buildSensorNetwork());
    scene.add(buildGroundwaterTable());

    const crossSectionPlane = new THREE.PlaneGeometry(CITY_WIDTH, 50);
    const crossSectionMat = new THREE.MeshBasicMaterial({
      color: 0x00f0ff,
      transparent: true,
      opacity: 0.03,
      side: THREE.DoubleSide
    });
    const crossSection = new THREE.Mesh(crossSectionPlane, crossSectionMat);
    crossSection.position.set(0, -20, -CITY_DEPTH / 2 + 10);
    scene.add(crossSection);

    const raycaster = new THREE.Raycaster();
    const mouse = new THREE.Vector2();

    function onPick(e) {
      const rect = renderer.domElement.getBoundingClientRect();
      mouse.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
      mouse.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;
      raycaster.setFromCamera(mouse, camera);

      const buildings = scene.getObjectByName("buildings");
      if (buildings) {
        const hits = raycaster.intersectObjects(buildings.children, true);
        if (hits.length > 0) {
          let obj = hits[0].object;
          while (obj && !obj.userData.type) obj = obj.parent;
          if (obj && obj.userData.type) {
            setHoveredBuilding(obj.userData);
          } else {
            setHoveredBuilding(null);
          }
        } else {
          setHoveredBuilding(null);
        }
      }
    }
    renderer.domElement.addEventListener("pointermove", onPick);

    let raf = 0;
    const clock = new THREE.Clock();

    function animate() {
      raf = requestAnimationFrame(animate);
      const t = clock.getElapsedTime();

      if (cutterRef.current) {
        cutterRef.current.rotation.z = t * 0.5;
      }

      const beacon = tbmRef.current?.getObjectByName("tbm-beacon");
      if (beacon) {
        beacon.position.y = -TUNNEL_DEPTH + TUNNEL_RADIUS + 1 + Math.sin(t * 2) * 0.3;
      }

      scene.getObjectByName("sensor-network")?.children.forEach((child, i) => {
        if (child.isGroup) {
          const ring = child.children[1];
          if (ring) {
            ring.rotation.z = t * 0.5 + i * 0.3;
            ring.scale.setScalar(1 + Math.sin(t * 2 + i) * 0.1);
          }
        }
      });

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

  const sensorsByStatus = useMemo(() => {
    const counts = { normal: 0, warning: 0, alert: 0, offline: 0 };
    SENSOR_DEFS.forEach((s) => { counts[s.status] = (counts[s.status] || 0) + 1; });
    return counts;
  }, []);

  return (
    <>
      <div className="city-tunnel-layout">
        <div className="city-tunnel-3d" ref={holderRef}>
          <div ref={mountRef} className="twin-3d-mount" />
          <div className="twin-3d-label">
            {hoveredBuilding
              ? `BUILDING: ${hoveredBuilding.type.toUpperCase()} | RISK: ${hoveredBuilding.risk.toUpperCase()}`
              : "DRAG TO ORBIT // SCROLL TO ZOOM // HOVER BUILDINGS FOR RISK DATA"
            }
          </div>
          <div className="city-hud-overlay">
            <div className="hud-block">
              <span className="hud-label">TBM STATUS</span>
              <span className="hud-value hud-ok">{tbmData.status}</span>
            </div>
            <div className="hud-block">
              <span className="hud-label">CHAINAGE</span>
              <span className="hud-value">{tbmData.chainage}m</span>
            </div>
            <div className="hud-block">
              <span className="hud-label">DEPTH</span>
              <span className="hud-value">{TUNNEL_DEPTH}m</span>
            </div>
            <div className="hud-block">
              <span className="hud-label">SETTLEMENT</span>
              <span className="hud-value hud-warn">{tbmData.settlement}mm</span>
            </div>
            <div className="hud-block">
              <span className="hud-label">PREDICTED</span>
              <span className="hud-value">{tbmData.predictedSettlement}mm</span>
            </div>
            <div className="hud-block">
              <span className="hud-label">RISK LEVEL</span>
              <span className="hud-value hud-ok">LOW</span>
            </div>
            <div className="hud-block">
              <span className="hud-label">SENSORS</span>
              <span className="hud-value">{SENSOR_DEFS.length} ACTIVE</span>
            </div>
          </div>
        </div>

        <div className="city-tunnel-panel">
          <div className="twin-hud">
            <div className="twin-hud-title">SHIELD-OS // DIGITAL TWIN</div>
            <div className="twin-hud-status">TUNNEL CROSS-SECTION VIEW</div>
          </div>

          <div className="twin-hud">
            <div className="twin-hud-title">TBM OPERATIONS</div>
            <div className="twin-hud-row"><span>CHAINAGE</span><b>{tbmData.chainage}m</b></div>
            <div className="twin-hud-row"><span>RING</span><b>#{tbmData.ring}</b></div>
            <div className="twin-hud-row"><span>THRUST</span><b>{tbmData.thrust}kN</b></div>
            <div className="twin-hud-row"><span>TORQUE</span><b>{tbmData.torque}kNm</b></div>
            <div className="twin-hud-row"><span>CUTTERHEAD</span><b>{tbmData.rpm} RPM</b></div>
            <div className="twin-hud-row"><span>FACE PRESS</span><b>{tbmData.facePressure}kPa</b></div>
            <div className="twin-hud-row"><span>ADVANCE</span><b>{tbmData.advanceRate}mm/min</b></div>
          </div>

          <div className="twin-hud">
            <div className="twin-hud-title">GEOLOGICAL PROFILE</div>
            {GEO_LAYERS.map((l) => (
              <div key={l.name} className="twin-hud-row" style={{ borderLeft: `3px solid #${l.color.toString(16).padStart(6, "0")}` }}>
                <span>{l.name}</span>
                <b>{Math.abs(l.top)}—{Math.abs(l.bottom)}m</b>
              </div>
            ))}
          </div>

          <div className="twin-hud">
            <div className="twin-hud-title">BUILDING RISK ANALYSIS</div>
            {BUILDING_DEFS.filter((b) => b.risk !== "low").map((b, i) => (
              <div key={i} className="twin-hud-row">
                <span style={{ color: `#${RISK_COLORS[b.risk].toString(16).padStart(6, "0")}` }}>
                  {b.type.toUpperCase()} @({b.x},{b.z})
                </span>
                <b className={b.risk === "critical" ? "sev-critical" : b.risk === "high" ? "sev-high" : "sev-warning"}>
                  {b.risk.toUpperCase()}
                </b>
              </div>
            ))}
          </div>

          <div className="twin-hud">
            <div className="twin-hud-title">IoT SENSOR NETWORK</div>
            <div className="twin-hud-row"><span className="shm-status ok">NORMAL</span><b>{sensorsByStatus.normal}</b></div>
            <div className="twin-hud-row"><span className="sev-warning">WARNING</span><b>{sensorsByStatus.warning}</b></div>
            <div className="twin-hud-row"><span className="sev-critical">ALERT</span><b>{sensorsByStatus.alert}</b></div>
            {Object.entries(SENSOR_COLORS).map(([type, color]) => (
              <div key={type} className="twin-hud-row">
                <span style={{ color: `#${color.toString(16).padStart(6, "0")}` }}>{type.toUpperCase()}</span>
                <b>{SENSOR_DEFS.filter((s) => s.type === type).length}</b>
              </div>
            ))}
          </div>

          {hoveredBuilding && (
            <div className="twin-hud twin-hud-hover">
              <div className="twin-hud-title">BUILDING INSPECTION</div>
              <div className="twin-hud-row"><span>TYPE</span><b>{hoveredBuilding.type.toUpperCase()}</b></div>
              <div className="twin-hud-row"><span>HEIGHT</span><b>{hoveredBuilding.h}m</b></div>
              <div className="twin-hud-row"><span>POSITION</span><b>({hoveredBuilding.x}, {hoveredBuilding.z})</b></div>
              <div className="twin-hud-row"><span>FOUNDATION</span><b>PILE</b></div>
              <div className="twin-hud-row"><span>DISTANCE</span><b>{Math.abs(hoveredBuilding.z + TUNNEL_DEPTH).toFixed(0)}m from tunnel</b></div>
              <div className="twin-hud-row"><span>RISK</span>
                <b style={{ color: `#${RISK_COLORS[hoveredBuilding.risk].toString(16).padStart(6, "0")}` }}>
                  {hoveredBuilding.risk.toUpperCase()}
                </b>
              </div>
              <div className="twin-hud-row"><span>MONITORING</span>
                <b className={hoveredBuilding.risk === "critical" || hoveredBuilding.risk === "high" ? "sev-critical" : "shm-status ok"}>
                  {hoveredBuilding.risk === "critical" ? "ALERT" : hoveredBuilding.risk === "high" ? "WARNING" : "NORMAL"}
                </b>
              </div>
            </div>
          )}

          <div className="twin-legend">
            <span className="lg lg-green">LOW RISK</span>
            <span className="lg lg-orange">MEDIUM</span>
            <span className="lg lg-red">HIGH</span>
            <span className="lg lg-pink">CRITICAL</span>
          </div>
        </div>
      </div>
    </>
  );
}
