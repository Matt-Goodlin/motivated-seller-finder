import type { PropertySummary } from "../../types";

const fmt = (n: number | null, prefix = "$") =>
  n != null ? `${prefix}${n.toLocaleString()}` : "—";

interface Props {
  properties: PropertySummary[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  loading: boolean;
}

export default function PropertyList({ properties, selectedId, onSelect, loading }: Props) {
  if (loading) {
    return (
      <div style={{ padding: 24, color: "var(--muted)", textAlign: "center" }}>
        Loading properties…
      </div>
    );
  }

  if (properties.length === 0) {
    return (
      <div style={{ padding: 24, color: "var(--muted)", textAlign: "center" }}>
        <p style={{ marginBottom: 8 }}>No properties found.</p>
        <p style={{ fontSize: 12 }}>Set a location and run a data source to get started.</p>
      </div>
    );
  }

  return (
    <div style={{ overflowY: "auto", flex: 1 }}>
      {properties.map((p) => (
        <div
          key={p.id}
          onClick={() => onSelect(p.id)}
          style={{
            padding: "12px 16px",
            borderBottom: "1px solid var(--border)",
            cursor: "pointer",
            background: selectedId === p.id ? "var(--surface2)" : "transparent",
            transition: "background 0.1s",
          }}
          onMouseEnter={(e) => { if (selectedId !== p.id) (e.currentTarget as HTMLDivElement).style.background = "rgba(255,255,255,0.03)"; }}
          onMouseLeave={(e) => { if (selectedId !== p.id) (e.currentTarget as HTMLDivElement).style.background = "transparent"; }}
        >
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 8 }}>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ fontWeight: 600, fontSize: 13, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                {p.address}
              </div>
              <div style={{ color: "var(--muted)", fontSize: 12, marginTop: 2 }}>
                {p.city}, {p.state} {p.zip_code}
              </div>
            </div>
            <div style={{ textAlign: "right", flexShrink: 0 }}>
              <span className={`score-badge score-${p.score_band}`}>
                {Math.round(p.total_score)}
              </span>
            </div>
          </div>

          <div style={{ display: "flex", gap: 8, marginTop: 8, flexWrap: "wrap", alignItems: "center" }}>
            <span className={p.market_status === "ON_MARKET" ? "badge-on-market" : "badge-off-market"}>
              {p.market_status === "ON_MARKET" ? "On Market" : "Off Market"}
            </span>

            {p.days_on_market != null && (
              <span style={{ color: "var(--muted)", fontSize: 11 }}>{p.days_on_market}d on market</span>
            )}

            {p.price_reductions > 0 && (
              <span style={{ color: "var(--orange)", fontSize: 11 }}>↓{p.price_reductions} price drop{p.price_reductions > 1 ? "s" : ""}</span>
            )}

            {p.owner_is_absentee && (
              <span style={{ color: "var(--yellow)", fontSize: 11 }}>Absentee</span>
            )}

            <span style={{ marginLeft: "auto", color: "var(--muted)", fontSize: 11 }}>
              {p.indicator_count} signal{p.indicator_count !== 1 ? "s" : ""}
            </span>
          </div>

          {(p.list_price || p.assessed_value) && (
            <div style={{ marginTop: 6, fontSize: 11, color: "var(--muted)" }}>
              {p.list_price && <span>List: <strong style={{ color: "var(--text)" }}>{fmt(p.list_price)}</strong></span>}
              {p.list_price && p.assessed_value && <span style={{ margin: "0 6px" }}>·</span>}
              {p.assessed_value && <span>Assessed: <strong style={{ color: "var(--text)" }}>{fmt(p.assessed_value)}</strong></span>}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
