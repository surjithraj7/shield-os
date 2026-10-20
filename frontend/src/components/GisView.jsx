/**
 * FORGE3D Innovation #5: GIS Integration
 * Leaflet satellite/hybrid map with tunnel alignment, UTM/WGS84 coordinates
 */
import { useEffect, useRef, useState, useCallback } from "react";
import { ENDPOINTS, getJSON } from "../api";
import L from "leaflet";
import "leaflet/dist/leaflet.css";

const DEFAULT_CENTER = [1.3521, 103.8198];
const DEFAULT_ZOOM = 12;

const SATELLITE_URL = "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}";
const LABELS_URL = "https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}";
const ATTRIBUTION = "Tiles &copy; Esri &mdash; Source: Esri, Maxar, Earthstar Geographics";

export default function GisView({ onToast }) {
  const mapRef = useRef(null);
  const mapInstance = useRef(null);
  const layersRef = useRef({ markers: [], polyline: null });
  const [gisData, setGisData] = useState(null);
  const [selectedPoint, setSelectedPoint] = useState(null);

  useEffect(() => {
    if (mapInstance.current) return;

    const map = L.map(mapRef.current, {
      center: DEFAULT_CENTER,
      zoom: DEFAULT_ZOOM,
      zoomControl: true,
    });

    L.tileLayer(SATELLITE_URL, {
      attribution: ATTRIBUTION,
      maxZoom: 19,
    }).addTo(map);

    L.tileLayer(LABELS_URL, {
      attribution: ATTRIBUTION,
      maxZoom: 19,
      pane: "overlayPane",
    }).addTo(map);

    mapInstance.current = map;

    setTimeout(() => map.invalidateSize(), 100);

    return () => {
      map.remove();
      mapInstance.current = null;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    async function loadGIS() {
      try {
        const res = await getJSON("/api/gis/data");
        if (cancelled) return;
        setGisData(res);
      } catch (e) {
        if (onToast) onToast("GIS API OFFLINE", "err");
      }
    }
    loadGIS();
    return () => { cancelled = true; };
  }, [onToast]);

  useEffect(() => {
    const map = mapInstance.current;
    if (!map || !gisData) return;

    const { alignment, points } = gisData;
    const { markers, polyline } = layersRef.current;

    markers.forEach((m) => map.removeLayer(m));
    if (polyline) map.removeLayer(polyline);
    layersRef.current = { markers: [], polyline: null };

    if (!points || points.length === 0) return;

    const latlngs = points.map((p) => [p.wgs84.lat, p.wgs84.lon]);

    const line = L.polyline(latlngs, {
      color: "#FF00FF",
      weight: 3,
      opacity: 0.9,
    }).addTo(map);
    layersRef.current.polyline = line;

    const newMarkers = [];

    points
      .filter((_, i) => i % 5 === 0)
      .forEach((p) => {
        const marker = L.circleMarker([p.wgs84.lat, p.wgs84.lon], {
          radius: 4,
          fillColor: "#00FFFF",
          color: "#fff",
          weight: 1,
          fillOpacity: 1,
        }).addTo(map);
        marker.on("click", () => setSelectedPoint(p));
        newMarkers.push(marker);
      });

    const originMarker = L.circleMarker(
      [alignment.origin_wgs84.lat, alignment.origin_wgs84.lon],
      {
        radius: 7,
        fillColor: "#FF00FF",
        color: "#fff",
        weight: 2,
        fillOpacity: 1,
      }
    ).addTo(map);
    originMarker.bindTooltip("ORIGIN", { permanent: true, direction: "right", offset: [10, 0] });
    newMarkers.push(originMarker);

    layersRef.current.markers = newMarkers;

    const bounds = L.latLngBounds(latlngs);
    bounds.extend([alignment.origin_wgs84.lat, alignment.origin_wgs84.lon]);
    map.fitBounds(bounds, { padding: [60, 60] });
  }, [gisData]);

  const handleSelectPoint = useCallback((p) => {
    setSelectedPoint(p);
    const map = mapInstance.current;
    if (map) {
      map.setView([p.wgs84.lat, p.wgs84.lon], map.getZoom());
    }
  }, []);

  return (
    <div className="geo-layout" style={{ height: "500px" }}>
      <div style={{ flex: 1, display: "flex", flexDirection: "column", height: "100%" }}>
        <div
          ref={mapRef}
          style={{ width: "100%", height: "100%", background: "#0a1628" }}
        />
      </div>
      <div className="twin-panel" style={{ width: "280px" }}>
        <div className="twin-hud">
          <div className="twin-hud-title">GIS COORDINATES</div>
          {gisData && (
            <>
              <div className="twin-hud-row">
                <span>PROJECTION</span>
                <b>UTM {gisData.alignment.origin_utm.zone}{gisData.alignment.origin_utm.letter}</b>
              </div>
              <div className="twin-hud-row">
                <span>ORIGIN LAT</span>
                <b>{gisData.alignment.origin_wgs84.lat.toFixed(4)}°</b>
              </div>
              <div className="twin-hud-row">
                <span>ORIGIN LON</span>
                <b>{gisData.alignment.origin_wgs84.lon.toFixed(4)}°</b>
              </div>
              <div className="twin-hud-row">
                <span>EASTING</span>
                <b>{gisData.alignment.origin_utm.easting_m.toFixed(0)}m</b>
              </div>
              <div className="twin-hud-row">
                <span>NORTHING</span>
                <b>{gisData.alignment.origin_utm.northing_m.toFixed(0)}m</b>
              </div>
              <div className="twin-hud-row">
                <span>AZIMUTH</span>
                <b>{gisData.alignment.azimuth_deg}°</b>
              </div>
              <div className="twin-hud-row">
                <span>DEPTH</span>
                <b>{gisData.alignment.depth_m}m</b>
              </div>
              <div className="twin-hud-row">
                <span>LENGTH</span>
                <b>{gisData.alignment.chainage_end_m}m</b>
              </div>
            </>
          )}
        </div>

        {selectedPoint && (
          <div className="twin-hud">
            <div className="twin-hud-title">SELECTED POINT</div>
            <div className="twin-hud-row"><span>CHAINAGE</span><b>{selectedPoint.chainage_m}m</b></div>
            <div className="twin-hud-row"><span>LAT</span><b>{selectedPoint.wgs84.lat.toFixed(6)}°</b></div>
            <div className="twin-hud-row"><span>LON</span><b>{selectedPoint.wgs84.lon.toFixed(6)}°</b></div>
            <div className="twin-hud-row"><span>EASTING</span><b>{selectedPoint.utm.easting_m.toFixed(1)}m</b></div>
            <div className="twin-hud-row"><span>NORTHING</span><b>{selectedPoint.utm.northing_m.toFixed(1)}m</b></div>
          </div>
        )}

        <div className="twin-hud">
          <div className="twin-hud-title">ALIGNMENT POINTS</div>
          <div style={{ maxHeight: "150px", overflowY: "auto" }}>
            {gisData && gisData.points &&
              gisData.points.filter((_, i) => i % 10 === 0).map((p, i) => (
                <div
                  key={i}
                  className="twin-hud-row"
                  style={{ cursor: "pointer" }}
                  onClick={() => handleSelectPoint(p)}
                >
                  <span>{p.chainage_m}m</span>
                  <b>{p.wgs84.lat.toFixed(3)}°</b>
                </div>
              ))
            }
          </div>
        </div>
      </div>
    </div>
  );
}
