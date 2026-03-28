import { useState, useRef, useEffect } from "react";
import { locationsApi } from "../../api";
import type { Location } from "../../types";

interface Props {
  currentLocation: Location | null;
  onSelect: (loc: Location) => void;
}

export default function LocationSearch({ currentLocation, onSelect }: Props) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<Location[]>([]);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  const search = (q: string) => {
    setQuery(q);
    if (timer.current) clearTimeout(timer.current);
    if (q.length < 2) { setResults([]); setOpen(false); return; }
    timer.current = setTimeout(async () => {
      setLoading(true);
      try {
        const res = await locationsApi.search(q);
        setResults(res.data);
        setOpen(true);
      } catch { /* ignore */ }
      finally { setLoading(false); }
    }, 400);
  };

  const select = (loc: Location) => {
    onSelect(loc);
    setQuery(loc.display_name.split(",").slice(0, 2).join(","));
    setOpen(false);
  };

  return (
    <div ref={ref} style={{ position: "relative", width: 320 }}>
      <input
        type="text"
        value={query}
        placeholder={currentLocation ? currentLocation.display_name.split(",")[0] : "Search city, county, or zip…"}
        onChange={(e) => search(e.target.value)}
        onFocus={() => results.length > 0 && setOpen(true)}
        style={{ paddingLeft: 32 }}
      />
      <span style={{ position: "absolute", left: 10, top: "50%", transform: "translateY(-50%)", fontSize: 14, pointerEvents: "none" }}>🔍</span>
      {loading && <span style={{ position: "absolute", right: 10, top: "50%", transform: "translateY(-50%)", fontSize: 11, color: "var(--muted)" }}>…</span>}

      {open && results.length > 0 && (
        <div style={{
          position: "absolute", top: "calc(100% + 4px)", left: 0, right: 0, zIndex: 2000,
          background: "var(--surface)", border: "1px solid var(--border)",
          borderRadius: "var(--radius)", boxShadow: "var(--shadow)", maxHeight: 280, overflowY: "auto",
        }}>
          {results.map((r, i) => (
            <div
              key={i}
              onClick={() => select(r)}
              style={{ padding: "10px 14px", cursor: "pointer", borderBottom: "1px solid var(--border)", fontSize: 13 }}
              onMouseEnter={(e) => (e.currentTarget.style.background = "var(--surface2)")}
              onMouseLeave={(e) => (e.currentTarget.style.background = "")}
            >
              <div style={{ fontWeight: 500 }}>{r.display_name.split(",").slice(0, 2).join(",")}</div>
              <div style={{ color: "var(--muted)", fontSize: 11, marginTop: 2 }}>{r.state}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
