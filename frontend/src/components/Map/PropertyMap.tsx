import { MapContainer, TileLayer, CircleMarker, Popup } from "react-leaflet";
import type { MapPin } from "../../types";

const BAND_COLORS: Record<string, string> = {
  HIGH: "#ef4444",
  MODERATE_HIGH: "#f97316",
  MODERATE: "#eab308",
  LOW: "#22c55e",
};

interface Props {
  pins: MapPin[];
  onSelectProperty: (id: string) => void;
}

export default function PropertyMap({ pins, onSelectProperty }: Props) {
  const center: [number, number] = [40.4406, -79.9959]; // Pittsburgh / western PA

  return (
    <MapContainer
      center={center}
      zoom={11}
      style={{ width: "100%", height: "100%", minHeight: 400 }}
    >
      <TileLayer
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        attribution='&copy; <a href="https://openstreetmap.org">OpenStreetMap</a>'
      />
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
