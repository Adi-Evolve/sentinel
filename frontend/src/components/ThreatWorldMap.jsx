import { useEffect, useMemo, useState } from "react";
import world from "@svg-maps/world";
import { svgPathBbox } from "svg-path-bbox";

const CITY_BY_COUNTRY = {
  US: "Washington, D.C.",
  CA: "Ottawa",
  GB: "London",
  DE: "Berlin",
  FR: "Paris",
  NL: "Amsterdam",
  RU: "Moscow",
  IN: "New Delhi",
  CN: "Beijing",
  JP: "Tokyo",
  SG: "Singapore",
  AU: "Canberra",
  ZA: "Pretoria",
  BR: "Brasilia",
  TR: "Ankara",
  UA: "Kyiv",
  PK: "Islamabad",
  NG: "Abuja",
  MX: "Mexico City",
  CH: "Bern",
  ES: "Madrid",
  IT: "Rome",
  KR: "Seoul",
  ID: "Jakarta",
};

const LOCATION_BY_CODE = new Map(world.locations.map((location) => [location.id.toUpperCase(), location]));

function countryNameFor(code) {
  if (!code) {
    return "Unknown";
  }
  try {
    const formatter = new Intl.DisplayNames(["en"], { type: "region" });
    return formatter.of(code) || code;
  } catch {
    return code;
  }
}

