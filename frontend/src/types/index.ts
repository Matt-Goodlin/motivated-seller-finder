export type MarketStatus = "ON_MARKET" | "OFF_MARKET" | "UNKNOWN";
export type ScoreBand = "HIGH" | "MODERATE_HIGH" | "MODERATE" | "LOW";

export interface PropertySummary {
  id: string;
  address: string;
  city: string;
  state: string;
  zip_code: string | null;
  county: string | null;
  latitude: number | null;
  longitude: number | null;
  owner_name: string | null;
  owner_is_absentee: boolean;
  assessed_value: number | null;
  market_value_estimate: number | null;
  list_price: number | null;
  market_status: MarketStatus;
  days_on_market: number | null;
  price_reductions: number;
  total_score: number;
  score_band: ScoreBand;
  indicator_count: number;
  zillow_url: string | null;
  updated_at: string;
}

export interface Indicator {
  id: string;
  indicator_type: string;
  category: string;
  confidence: number;
  source_name: string;
  detected_at: string;
  notes: string | null;
  weight: number;
}

export interface Score {
  id: string;
  total_score: number;
  financial_score: number;
  legal_score: number;
  landlord_score: number;
  market_score: number;
  condition_score: number;
  indicator_count: number;
  last_calculated_at: string;
}

export interface PropertyDetail extends PropertySummary {
  parcel_id: string | null;
  owner_mailing_address: string | null;
  owner_phone: string | null;
  owner_email: string | null;
  last_sale_price: number | null;
  last_sale_date: string | null;
  years_owned: number | null;
  mortgage_balance: number | null;
  equity_estimate: number | null;
  property_type: string | null;
  year_built: number | null;
  sq_ft: number | null;
  lot_size_sqft: number | null;
  bedrooms: number | null;
  bathrooms: number | null;
  mls_id: string | null;
  list_date: string | null;
  data_sources: string;
  score: Score | null;
  indicators: Indicator[];
  street_view: { available: boolean; url: string | null; source: string | null } | null;
}

export interface MapPin {
  id: string;
  lat: number;
  lng: number;
  address: string;
  market_status: MarketStatus;
  score: number;
  score_band: ScoreBand;
}

export interface User {
  id: string;
  email: string;
  name: string;
  is_admin: boolean;
  is_active: boolean;
  created_at: string;
  last_login_at: string | null;
}

export interface DataSource {
  source_name: string;
  display_name: string;
  description: string;
  is_paid: boolean;
  enabled: boolean;
  is_configured: boolean;
  last_run_at: string | null;
}

export interface Location {
  display_name: string;
  city: string | null;
  county: string | null;
  state: string | null;
  state_code: string | null;
  latitude: number;
  longitude: number;
  bbox: [number, number, number, number];
}

export interface Invite {
  id: string;
  token: string;
  email: string | null;
  expires_at: string;
  is_active: boolean;
  used_at: string | null;
  invite_url: string;
}
