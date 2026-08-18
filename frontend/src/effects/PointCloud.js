/**
 * FORGE3D Innovation #9: Point Cloud Integration
 * LiDAR/photogrammetry point cloud rendering in Three.js
 */
import * as THREE from "three";

/**
 * Generate a synthetic ring point cloud (simulating LiDAR scan data)
 * In production, this would load real .las/.laz/.ply files
 */
export function generateRingPointCloud(ringNo = 1, nominalRadiusM = 3.2, nPoints = 2048) {
  const positions = new Float32Array(nPoints * 3);
  const colors = new Float32Array(nPoints * 3);
  const normals = new Float32Array(nPoints * 3);

  for (let i = 0; i < nPoints; i++) {
    const theta = (i / nPoints) * Math.PI * 2;
    const phi = Math.random() * Math.PI;
    
    // Nominal radius with random deviation (simulating ovalization)
    const deviation = (Math.random() - 0.5) * 0.02; // +/- 1% ovalization
    const r = nominalRadiusM * (1 + deviation);
    
    const i3 = i * 3;
    positions[i3] = r * Math.cos(theta) * Math.sin(phi);
    positions[i3 + 1] = r * Math.sin(theta) * Math.sin(phi);
    positions[i3 + 2] = (Math.random() - 0.5) * 1.6; // Ring width

    // Color by deviation from nominal
    const devMM = Math.abs(deviation * nominalRadiusM * 1000);
    if (devMM < 5) {
      colors[i3] = 0; colors[i3 + 1] = 0.8; colors[i3 + 2] = 0.4; // Green
    } else if (devMM < 15) {
      colors[i3] = 1; colors[i3 + 1] = 0.7; colors[i3 + 2] = 0; // Orange
    } else {
      colors[i3] = 1; colors[i3 + 1] = 0.2; colors[i3 + 2] = 0.4; // Red
    }

    // Normals (radial)
    normals[i3] = Math.cos(theta) * Math.sin(phi);
    normals[i3 + 1] = Math.sin(theta) * Math.sin(phi);
    normals[i3 + 2] = Math.cos(phi);
  }

  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute("position", new THREE.BufferAttribute(positions, 3));
  geometry.setAttribute("color", new THREE.BufferAttribute(colors, 3));
  geometry.setAttribute("normal", new THREE.BufferAttribute(normals, 3));

  return geometry;
}

/**
 * Build a complete point cloud scene for a ring
 */
export function buildPointCloudGroup(ringNo, nominalRadiusM = 3.2) {
  const group = new THREE.Group();
  group.name = `pointcloud-ring-${ringNo}`;

  // Point cloud
  const geo = generateRingPointCloud(ringNo, nominalRadiusM, 4096);
  const mat = new THREE.PointsMaterial({
    size: 0.02,
    vertexColors: true,
    sizeAttenuation: true,
  });
  const points = new THREE.Points(geo, mat);
  group.add(points);

  // Wireframe reference ring
  const wireGeo = new THREE.TorusGeometry(nominalRadiusM, 0.02, 8, 64);
  const wireMat = new THREE.MeshBasicMaterial({ color: 0x00ffff, wireframe: true, transparent: true, opacity: 0.3 });
  const wire = new THREE.Mesh(wireGeo, wireMat);
  wire.rotation.y = Math.PI / 2;
  group.add(wire);

  return group;
}

/**
 * PointCloudViewer component - renders LiDAR data in Three.js
 * This is a utility class, not a React component
 */
export class PointCloudRenderer {
  constructor(container) {
    this.container = container;
    this.scene = null;
    this.camera = null;
    this.renderer = null;
    this.controls = null;
    this.pointClouds = {};
  }

  init() {
    this.scene = new THREE.Scene();
    this.scene.background = new THREE.Color(0x0a0a1a);

    this.camera = new THREE.PerspectiveCamera(
      55,
      this.container.clientWidth / this.container.clientHeight,
      0.1,
      100
    );
    this.camera.position.set(5, 3, 5);

    this.renderer = new THREE.WebGLRenderer({ antialias: true });
    this.renderer.setSize(this.container.clientWidth, this.container.clientHeight);
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    this.container.appendChild(this.renderer.domElement);

    this.scene.add(new THREE.AmbientLight(0x404060, 0.8));
    const sun = new THREE.DirectionalLight(0xffffff, 1.0);
    sun.position.set(5, 10, 5);
    this.scene.add(sun);

    this.animate();
  }

  addRing(ringNo, nominalRadiusM = 3.2) {
    const group = buildPointCloudGroup(ringNo, nominalRadiusM);
    this.scene.add(group);
    this.pointClouds[ringNo] = group;
    return group;
  }

  removeRing(ringNo) {
    if (this.pointClouds[ringNo]) {
      this.scene.remove(this.pointClouds[ringNo]);
      delete this.pointClouds[ringNo];
    }
  }

  animate() {
    requestAnimationFrame(() => this.animate());
    if (this.renderer && this.scene && this.camera) {
      this.renderer.render(this.scene, this.camera);
    }
  }

  dispose() {
    if (this.renderer) {
      this.renderer.dispose();
      this.container.removeChild(this.renderer.domElement);
    }
  }
}
