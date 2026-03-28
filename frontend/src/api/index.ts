import api from "./client";
import type {
  PropertySummary, PropertyDetail, MapPin,
  User, DataSource, Location, Invite,
} from "../types";

// ─── Auth ─────────────────────────────────────────────────────────────────────
export const authApi = {
  login: (email: string, password: string) =>
    api.post<{ user: User; access_token: string }>("/auth/login", { email, password }),
  logout: () => api.post("/auth/logout"),
  me: () => api.get<User>("/auth/me"),
  validateInvite: (token: string) =>
    api.get<{ valid: boolean; email: string | null }>(`/auth/invite/${token}`),
  register: (data: { invite_token: string; name: string; email: string; password: string }) =>
    api.post<{ user: User; access_token: string }>("/auth/register", data),
};

// ─── Admin ───────────────────────────────────────────────────────────────────
export const adminApi = {
  listUsers: () => api.get<User[]>("/admin/users"),
  deactivateUser: (id: string) => api.patch(`/admin/users/${id}/deactivate`),
  activateUser: (id: string) => api.patch(`/admin/users/${id}/activate`),
  createInvite: (email?: string, expiresDays = 7) =>
    api.post<Invite>("/admin/invites", { email, expires_days: expiresDays }),
  listInvites: () => api.get<Invite[]>("/admin/invites"),
  revokeInvite: (id: string) => api.delete(`/admin/invites/${id}`),
};

// ─── Properties ───────────────────────────────────────────────────────────────
export const propertiesApi = {
  list: (params: Record<string, unknown> = {}) =>
    api.get<{ total: number; page: number; pages: number; items: PropertySummary[] }>("/properties", { params }),
  mapPins: (params: Record<string, unknown> = {}) =>
    api.get<MapPin[]>("/properties/map-pins", { params }),
  get: (id: string) => api.get<PropertyDetail>(`/properties/${id}`),
  exportCsv: (params: Record<string, unknown> = {}) => {
    const qs = new URLSearchParams(params as Record<string, string>).toString();
    window.open(`/api/properties/export/csv?${qs}`, "_blank");
  },
};

// ─── Data Sources ─────────────────────────────────────────────────────────────
export const dataSourcesApi = {
  list: () => api.get<DataSource[]>("/data-sources"),
  update: (name: string, data: { enabled?: boolean; api_key?: string }) =>
    api.put<DataSource>(`/data-sources/${name}`, data),
  run: (name: string, county: string, state: string) =>
    api.post(`/data-sources/${name}/run`, null, { params: { county, state } }),
  runs: (name: string) => api.get(`/data-sources/${name}/runs`),
};

// ─── Locations ───────────────────────────────────────────────────────────────
export const locationsApi = {
  search: (q: string) => api.get<Location[]>("/locations/search", { params: { q } }),
  set: (location: Location) => api.post<Location>("/locations/set", location),
  current: () => api.get<Location | null>("/locations/current"),
};
