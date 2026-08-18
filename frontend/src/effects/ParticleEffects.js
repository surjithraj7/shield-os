/**
 * FORGE3D Innovation #4: Real-time Particle Effects
 * Muck flow, grout injection, dust clouds in Three.js digital twin
 */

import * as THREE from "three";

// ============================================================
// Particle System Base Class
// ============================================================

class ParticleSystem {
  constructor(scene, config = {}) {
    this.scene = scene;
    this.config = {
      count: config.count || 500,
      position: config.position || new THREE.Vector3(0, 0, 0),
      spread: config.spread || new THREE.Vector3(1, 1, 1),
      color: config.color || 0x8B4513,
      size: config.size || 0.15,
      lifetime: config.lifetime || 3.0,
      speed: config.speed || 1.0,
      opacity: config.opacity || 0.8,
      gravity: config.gravity || new THREE.Vector3(0, -0.5, 0),
      ...config,
    };

    this.particles = [];
    this.group = new THREE.Group();
    this.scene.add(this.group);
    this.time = 0;
  }

  init() {
    // Create particle geometry
    const geometry = new THREE.BufferGeometry();
    const positions = new Float32Array(this.config.count * 3);
    const colors = new Float32Array(this.config.count * 3);
    const sizes = new Float32Array(this.config.count);
    const alphas = new Float32Array(this.config.count);

    const baseColor = new THREE.Color(this.config.color);

    for (let i = 0; i < this.config.count; i++) {
      const i3 = i * 3;

      // Random initial position within spread
      positions[i3] = this.config.position.x + (Math.random() - 0.5) * this.config.spread.x;
      positions[i3 + 1] = this.config.position.y + (Math.random() - 0.5) * this.config.spread.y;
      positions[i3 + 2] = this.config.position.z + (Math.random() - 0.5) * this.config.spread.z;

      // Color with slight variation
      colors[i3] = baseColor.r + (Math.random() - 0.5) * 0.1;
      colors[i3 + 1] = baseColor.g + (Math.random() - 0.5) * 0.1;
      colors[i3 + 2] = baseColor.b + (Math.random() - 0.5) * 0.1;

      sizes[i] = this.config.size * (0.5 + Math.random() * 0.5);
      alphas[i] = this.config.opacity;

      this.particles.push({
        velocity: new THREE.Vector3(
          (Math.random() - 0.5) * this.config.speed,
          (Math.random() - 0.5) * this.config.speed,
          (Math.random() - 0.5) * this.config.speed
        ),
        life: Math.random() * this.config.lifetime,
        maxLife: this.config.lifetime,
      });
    }

    geometry.setAttribute("position", new THREE.BufferAttribute(positions, 3));
    geometry.setAttribute("color", new THREE.BufferAttribute(colors, 3));
    geometry.setAttribute("size", new THREE.BufferAttribute(sizes, 1));
    geometry.setAttribute("alpha", new THREE.BufferAttribute(alphas, 1));

    const material = new THREE.PointsMaterial({
      size: this.config.size,
      vertexColors: true,
      transparent: true,
      opacity: this.config.opacity,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
      sizeAttenuation: true,
    });

    this.points = new THREE.Points(geometry, material);
    this.group.add(this.points);
  }

  update(dt) {
    this.time += dt;
    const positions = this.points.geometry.attributes.position.array;

    for (let i = 0; i < this.config.count; i++) {
      const i3 = i * 3;
      const p = this.particles[i];

      p.life += dt;
      if (p.life >= p.maxLife) {
        // Reset particle
        p.life = 0;
        positions[i3] = this.config.position.x + (Math.random() - 0.5) * this.config.spread.x;
        positions[i3 + 1] = this.config.position.y + (Math.random() - 0.5) * this.config.spread.y;
        positions[i3 + 2] = this.config.position.z + (Math.random() - 0.5) * this.config.spread.z;
        p.velocity.set(
          (Math.random() - 0.5) * this.config.speed,
          (Math.random() - 0.5) * this.config.speed,
          (Math.random() - 0.5) * this.config.speed
        );
      }

      // Apply velocity + gravity
      positions[i3] += p.velocity.x * dt;
      positions[i3 + 1] += (p.velocity.y + this.config.gravity.y * p.life) * dt;
      positions[i3 + 2] += p.velocity.z * dt;
    }

    this.points.geometry.attributes.position.needsUpdate = true;
  }

