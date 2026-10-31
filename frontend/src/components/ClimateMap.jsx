
import { MapContainer, TileLayer, CircleMarker, Popup } from "react-leaflet";
import "leaflet/dist/leaflet.css";
import "./ClimateMap.css";

export default function ClimateMap() {
  const pune = [18.5204, 73.8567];

  return (
    <div className="climate-map">
      <div className="climate-map__badge">
        <span className="climate-map__pulse" />
        GEOGRAPHIC OVERVIEW
      </div>

      <MapContainer
        center={pune}
        zoom={11}
        scrollWheelZoom
        className="climate-map__canvas"
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
        />

        <CircleMarker
          center={pune}
          radius={10}
          pathOptions={{
            color: "#b8f3d2",
            fillColor: "#35d399",
            fillOpacity: 0.95,
            weight: 3,
          }}
        >
          <Popup>
            <strong>Pune</strong>
            <br />
            Geographic reference location
          </Popup>
        </CircleMarker>
      </MapContainer>

      <div className="climate-map__location">
        <span>REFERENCE LOCATION</span>
        <strong>Pune, Maharashtra</strong>
        <small>18.5204° N · 73.8567° E</small>
      </div>
    </div>
  );
}
