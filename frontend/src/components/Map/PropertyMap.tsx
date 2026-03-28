import { MapContainer, TileLayer, CircleMarker, Popup, useMap } from "react-leaflet";
import type { MapPin, Location } from "../../types";

const BAND_COLORS: Record<string, string> = {
  HIGH: "#ef4444",
  MODERATE_HIGH: "#f97316",
  MODERATE: "#eab308",
  LOW: "#22c55e",
};

interface Props {
  pins: MapPin[];
  location: Location | null;
  onSelectProperty: (id: string) => void;
}

function FlyTo({ location }: { location: Location | null }) {
  const map = useMap();
  if (location) {
    map.flyTo([location.latitude, location.longitude], 12, { animate: true, duration: 1.2 });
  }
  return null;
}

export default function PropertyMap({ pins, location, onSelectProperty }: Props) {
  const center: [number, number] = location
    ? [location.latitude, location.longitude]
    : [39.5, -98.35]; // center of US

  return (
    <MapContainer
      center={center}
      zoom={location ? 12 : 4}
      style={{ width: "100%", height: "100%", minHeight: 400 }}
    >
      <TileLayer
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        attribution='&copy; <a href="https://openstreetmap.org">OpenStreetMap</a>'
      />
      <FlyTo location={location} />
      {pins.map((pin) => (
        <CircleMarker
          key={pin.id}
          center={[pin.lat, pin.lng]}
          radius={pin.score >= 60 ? 10 : 7}
          pathOptions={{
            fillColor: BAND_COLORS[pin.score_band] || "#8b90b0",
            color: "#fff",
            weight: 1.5,
            fillOpacity: 0.85,
          }}
          eventHandlers={{ click: () => onSelectProperty(pin.id) }}
        >
          <Popup>
            <div style={{ minWidth: 160 }}>
              <strong style={{ display: "block", marginBottom: 4 }}>{pin.address}</strong>
              <span>Score: <strong>{Math.round(pin.score)}</strong></span>
              <br />
              <span>{pin.market_status.replace("_", " ")}</span>
              <br />
              <button
                onClick={() => onSelectProperty(pin.id)}
                style={{ marginTop: 8, padding: "4px 10px", background: "#5c6ef8", color: "#fff", border: "none", borderRadius: 4, cursor: "pointer" }}
              >
                View Details
              </button>
            </div>
          </Popup>
        </CircleMarker>
      ))}
    </MapContainer>
  );
}
