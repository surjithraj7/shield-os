/**
 * FORGE3D Innovation #10: BIM/IFC Import
 * Load IFC building models for surrounding structure visualization
 * Uses three.js IFC loader for BIM integration
 */
import * as THREE from "three";

/**
 * Simplified BIM building representation
 * In production, use web-ifc-three for full IFC parsing
 */
export class BIMLoader {
  constructor() {
    this.buildings = new Map();
  }

  /**
   * Load a building from simplified JSON definition
   * @param {Object} buildingDef - Building definition with geometry
   */
  loadBuilding(buildingDef) {
    const group = new THREE.Group();
    group.name = `bim-${buildingDef.id}`;

    // Building footprint
    if (buildingDef.footprint) {
      const shape = new THREE.Shape();
      const fp = buildingDef.footprint;
      shape.moveTo(fp[0][0], fp[0][1]);
      for (let i = 1; i < fp.length; i++) {
        shape.lineTo(fp[i][0], fp[i][1]);
      }
      shape.closePath();

      const extrudeSettings = {
        depth: buildingDef.height || 10,
        bevelEnabled: false,
      };

      const geo = new THREE.ExtrudeGeometry(shape, extrudeSettings);
      const mat = new THREE.MeshStandardMaterial({
        color: buildingDef.color || 0x8899aa,
        transparent: true,
        opacity: 0.6,
        side: THREE.DoubleSide,
      });
      const mesh = new THREE.Mesh(geo, mat);
      mesh.rotation.x = -Math.PI / 2;
      mesh.position.set(
        buildingDef.x || 0,
        buildingDef.y || 0,
        buildingDef.z || 0
      );
      group.add(mesh);

      // Building outline
      const edges = new THREE.EdgesGeometry(geo);
      const lineMat = new THREE.LineBasicMaterial({
        color: 0x00ffff,
        transparent: true,
        opacity: 0.8,
      });
      const wireframe = new THREE.LineSegments(edges, lineMat);
      wireframe.rotation.x = -Math.PI / 2;
      wireframe.position.copy(mesh.position);
      group.add(wireframe);
    }

    // Foundation depth indicator
    if (buildingDef.foundation_depth_m) {
      const foundGeo = new THREE.BoxGeometry(
        (buildingDef.footprint_width || 10) + 2,
        buildingDef.foundation_depth_m,
        (buildingDef.footprint_depth || 10) + 2
      );
      const foundMat = new THREE.MeshBasicMaterial({
        color: 0x654321,
        transparent: true,
        opacity: 0.2,
        wireframe: true,
      });
      const foundation = new THREE.Mesh(foundGeo, foundMat);
      foundation.position.set(
        buildingDef.x || 0,
        -buildingDef.foundation_depth_m / 2,
        buildingDef.z || 0
      );
      group.add(foundation);
    }

    // Label
    const canvas = document.createElement("canvas");
    canvas.width = 256;
    canvas.height = 64;
    const ctx = canvas.getContext("2d");
    ctx.fillStyle = "rgba(0,0,0,0.7)";
    ctx.fillRect(0, 0, 256, 64);
    ctx.fillStyle = "#00ffff";
    ctx.font = "bold 16px Courier New";
    ctx.fillText(buildingDef.name || "Building", 10, 25);
    ctx.fillStyle = "#ffffff";
    ctx.font = "12px Courier New";
    ctx.fillText(`Clearance: ${buildingDef.clearance_m || "N/A"}m`, 10, 50);

    const texture = new THREE.CanvasTexture(canvas);
    const spriteMat = new THREE.SpriteMaterial({ map: texture, transparent: true });
    const sprite = new THREE.Sprite(spriteMat);
    sprite.position.set(
      buildingDef.x || 0,
      (buildingDef.height || 10) + 2,
      buildingDef.z || 0
    );
    sprite.scale.set(10, 2.5, 1);
    group.add(sprite);

    this.buildings.set(buildingDef.id, group);
    return group;
  }

  /**
   * Get all loaded buildings as a group
   */
  getAllBuildings() {
    const allGroup = new THREE.Group();
    allGroup.name = "bim-buildings";
    this.buildings.forEach((building) => {
      allGroup.add(building);
    });
    return allGroup;
  }

  removeBuilding(id) {
    if (this.buildings.has(id)) {
      this.buildings.delete(id);
    }
  }

  dispose() {
    this.buildings.clear();
  }
}

/**
 * Default buildings for Beijing Metro Line 12 context
 */
export const DEFAULT_BUILDINGS = [
  {
    id: "bld-001",
    name: "Building B-01",
    x: 15,
    y: 0,
    z: -20,
    height: 18,
    foundation_depth_m: 6,
    clearance_m: 8.5,
    color: 0x8899aa,
    footprint: [[-5, -5], [5, -5], [5, 5], [-5, 5]],
    footprint_width: 10,
    footprint_depth: 10,
  },
  {
    id: "bld-002",
    name: "Building B-02",
    x: -20,
    y: 0,
    z: -40,
    height: 12,
    foundation_depth_m: 4,
    clearance_m: 5.2,
    color: 0x998877,
    footprint: [[-4, -6], [4, -6], [4, 6], [-4, 6]],
    footprint_width: 8,
    footprint_depth: 12,
  },
  {
    id: "bld-003",
    name: "Water Tower",
    x: 25,
    y: 0,
    z: -60,
    height: 8,
    foundation_depth_m: 3,
    clearance_m: 3.1,
    color: 0x667788,
    footprint: [[-2, -2], [2, -2], [2, 2], [-2, 2]],
    footprint_width: 4,
    footprint_depth: 4,
  },
];
