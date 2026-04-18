import { useMemo } from "react";
import world from "@svg-maps/world";
import { svgPathBbox } from "svg-path-bbox";

const LOCATION_BY_CODE = new Map(world.locations.map((location) => [location.id.toUpperCase(), location]));

function formatCoordinate(value, axis) {
  const absolute = Math.abs(Number(value || 0)).toFixed(2);
  if (axis === "lat") {
    return `${absolute}°${value >= 0 ? "N" : "S"}`;
  }
  return `${absolute}°${value >= 0 ? "E" : "W"}`;
}

export default function GeoCountryPreview({ countryCode, latitude, longitude, rank, score }) {
  const location = LOCATION_BY_CODE.get(String(countryCode || "").toUpperCase()) || null;

  const viewBox = useMemo(() => {
    if (!location?.path) {
      return "0 0 1010 666";
    }
    const [x1, y1, x2, y2] = svgPathBbox(location.path);
    const padding = 12;
    const width = Math.max(24, x2 - x1 + padding * 2);
    const height = Math.max(24, y2 - y1 + padding * 2);
    return `${x1 - padding} ${y1 - padding} ${width} ${height}`;
  }, [location?.path]);

  if (!location) {
    return (
      <article className="geo-country-card unavailable">
        <header>
          <span>Country #{rank}</span>
          <strong>{countryCode || "Unknown"}</strong>
        </header>
        <p>Country shape not available in map dataset.</p>
      </article>
    );
  }

  return (
    <article className="geo-country-card">
      <header>
        <span>Country #{rank}</span>
        <strong>{location.name}</strong>
      </header>

      <svg viewBox={viewBox} className="geo-country-shape" aria-label={`${location.name} country map`}>
        <path d={location.path} className="geo-country-path" />
      </svg>

      <div className="geo-country-meta">
        <p>{countryCode}</p>
        <p>Lat {formatCoordinate(latitude, "lat")}</p>
        <p>Lon {formatCoordinate(longitude, "lon")}</p>
        <p>Score {score}/100</p>
      </div>
    </article>
  );
}