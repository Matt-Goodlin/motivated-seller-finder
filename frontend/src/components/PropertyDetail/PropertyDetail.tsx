import { useEffect, useState } from "react";
import { propertiesApi } from "../../api";
import type { PropertyDetail as PD } from "../../types";
import ScoreBreakdown from "../ScoreBreakdown/ScoreBreakdown";

const INDICATOR_LABELS: Record<string, string> = {
  pre_foreclosure: "Pre-Foreclosure / NOD",
  tax_delinquent: "Tax Delinquency",
  active_lien: "Active Lien",
  bankruptcy_filing: "Bankruptcy Filing",
  utility_shutoff: "Utility Shutoff",
  low_equity: "Low / Negative Equity",
  probate_filing: "Probate / Estate Filing",
  divorce_filing: "Divorce Filing",
  eviction_filing: "Eviction Filing",
  job_relocation: "Job Relocation Signal",
  code_violation: "Code Violation",
  failed_inspection: "Failed Inspection",
  permit_incomplete: "Permit Filed, Not Completed",
  low_rent_vs_market: "Below-Market Rent",
  landlord_multi_eviction: "Multiple Evictions (Landlord)",
  expired_listing: "Expired MLS Listing",
  long_dom: "Long Days on Market",
  price_drops: "Multiple Price Reductions",
  usps_vacancy: "USPS Vacancy Flag",
  no_mail_activity: "No Mail Activity",
  street_view_neglect: "Street View: Deferred Maintenance",
  long_ownership_no_improvements: "Long-Term Ownership, No Improvements",
  absentee_owner: "Absentee / Out-of-State Owner",
};

const CATEGORY_COLORS: Record<string, string> = {
  FINANCIAL: "var(--red)",
  LEGAL_LIFE_EVENT: "var(--orange)",
  LANDLORD_PAIN: "var(--yellow)",
  MARKET_SIGNAL: "var(--primary)",
  PROPERTY_CONDITION: "var(--green)",
};

const fmt = (n: number | null | undefined, prefix = "$") =>
  n != null ? `${prefix}${n.toLocaleString()}` : "—";

interface Props {
  propertyId: string;
  onClose: () => void;
}

