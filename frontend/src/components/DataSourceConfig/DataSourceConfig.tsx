import { useEffect, useState } from "react";
import { dataSourcesApi } from "../../api";
import type { DataSource, Location } from "../../types";

interface Props { location: Location | null; }

export default function DataSourceConfig({ location }: Props) {
  const [sources, setSources] = useState<DataSource[]>([]);
  const [apiKeys, setApiKeys] = useState<Record<string, string>>({});
  const [running, setRunning] = useState<Record<string, boolean>>({});
  const [message, setMessage] = useState("");

  useEffect(() => {
    dataSourcesApi.list().then((r) => setSources(r.data));
  }, []);

  const toggle = async (name: string, enabled: boolean) => {
    await dataSourcesApi.update(name, { enabled });
    setSources((s) => s.map((src) => src.source_name === name ? { ...src, enabled } : src));
  };

  const saveKey = async (name: string) => {
    const key = apiKeys[name];
    if (!key) return;
    await dataSourcesApi.update(name, { api_key: key, enabled: true });
    setSources((s) => s.map((src) => src.source_name === name ? { ...src, enabled: true, is_configured: true } : src));
    setApiKeys((k) => { const c = { ...k }; delete c[name]; return c; });
    setMessage(`API key saved for ${name}`);
    setTimeout(() => setMessage(""), 3000);
  };

  const runSource = async (name: string) => {
    if (!location) { setMessage("Set a location first."); setTimeout(() => setMessage(""), 3000); return; }
    setRunning((r) => ({ ...r, [name]: true }));
    try {
      await dataSourcesApi.run(name, location.county || location.city || "", location.state_code || "");
      setMessage(`${name} data fetch started!`);
    } catch {
      setMessage(`Failed to start ${name}`);
    } finally {
      setRunning((r) => ({ ...r, [name]: false }));
      setTimeout(() => setMessage(""), 4000);
    }
  };

  const free = sources.filter((s) => !s.is_paid);
  const paid = sources.filter((s) => s.is_paid);

  const SourceRow = ({ src }: { src: DataSource }) => (
    <div style={{ padding: "14px 16px", borderBottom: "1px solid var(--border)" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 8 }}>
        <div style={{ flex: 1 }}>
          <div style={{ fontWeight: 600, fontSize: 13 }}>
            {src.display_name}
            {src.is_configured && src.enabled && (
              <span style={{ marginLeft: 8, fontSize: 11, color: "var(--green)" }}>● Active</span>
            )}
          </div>
          <div style={{ color: "var(--muted)", fontSize: 12, marginTop: 2 }}>{src.description}</div>
          {src.last_run_at && (
            <div style={{ color: "var(--muted)", fontSize: 11, marginTop: 4 }}>
              Last run: {new Date(src.last_run_at).toLocaleString()}
            </div>
          )}
        </div>
        <div style={{ display: "flex", gap: 8, flexShrink: 0, alignItems: "center" }}>
          <label style={{ display: "flex", alignItems: "center", gap: 6, cursor: "pointer", fontSize: 13 }}>
            <input
              type="checkbox"
              checked={src.enabled}
              onChange={(e) => toggle(src.source_name, e.target.checked)}
              style={{ width: "auto" }}
            />
            Enabled
          </label>
          {src.is_configured && src.enabled && (
            <button
              className="btn-secondary"
              style={{ fontSize: 12, padding: "4px 10px" }}
              disabled={running[src.source_name]}
              onClick={() => runSource(src.source_name)}
            >
              {running[src.source_name] ? "Running…" : "Run Now"}
            </button>
          )}
        </div>
      </div>

      {src.is_paid && !src.is_configured && (
        <div style={{ marginTop: 10, display: "flex", gap: 8 }}>
          <input
            type="password"
            placeholder="Paste API key…"
            value={apiKeys[src.source_name] || ""}
            onChange={(e) => setApiKeys((k) => ({ ...k, [src.source_name]: e.target.value }))}
            style={{ flex: 1 }}
          />
          <button
            className="btn-primary"
            style={{ fontSize: 12, padding: "6px 12px", whiteSpace: "nowrap" }}
            onClick={() => saveKey(src.source_name)}
          >
            Save Key
          </button>
        </div>
      )}
    </div>
  );

  return (
    <div>
      {message && (
        <div style={{ padding: "10px 14px", marginBottom: 12, background: "rgba(92,110,248,0.15)", borderRadius: "var(--radius)", fontSize: 13 }}>
          {message}
        </div>
      )}

      <div className="card" style={{ padding: 0, overflow: "hidden" }}>
        <div style={{ padding: "12px 16px", background: "var(--surface2)", borderBottom: "1px solid var(--border)" }}>
          <h3 style={{ fontSize: 14, fontWeight: 700 }}>Free Data Sources</h3>
        </div>
        {free.map((src) => <SourceRow key={src.source_name} src={src} />)}
      </div>

      <div className="card" style={{ padding: 0, overflow: "hidden", marginTop: 16 }}>
        <div style={{ padding: "12px 16px", background: "var(--surface2)", borderBottom: "1px solid var(--border)" }}>
          <h3 style={{ fontSize: 14, fontWeight: 700 }}>Paid Data Sources</h3>
          <p style={{ color: "var(--muted)", fontSize: 12, marginTop: 4 }}>These sources require an API subscription but provide more comprehensive data.</p>
        </div>
        {paid.map((src) => <SourceRow key={src.source_name} src={src} />)}
      </div>
    </div>
  );
}
