import { useEffect, useState, useCallback } from "react";
import { propertiesApi, locationsApi, authApi } from "../api";
import type { PropertySummary, MapPin, Location, User } from "../types";
import PropertyMap from "../components/Map/PropertyMap";
import PropertyList from "../components/PropertyList/PropertyList";
import FilterPanel from "../components/FilterPanel/FilterPanel";
import PropertyDetailPanel from "../components/PropertyDetail/PropertyDetail";
import LocationSearch from "../components/Auth/LocationSearch";
import DataSourceConfig from "../components/DataSourceConfig/DataSourceConfig";

type Tab = "map" | "list" | "sources";

interface Props { user: User; onLogout: () => void; }

export default function Dashboard({ user, onLogout }: Props) {
  const [activeTab, setActiveTab] = useState<Tab>("map");
  const [location, setLocation] = useState<Location | null>(null);
  const [properties, setProperties] = useState<PropertySummary[]>([]);
  const [pins, setPins] = useState<MapPin[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(false);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [filters, setFilters] = useState({ score_min: 0, score_max: 100, market_status: "", sort_by: "score" });

  // Load current location on mount
  useEffect(() => {
    locationsApi.current().then((r) => r.data && setLocation(r.data));
  }, []);

  const loadProperties = useCallback(async () => {
    setLoading(true);
    try {
      const params: Record<string, unknown> = {
        page,
        score_min: filters.score_min,
        score_max: filters.score_max,
        sort_by: filters.sort_by,
        ...(filters.market_status && { market_status: filters.market_status }),
        ...(location?.county && { county: location.county }),
        ...(location?.state_code && { state: location.state_code }),
      };
      const [listRes, pinsRes] = await Promise.all([
        propertiesApi.list(params),
        propertiesApi.mapPins({
          score_min: filters.score_min,
          ...(location?.county && { county: location.county }),
          ...(location?.state_code && { state: location.state_code }),
        }),
      ]);
      setProperties(listRes.data.items);
      setTotal(listRes.data.total);
      setPins(pinsRes.data);
    } finally {
      setLoading(false);
    }
  }, [page, filters, location]);

  useEffect(() => { loadProperties(); }, [loadProperties]);

  const handleLocationSelect = async (loc: Location) => {
    await locationsApi.set(loc);
    setLocation(loc);
    setPage(1);
  };

  const handleLogout = async () => {
    await authApi.logout();
    onLogout();
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100vh", overflow: "hidden" }}>
      {/* Top nav */}
      <header style={{
        display: "flex", alignItems: "center", gap: 12, padding: "10px 16px",
        background: "var(--surface)", borderBottom: "1px solid var(--border)", flexShrink: 0
      }}>
        <span style={{ fontWeight: 700, fontSize: 15, marginRight: 8 }}>🏠 Motivated Seller Finder</span>

        <LocationSearch currentLocation={location} onSelect={handleLocationSelect} />

        <div style={{ display: "flex", gap: 4, marginLeft: 8 }}>
          {(["map", "list", "sources"] as Tab[]).map((t) => (
            <button
              key={t}
              onClick={() => setActiveTab(t)}
              className={activeTab === t ? "btn-primary" : "btn-secondary"}
              style={{ fontSize: 13, padding: "6px 12px" }}
            >
              {t === "map" ? "🗺 Map" : t === "list" ? "📋 List" : "⚙ Sources"}
            </button>
          ))}
        </div>

        <div style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 10 }}>
          {user.is_admin && (
            <a href="/admin" style={{ fontSize: 12, color: "var(--muted)" }}>Admin</a>
          )}
          <span style={{ fontSize: 12, color: "var(--muted)" }}>{user.name}</span>
          <button className="btn-secondary" style={{ fontSize: 12, padding: "5px 10px" }} onClick={handleLogout}>
            Sign Out
          </button>
        </div>
      </header>

      {/* Main content */}
      <div style={{ flex: 1, overflow: "hidden", display: "flex", flexDirection: "column" }}>

        {/* Filter bar */}
        {(activeTab === "map" || activeTab === "list") && (
          <div style={{ padding: "0 16px", borderBottom: "1px solid var(--border)", background: "var(--surface)", flexShrink: 0 }}>
            <FilterPanel
              filters={filters}
              onChange={(f) => { setFilters(f); setPage(1); }}
              onExport={() => propertiesApi.exportCsv({
                score_min: filters.score_min,
                ...(location?.county && { county: location.county }),
                ...(location?.state_code && { state: location.state_code }),
              })}
              totalCount={total}
            />
          </div>
        )}

        <div style={{ flex: 1, overflow: "hidden", display: "flex" }}>
          {activeTab === "map" && (
            <div style={{ flex: 1, position: "relative" }}>
              <PropertyMap
                pins={pins}
                location={location}
                onSelectProperty={setSelectedId}
              />
              {!location && (
                <div style={{
                  position: "absolute", top: "50%", left: "50%", transform: "translate(-50%, -50%)",
                  background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "var(--radius)",
                  padding: "20px 28px", textAlign: "center", pointerEvents: "none"
                }}>
                  <div style={{ fontSize: 24, marginBottom: 8 }}>🔍</div>
                  <div style={{ fontWeight: 600 }}>Search for a location to get started</div>
                  <div style={{ color: "var(--muted)", fontSize: 13, marginTop: 4 }}>Enter a city, county, or zip code above</div>
                </div>
              )}
            </div>
          )}

          {activeTab === "list" && (
            <div style={{ flex: 1, overflowY: "auto", display: "flex", flexDirection: "column" }}>
              <PropertyList
                properties={properties}
                selectedId={selectedId}
                onSelect={setSelectedId}
                loading={loading}
              />
              {total > properties.length && (
                <div style={{ display: "flex", justifyContent: "center", gap: 8, padding: 16 }}>
                  {page > 1 && <button className="btn-secondary" onClick={() => setPage((p) => p - 1)}>← Prev</button>}
                  <span style={{ color: "var(--muted)", fontSize: 13, alignSelf: "center" }}>
                    Page {page} · {total} total
                  </span>
                  {page * 50 < total && <button className="btn-secondary" onClick={() => setPage((p) => p + 1)}>Next →</button>}
                </div>
              )}
            </div>
          )}

          {activeTab === "sources" && (
            <div style={{ flex: 1, overflowY: "auto", padding: 16 }}>
              <h2 style={{ marginBottom: 16, fontSize: 18 }}>Data Sources</h2>
              {!location && (
                <div className="card" style={{ marginBottom: 16, borderLeft: "3px solid var(--yellow)" }}>
                  <p style={{ color: "var(--yellow)", fontSize: 13 }}>⚠ Set a location first so data sources know where to pull data from.</p>
                </div>
              )}
              <DataSourceConfig location={location} />
            </div>
          )}
        </div>
      </div>

      {/* Property detail slide-in */}
      {selectedId && (
        <PropertyDetailPanel
          propertyId={selectedId}
          onClose={() => setSelectedId(null)}
        />
      )}
    </div>
  );
}
