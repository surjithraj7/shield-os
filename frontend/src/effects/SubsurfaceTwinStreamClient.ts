/**
 * Subsurface Digital Twin Real-Time Streaming Client & WebGL Render Pipeline
 * =========================================================================
 * Manages WebSocket/gRPC binary buffer streaming from Python backend to WebGL/Three.js frontend.
 * Updates dynamic vertex displacement buffers for 3D geological strata mesh & PINN settlement troughs.
 */

import * as THREE from 'three';

export interface TelemetryStreamPacket {
  ring_number: number;
  chainage_m: number;
  pinn_settlement_grid: number[]; // 1D array of surface settlement values along transverse profile
  stratum_gaussian_splats?: Array<{ x: number; y: number; z: number; density: number; color_hex: string }>;
  agent_status: {
    geotech_risk: string;
    safety_decision: 'APPROVED' | 'VETOED_RETRY' | 'EMERGENCY_HALT';
    tbm_setpoints: { epb_kpa: number; thrust_kn: number; rpm: number };
  };
}

export class SubsurfaceTwinStreamClient {
  private wsUrl: string;
  private ws: WebSocket | null = null;
  private scene: THREE.Scene;
  private settlementSurfaceMesh: THREE.Mesh | null = null;
  private stratumPointCloud: THREE.Points | null = null;
  private onTelemetryCallback: ((data: TelemetryStreamPacket) => void) | null = null;

  constructor(wsUrl: string, scene: THREE.Scene) {
    this.wsUrl = wsUrl;
    this.scene = scene;
  }

  public connect(onTelemetryReceived?: (data: TelemetryStreamPacket) => void): void {
    this.onTelemetryCallback = onTelemetryReceived || null;
    
    try {
      this.ws = new WebSocket(this.wsUrl);
      this.ws.binaryType = 'arraybuffer';

      this.ws.onopen = () => {
        console.log('[SubsurfaceTwinStreamClient] Connected to AI Twin Stream:', this.wsUrl);
      };

      this.ws.onmessage = (event: MessageEvent) => {
        if (typeof event.data === 'string') {
          const packet: TelemetryStreamPacket = JSON.parse(event.data);
          this.handleTelemetryUpdate(packet);
          if (this.onTelemetryCallback) {
            this.onTelemetryCallback(packet);
          }
        } else if (event.data instanceof ArrayBuffer) {
          // Fast binary Float32Array unpack for high-throughput 60FPS settlement grid updates
          const floatArray = new Float32Array(event.data);
          this.updateSettlementMeshGeometry(floatArray);
        }
      };

      this.ws.onerror = (err) => {
        console.warn('[SubsurfaceTwinStreamClient] WebSocket error:', err);
      };

      this.ws.onclose = () => {
        console.log('[SubsurfaceTwinStreamClient] Disconnected. Reconnecting in 3s...');
        setTimeout(() => this.connect(onTelemetryReceived), 3000);
      };
    } catch (e) {
      console.error('[SubsurfaceTwinStreamClient] Init failed:', e);
    }
  }

  /**
   * Initializes the 3D Ground Surface Plane Mesh with dynamic heightfield vertex buffers.
   */
  public initSettlementMesh(gridWidth: number = 40, gridDepth: number = 100, segX: number = 100, segZ: number = 200): THREE.Mesh {
    const geometry = new THREE.PlaneGeometry(gridWidth, gridDepth, segX, segZ);
    geometry.rotateX(-Math.PI / 2); // Orient horizontally at ground surface z=0

    const material = new THREE.MeshStandardMaterial({
      color: 0x334155,
      wireframe: false,
      roughness: 0.6,
      metalness: 0.2,
      side: THREE.DoubleSide,
      flatShading: true,
    });

    this.settlementSurfaceMesh = new THREE.Mesh(geometry, material);
    this.settlementSurfaceMesh.position.set(0, 15.0, 0); // Ground elevation relative to tunnel centerline
    this.scene.add(this.settlementSurfaceMesh);

    return this.settlementSurfaceMesh;
  }

  /**
   * Updates ground surface vertex displacement buffer in real time based on PINN inference stream.
   */
  public updateSettlementMeshGeometry(settlementGridMm: Float32Array): void {
    if (!this.settlementSurfaceMesh) return;

    const geo = this.settlementSurfaceMesh.geometry as THREE.BufferGeometry;
    const posAttr = geo.attributes.position as THREE.BufferAttribute;
    const count = Math.min(posAttr.count, settlementGridMm.length);

    for (let i = 0; i < count; i++) {
      // Displace Y coordinate downward by settlement in meters
      const displacementMeters = settlementGridMm[i] / 1000.0;
      posAttr.setY(i, 15.0 - displacementMeters);
    }

    posAttr.needsUpdate = true;
    geo.computeVertexNormals();
  }

  private handleTelemetryUpdate(packet: TelemetryStreamPacket): void {
    if (packet.pinn_settlement_grid && packet.pinn_settlement_grid.length > 0) {
      this.updateSettlementMeshGeometry(new Float32Array(packet.pinn_settlement_grid));
    }
  }

  public disconnect(): void {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }
}
