interface Filters {
  score_min: number;
  score_max: number;
  market_status: string;
  sort_by: string;
}

interface Props {
  filters: Filters;
  onChange: (f: Filters) => void;
  onExport: () => void;
  totalCount: number;
}

export default function FilterPanel({ filters, onChange, onExport, totalCount }: Props) {
  const set = (key: keyof Filters, val: unknown) => onChange({ ...filters, [key]: val });

  return (
    <div style={{ display: "flex", gap: 12, alignItems: "center", flexWrap: "wrap", padding: "12px 0" }}>
      <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
        <span style={{ color: "var(--muted)", fontSize: 12, whiteSpace: "nowrap" }}>Min score</span>
        <input
          type="number"
          value={filters.score_min}
          min={0}
          max={100}
          onChange={(e) => set("score_min", Number(e.target.value))}
          style={{ width: 64 }}
        />
      </div>

      <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
        <span style={{ color: "var(--muted)", fontSize: 12, whiteSpace: "nowrap" }}>Market</span>
        <select value={filters.market_status} onChange={(e) => set("market_status", e.target.value)} style={{ width: 130 }}>
          <option value="">All</option>
          <option value="ON_MARKET">On Market</option>
          <option value="OFF_MARKET">Off Market</option>
        </select>
      </div>

      <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
        <span style={{ color: "var(--muted)", fontSize: 12, whiteSpace: "nowrap" }}>Sort by</span>
        <select value={filters.sort_by} onChange={(e) => set("sort_by", e.target.value)} style={{ width: 150 }}>
          <option value="score">Score (High → Low)</option>
          <option value="days_on_market">Days on Market</option>
          <option value="assessed_value">Assessed Value</option>
        </select>
      </div>

      <span style={{ color: "var(--muted)", fontSize: 12, marginLeft: "auto" }}>
        {totalCount.toLocaleString()} properties
      </span>

      <button className="btn-secondary" onClick={onExport} style={{ whiteSpace: "nowrap" }}>
        Export CSV
      </button>
    </div>
  );
}
