/**
 * 3D Spatial Defect Mapping & Dynamic Decal Visualizer for Three.js Digital Twin
 * ==============================================================================
 * Maps 2D CCTV image pixel defect coordinates to 3D cylindrical UV world space
 * and renders interactive visual decals and animated alert sprites on tunnel ring segments.
 */

import * as THREE from 'three';

export interface DefectPayload {
  defect_id: string;
  class_name: 'Ring_Misalignment' | 'Gasket_Extrusion' | 'Water_Ingress' | 'Concrete_Spalling' | 'Joint_Gap';
  confidence: number;
  severity: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  uv_coordinates: [number, number]; // [theta_rad, z_local_m]
  world_3d_coords: [number, number, number]; // [X, Y, Z]
}

export class TunnelDefectVisualizer3D {
  private scene: THREE.Scene;
  private defectGroup: THREE.Group;
  private decalMaterials: Map<string, THREE.MeshBasicMaterial>;

  constructor(scene: THREE.Scene) {
    this.scene = scene;
    this.defectGroup = new THREE.Group();
    this.defectGroup.name = 'TunnelDefectsGroup';
    this.scene.add(this.defectGroup);

    this.decalMaterials = new Map([
      ['Water_Ingress', new THREE.MeshBasicMaterial({ color: 0x00aaff, side: THREE.DoubleSide, transparent: true, opacity: 0.85 })],
      ['Gasket_Extrusion', new THREE.MeshBasicMaterial({ color: 0xffaa00, side: THREE.DoubleSide, transparent: true, opacity: 0.85 })],
      ['Concrete_Spalling', new THREE.MeshBasicMaterial({ color: 0xff2244, side: THREE.DoubleSide, transparent: true, opacity: 0.85 })],
      ['Ring_Misalignment', new THREE.MeshBasicMaterial({ color: 0xaa00ff, side: THREE.DoubleSide, transparent: true, opacity: 0.85 })],
      ['Joint_Gap', new THREE.MeshBasicMaterial({ color: 0xffff00, side: THREE.DoubleSide, transparent: true, opacity: 0.85 })],
    ]);
  }

  /**
   * Projects 2D Pixel defect coordinates (x_pixel, y_pixel) onto 3D Cylindrical Ring Mesh UV space.
   */
  public projectPixelTo3DWorld(
    xPixel: number,
    yPixel: number,
    imageWidth: number,
    imageHeight: number,
    tunnelRadius: number,
    ringLength: number,
    ringOriginZ: number
  ): THREE.Vector3 {
    const uNorm = xPixel / imageWidth;
    const vNorm = yPixel / imageHeight;

    const thetaRad = uNorm * 2.0 * Math.PI;
    const zLocal = vNorm * ringLength;

    const X = tunnelRadius * Math.cos(thetaRad);
    const Y = tunnelRadius * Math.sin(thetaRad);
    const Z = ringOriginZ + zLocal;

    return new THREE.Vector3(X, Y, Z);
  }

  /**
   * Renders dynamic 3D defect decal marker and glowing aura on the tunnel wall.
   */
  public renderDefectOnTwin(defect: DefectPayload): THREE.Mesh {
    const [x, y, z] = defect.world_3d_coords;
    const position = new THREE.Vector3(x, y, z);

    // 1. Create Decal Geometry (Disk matching local tangent plane)
    const decalGeo = new THREE.CircleGeometry(0.18, 32);
    const material = this.decalMaterials.get(defect.class_name) || this.decalMaterials.get('Water_Ingress')!;
    
    const decalMesh = new THREE.Mesh(decalGeo, material);
    decalMesh.position.copy(position);

    // Orient decal normal radially outward from tunnel center axis (0, 0, Z)
    const normal = new THREE.Vector3(x, y, 0).normalize();
    decalMesh.lookAt(position.clone().add(normal));

    // 2. Attach Pulsing Warning Sprite ring
    const ringGeo = new THREE.RingGeometry(0.22, 0.28, 32);
    const ringMat = new THREE.MeshBasicMaterial({
      color: defect.severity === 'CRITICAL' ? 0xff0000 : defect.severity === 'HIGH' ? 0xff6600 : 0xffff00,
      side: THREE.DoubleSide,
      transparent: true,
      opacity: 0.9,
    });
    const ringMesh = new THREE.Mesh(ringGeo, ringMat);
    decalMesh.add(ringMesh);

    decalMesh.userData = { defectPayload: defect };
    this.defectGroup.add(decalMesh);

    return decalMesh;
  }

  /**
   * Animate defect warning markers (pulse animation loop).
   */
  public updateAnimations(clockDelta: number): void {
    const time = Date.now() * 0.003;
    this.defectGroup.children.forEach((child) => {
      if (child.children.length > 0) {
        const ringMesh = child.children[0] as THREE.Mesh;
        const scale = 1.0 + 0.15 * Math.sin(time * 2.0);
        ringMesh.scale.set(scale, scale, 1.0);
      }
    });
  }

  /**
   * Clear all rendered defect decals.
   */
  public clearAllDefects(): void {
    while (this.defectGroup.children.length > 0) {
      const obj = this.defectGroup.children[0];
      this.defectGroup.remove(obj);
    }
  }
}