export default function ThreatWorldMap({ anomalies }) {
  const [zoomLevel, setZoomLevel] = useState(1);
  const [isExpanded, setIsExpanded] = useState(false);
  const [panOffset, setPanOffset] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const [dragOrigin, setDragOrigin] = useState(null);

  const locationCenters = useMemo(() => {
    const centers = new Map();
    world.locations.forEach((location) => {
      const [x1, y1, x2, y2] = svgPathBbox(location.path);
      centers.set(location.id.toUpperCase(), {
        x: (x1 + x2) / 2,
        y: (y1 + y2) / 2,
      });
    });
    return centers;
  }, []);

  const rawPoints = anomalies
    .map((anomaly) => {
      const code = String(anomaly.country_code || "").toUpperCase();
      const location = LOCATION_BY_CODE.get(code);
      const center = locationCenters.get(code);

      if (!location || !center) {
        return null;
      }

      return {
        country_code: code,
        country_name: countryNameFor(code),
        city_name: anomaly.city || anomaly.city_name || CITY_BY_COUNTRY[code] || "City Unavailable",
        severity: anomaly.composite_score || 0,
        x: center.x,
        y: center.y,
      };
    })
    .filter(Boolean);

  const mergedByCountry = new Map();
  rawPoints.forEach((point) => {
    const existing = mergedByCountry.get(point.country_code);
    if (!existing || existing.severity < point.severity) {
      mergedByCountry.set(point.country_code, point);
    }
  });

  const points = Array.from(mergedByCountry.values()).sort((left, right) => Number(right.severity) - Number(left.severity));
  const hotspot = points[0] || null;
  const pointByCountry = new Map(points.map((point) => [point.country_code, point]));
  const viewBox = world.viewBox || "0 0 1000 500";
  const [vbX, vbY, vbW, vbH] = String(viewBox)
    .trim()
    .split(/\s+/)
    .map((value) => Number(value));
  const focusX = hotspot?.x || vbX + vbW / 2;
  const focusY = hotspot?.y || vbY + vbH / 2;
  const showDeepLabels = zoomLevel >= 1.8;
  const visualScale = 1 / zoomLevel;

  useEffect(() => {
    if (zoomLevel <= 1) {
      setPanOffset({ x: 0, y: 0 });
      setIsDragging(false);
      setDragOrigin(null);
    }
  }, [zoomLevel]);

  function clampPan(candidate, zoom) {
    const maxX = Math.max(0, 240 * (zoom - 1));
    const maxY = Math.max(0, 150 * (zoom - 1));
    return {
      x: Math.max(-maxX, Math.min(maxX, candidate.x)),
      y: Math.max(-maxY, Math.min(maxY, candidate.y)),
    };
  }

  function startPan(event) {
    if (zoomLevel <= 1) {
      return;
    }
    if (event.target?.closest?.(".map-control-panel")) {
      return;
    }
    setIsDragging(true);
    setDragOrigin({
      startX: event.clientX,
      startY: event.clientY,
      originPanX: panOffset.x,
      originPanY: panOffset.y,
    });
    event.currentTarget.setPointerCapture?.(event.pointerId);
  }

  function movePan(event) {
    if (!isDragging || !dragOrigin) {
      return;
    }
    const deltaX = event.clientX - dragOrigin.startX;
    const deltaY = event.clientY - dragOrigin.startY;
    setPanOffset(
      clampPan(
        {
          x: dragOrigin.originPanX + deltaX,
          y: dragOrigin.originPanY + deltaY,
        },
        zoomLevel
      )
    );
  }

  function endPan(event) {
    if (!isDragging) {
      return;
    }
    setIsDragging(false);
    setDragOrigin(null);
    event.currentTarget.releasePointerCapture?.(event.pointerId);
  }

  const pathLinks = hotspot
    ? points.slice(1, 6).map((point, index) => {
        const startX = hotspot.x;
        const startY = hotspot.y;
        const endX = point.x;
        const endY = point.y;
        const curveX = (startX + endX) / 2;
        const arcHeight = 42 + Math.abs(endX - startX) * 0.08;
        const curveY = Math.max(45, Math.min(startY, endY) - arcHeight);
        return {
          id: `${hotspot.country_code}-${point.country_code}-${index}`,
          path: `M ${startX} ${startY} Q ${curveX} ${curveY} ${endX} ${endY}`,
        };
      })
    : [];

  return (
    <section className="viz-card world-card">
      <div className="viz-head">
        <h3>Global Threat Surface</h3>
        <p>
          AI-flagged anomalies by geolocated country
          {points.length ? ` (${points.length} mapped)` : ""}
        </p>
      </div>

      <div className="world-map-meta">
        <span>Hotspots {points.length}</span>
        <span>Highest {hotspot ? `${hotspot.country_name} ${Math.round(hotspot.severity)}/100` : "n/a"}</span>
        <span>Visible Routes {pathLinks.length}</span>
      </div>

      <div
        className={`world-map map-interactive-surface ${isExpanded ? "is-expanded" : ""} ${isDragging ? "is-dragging" : ""}`}
        onPointerDown={startPan}
        onPointerMove={movePan}
        onPointerUp={endPan}
        onPointerCancel={endPan}
      >
        <div className="map-control-panel" role="group" aria-label="Map controls">
          <button
            type="button"
            className="map-control-button"
            onClick={() => setZoomLevel((previous) => Math.min(4, Number((previous + 0.25).toFixed(2))))}
            aria-label="Zoom in map"
          >
            +
          </button>
          <button
            type="button"
            className="map-control-button"
            onClick={() => setZoomLevel((previous) => Math.max(1, Number((previous - 0.25).toFixed(2))))}
            aria-label="Zoom out map"
          >
            -
          </button>
          <button
            type="button"
            className="map-control-button"
            onClick={() => {
              setZoomLevel(1);
              setPanOffset({ x: 0, y: 0 });
            }}
            aria-label="Reset map zoom"
          >
            Reset
          </button>
          <button
            type="button"
            className="map-control-button"
            onClick={() => setIsExpanded((previous) => !previous)}
            aria-label={isExpanded ? "Minimize map" : "Maximize map"}
          >
            {isExpanded ? "Min" : "Max"}
          </button>
          <span className="map-control-value">{zoomLevel.toFixed(2)}x</span>
        </div>

        <svg viewBox={viewBox} aria-label="World threat map">
          <g
            className="world-viewport"
            style={{
              transformOrigin: `${focusX}px ${focusY}px`,
              transform: `translate(${panOffset.x}px, ${panOffset.y}px) scale(${zoomLevel})`,
            }}
          >
          <defs>
            <linearGradient id="worldRouteStroke" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stopColor="rgba(116, 222, 239, 0.2)" />
              <stop offset="50%" stopColor="rgba(255, 186, 99, 0.74)" />
              <stop offset="100%" stopColor="rgba(246, 88, 88, 0.92)" />
            </linearGradient>
          </defs>

          <rect x="0" y="0" width="1000" height="500" rx="22" className="world-bg" />

          {[80, 160, 240, 320, 400].map((row) => (
            <line key={`world-grid-row-${row}`} x1="0" y1={row} x2="1000" y2={row} className="world-grid" />
          ))}
          {[125, 250, 375, 500, 625, 750, 875].map((column) => (
            <line key={`world-grid-col-${column}`} x1={column} y1="0" x2={column} y2="500" className="world-grid" />
          ))}

          {world.locations.map((location) => {
            const code = location.id.toUpperCase();
            const highlighted = pointByCountry.get(code);

            if (!highlighted) {
              return <path key={`world-country-${code}`} className="world-country" d={location.path} />;
            }

            const intensity = Math.max(0.35, Math.min(1, Number(highlighted.severity || 0) / 100));
            return (
              <path
                key={`world-country-${code}`}
                className="world-country hot"
                d={location.path}
                style={{ "--world-hot-intensity": intensity }}
              />
            );
          })}

          {pathLinks.map((link, index) => (
            <path key={link.id} d={link.path} className="world-route" style={{ animationDelay: `${index * 0.25}s` }} />
          ))}

          {points.map((point, index) => {
            const radius = 6 + (point.severity / 100) * 13;
            return (
              <g key={`${point.country_code}-${index}`}>
                <title>{`${point.country_name} - ${point.city_name}`}</title>
                <circle cx={point.x} cy={point.y} r={Math.max(3, radius * visualScale)} className="threat-pulse" />
                <circle cx={point.x} cy={point.y} r={Math.max(2, radius * 0.42 * visualScale)} className="threat-core" />
                {index < 3 || (showDeepLabels && index < 5) ? (
                  <text
                    x={point.x + 9}
                    y={point.y - 9}
                    className="world-label"
                    style={{ fontSize: `${Math.max(5.5, 10 * visualScale)}px`, strokeWidth: `${Math.max(1.2, 3 * visualScale)}px` }}
                  >
                    {showDeepLabels ? `${point.country_name} - ${point.city_name}` : point.city_name}
                  </text>
                ) : null}
              </g>
            );
          })}
          </g>
        </svg>
      </div>

      <div className="world-focus-row">
        {points.slice(0, 5).map((point, index) => (
          <span key={`${point.country_code}-legend`} className="world-focus-pill">
            #{index + 1} {point.country_name} - {point.city_name} ({Math.round(point.severity)})
          </span>
        ))}
      </div>
    </section>
  );
}