  dispose() {
    this.scene.remove(this.group);
    this.points.geometry.dispose();
    this.points.material.dispose();
  }
}

// ============================================================
// Muck Flow System (debris from cutterhead)
// ============================================================

export class MuckFlowEffect extends ParticleSystem {
  constructor(scene, config = {}) {
    super(scene, {
      count: 800,
      position: new THREE.Vector3(0, -2.5, -1),
      spread: new THREE.Vector3(2.5, 0.5, 1),
      color: 0x5c4033,
      size: 0.12,
      lifetime: 4.0,
      speed: 0.8,
      opacity: 0.9,
      gravity: new THREE.Vector3(0, -1.5, 0),
      ...config,
    });
    this.init();
  }
}

// ============================================================
// Grout Injection System (fluid behind shield)
// ============================================================

export class GroutEffect extends ParticleSystem {
  constructor(scene, config = {}) {
    super(scene, {
      count: 400,
      position: new THREE.Vector3(0, 0, 3.5),
      spread: new THREE.Vector3(0.8, 0.8, 2),
      color: 0x88aacc,
      size: 0.08,
      lifetime: 2.5,
      speed: 0.5,
      opacity: 0.6,
      gravity: new THREE.Vector3(0, 0.2, 0), // Grout flows outward
      ...config,
    });
    this.init();
  }
}

// ============================================================
// Dust Cloud System (ambient dust around excavation)
// ============================================================

export class DustCloudEffect extends ParticleSystem {
  constructor(scene, config = {}) {
    super(scene, {
      count: 300,
      position: new THREE.Vector3(0, 0, -2),
      spread: new THREE.Vector3(5, 3, 4),
      color: 0x998877,
      size: 0.25,
      lifetime: 5.0,
      speed: 0.2,
      opacity: 0.3,
      gravity: new THREE.Vector3(0, 0.1, 0.1),
      ...config,
    });
    this.init();
  }
}

// ============================================================
// Water Seepage Effect (for SHM alerts)
// ============================================================

export class WaterSeepageEffect extends ParticleSystem {
  constructor(scene, config = {}) {
    super(scene, {
      count: 200,
      position: config.position || new THREE.Vector3(3, -1, -5),
      spread: new THREE.Vector3(0.3, 1, 0.3),
      color: 0x4488cc,
      size: 0.06,
      lifetime: 2.0,
      speed: 0.3,
      opacity: 0.7,
      gravity: new THREE.Vector3(0, -2, 0),
      ...config,
    });
    this.init();
  }
}

// ============================================================
// Hydraulic Piston Steam Effect
// ============================================================

export class HydraulicSteamEffect extends ParticleSystem {
  constructor(scene, config = {}) {
    super(scene, {
      count: 150,
      position: config.position || new THREE.Vector3(2, 2, 0),
      spread: new THREE.Vector3(0.5, 0.3, 0.5),
      color: 0xcccccc,
      size: 0.1,
      lifetime: 1.5,
      speed: 0.6,
      opacity: 0.4,
      gravity: new THREE.Vector3(0, 1, 0), // Steam rises
      ...config,
    });
    this.init();
  }
}

// ============================================================
// Particle Effects Manager
// ============================================================

export class ParticleEffectsManager {
  constructor(scene) {
    this.scene = scene;
    this.effects = {};
    this.active = true;
  }

  addEffect(name, effectClass, config = {}) {
    const effect = new effectClass(this.scene, config);
    effect.init();
    this.effects[name] = effect;
    return effect;
  }

  removeEffect(name) {
    if (this.effects[name]) {
      this.effects[name].dispose();
      delete this.effects[name];
    }
  }

  update(dt) {
    if (!this.active) return;
    Object.values(this.effects).forEach((effect) => effect.update(dt));
  }

  setEnabled(enabled) {
    this.active = enabled;
    Object.values(this.effects).forEach((effect) => {
      effect.group.visible = enabled;
    });
  }

  dispose() {
    Object.values(this.effects).forEach((effect) => effect.dispose());
    this.effects = {};
  }
}