export default function PropertyDetailPanel({ propertyId, onClose }: Props) {
  const [prop, setProp] = useState<PD | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    propertiesApi.get(propertyId)
      .then((r) => setProp(r.data))
      .finally(() => setLoading(false));
  }, [propertyId]);

  return (
    <div style={{
      position: "fixed", right: 0, top: 0, bottom: 0, width: 440,
      background: "var(--surface)", borderLeft: "1px solid var(--border)",
      overflowY: "auto", zIndex: 1000, padding: 20,
      boxShadow: "-4px 0 24px rgba(0,0,0,0.4)"
    }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
        <h2 style={{ fontSize: 16, fontWeight: 700 }}>Property Details</h2>
        <button onClick={onClose} style={{ background: "none", fontSize: 18, color: "var(--muted)", padding: 4 }}>✕</button>
      </div>

      {loading && <div style={{ color: "var(--muted)", textAlign: "center", paddingTop: 40 }}>Loading…</div>}

      {prop && (
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          {/* Header */}
          <div className="card">
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
              <div>
                <h3 style={{ fontWeight: 700, marginBottom: 4 }}>{prop.address}</h3>
                <div style={{ color: "var(--muted)", fontSize: 13 }}>{prop.city}, {prop.state} {prop.zip_code}</div>
              </div>
              <span className={`score-badge score-${prop.score_band}`} style={{ fontSize: 18, padding: "6px 14px" }}>
                {Math.round(prop.total_score)}
              </span>
            </div>
            <div style={{ display: "flex", gap: 8, marginTop: 10, flexWrap: "wrap" }}>
              <span className={prop.market_status === "ON_MARKET" ? "badge-on-market" : "badge-off-market"}>
                {prop.market_status === "ON_MARKET" ? "On Market" : "Off Market"}
              </span>
              {prop.owner_is_absentee && <span style={{ background: "rgba(234,179,8,0.15)", color: "var(--yellow)", borderRadius: 4, padding: "2px 8px", fontSize: 12 }}>Absentee Owner</span>}
              {prop.zillow_url && (
                <a href={prop.zillow_url} target="_blank" rel="noreferrer" style={{ fontSize: 12, padding: "2px 8px", background: "rgba(92,110,248,0.1)", borderRadius: 4 }}>
                  View on Zillow ↗
                </a>
              )}
            </div>
          </div>

          {/* Score Breakdown */}
          {prop.score && (
            <div className="card">
              <h4 style={{ marginBottom: 12, fontSize: 14 }}>Motivation Score Breakdown</h4>
              <ScoreBreakdown score={prop.score} />
            </div>
          )}

          {/* Indicators */}
          {prop.indicators.length > 0 && (
            <div className="card">
              <h4 style={{ marginBottom: 12, fontSize: 14 }}>Signals Detected ({prop.indicators.length})</h4>
              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                {[...prop.indicators]
                  .sort((a, b) => b.weight * b.confidence - a.weight * a.confidence)
                  .map((ind) => (
                    <div key={ind.id} style={{ padding: "10px 12px", background: "var(--surface2)", borderRadius: "var(--radius)", borderLeft: `3px solid ${CATEGORY_COLORS[ind.category] || "var(--border)"}` }}>
                      <div style={{ display: "flex", justifyContent: "space-between" }}>
                        <span style={{ fontWeight: 600, fontSize: 13 }}>{INDICATOR_LABELS[ind.indicator_type] || ind.indicator_type}</span>
                        <span style={{ color: "var(--muted)", fontSize: 11 }}>Weight: {ind.weight} × {Math.round(ind.confidence * 100)}%</span>
                      </div>
                      {ind.notes && <div style={{ color: "var(--muted)", fontSize: 12, marginTop: 4 }}>{ind.notes}</div>}
                      <div style={{ fontSize: 11, color: "var(--muted)", marginTop: 4 }}>Source: {ind.source_name}</div>
                    </div>
                  ))}
              </div>
            </div>
          )}

          {/* Owner Info */}
          <div className="card">
            <h4 style={{ marginBottom: 12, fontSize: 14 }}>Owner Information</h4>
            <table style={{ width: "100%", fontSize: 13, borderCollapse: "collapse" }}>
              <tbody>
                {[
                  ["Owner", prop.owner_name],
                  ["Mailing Address", prop.owner_mailing_address],
                  ["Phone", prop.owner_phone],
                  ["Email", prop.owner_email],
                  ["Years Owned", prop.years_owned != null ? `~${Math.round(prop.years_owned)} years` : null],
                ].map(([label, value]) => value && (
                  <tr key={label as string}>
                    <td style={{ color: "var(--muted)", paddingBottom: 8, paddingRight: 12, whiteSpace: "nowrap" }}>{label}</td>
                    <td style={{ paddingBottom: 8 }}>{value as string}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Financial */}
          <div className="card">
            <h4 style={{ marginBottom: 12, fontSize: 14 }}>Financials</h4>
            <table style={{ width: "100%", fontSize: 13, borderCollapse: "collapse" }}>
              <tbody>
                {[
                  ["Assessed Value", fmt(prop.assessed_value)],
                  ["List Price", fmt(prop.list_price)],
                  ["Last Sale Price", fmt(prop.last_sale_price)],
                  ["Last Sale Date", prop.last_sale_date],
                  ["Estimated Equity", fmt(prop.equity_estimate)],
                  ["Days on Market", prop.days_on_market != null ? `${prop.days_on_market} days` : null],
                  ["Price Reductions", prop.price_reductions > 0 ? `${prop.price_reductions}` : null],
                ].map(([label, value]) => value && (
                  <tr key={label as string}>
                    <td style={{ color: "var(--muted)", paddingBottom: 8, paddingRight: 12 }}>{label}</td>
                    <td style={{ paddingBottom: 8 }}>{value as string}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Property Details */}
          <div className="card">
            <h4 style={{ marginBottom: 12, fontSize: 14 }}>Property Details</h4>
            <table style={{ width: "100%", fontSize: 13, borderCollapse: "collapse" }}>
              <tbody>
                {[
                  ["Type", prop.property_type],
                  ["Year Built", prop.year_built],
                  ["Sq Ft", prop.sq_ft?.toLocaleString()],
                  ["Lot Size", prop.lot_size_sqft?.toLocaleString() ? `${prop.lot_size_sqft?.toLocaleString()} sqft` : null],
                  ["Beds/Baths", prop.bedrooms != null ? `${prop.bedrooms} bed / ${prop.bathrooms} bath` : null],
                  ["Parcel ID", prop.parcel_id],
                ].map(([label, value]) => value && (
                  <tr key={label as string}>
                    <td style={{ color: "var(--muted)", paddingBottom: 8, paddingRight: 12 }}>{label}</td>
                    <td style={{ paddingBottom: 8 }}>{value}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Street View */}
          {prop.street_view?.available && prop.street_view.url && (
            <div className="card">
              <h4 style={{ marginBottom: 12, fontSize: 14 }}>Street View</h4>
              <img
                src={prop.street_view.url}
                alt="Street view"
                style={{ width: "100%", borderRadius: "var(--radius)", display: "block" }}
              />
              <div style={{ fontSize: 11, color: "var(--muted)", marginTop: 6 }}>Source: {prop.street_view.source}</div>
            </div>
          )}

          <div style={{ color: "var(--muted)", fontSize: 11, textAlign: "center" }}>
            Data sources: {prop.data_sources} · Updated {new Date(prop.updated_at).toLocaleDateString()}
          </div>
        </div>
      )}
    </div>
  );
}
