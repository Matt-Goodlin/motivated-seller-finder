import { useState, useEffect } from "react";
import { useSearchParams, useNavigate } from "react-router-dom";
import { authApi } from "../api";
import type { User } from "../types";

interface Props { onLogin: (user: User) => void; }

export default function RegisterPage({ onLogin }: Props) {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const token = params.get("token") || "";

  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState("");
  const [tokenValid, setTokenValid] = useState<boolean | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!token) { setTokenValid(false); return; }
    authApi.validateInvite(token)
      .then((res) => {
        setTokenValid(true);
        if (res.data.email) setEmail(res.data.email);
      })
      .catch(() => setTokenValid(false));
  }, [token]);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (password !== confirm) { setError("Passwords do not match."); return; }
    if (password.length < 8) { setError("Password must be at least 8 characters."); return; }
    setLoading(true);
    setError("");
    try {
      const res = await authApi.register({ invite_token: token, name, email, password });
      onLogin(res.data.user);
      navigate("/");
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setError(msg || "Registration failed.");
    } finally {
      setLoading(false);
    }
  };

  if (tokenValid === null) {
    return <div style={{ textAlign: "center", marginTop: "40vh", color: "var(--muted)" }}>Validating invite…</div>;
  }

  if (tokenValid === false) {
    return (
      <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: "100vh" }}>
        <div className="card" style={{ width: 380, padding: 32, textAlign: "center" }}>
          <div style={{ fontSize: 32, marginBottom: 12 }}>⚠️</div>
          <h2 style={{ marginBottom: 8 }}>Invalid Invite</h2>
          <p style={{ color: "var(--muted)" }}>This invite link is invalid, expired, or has already been used.</p>
          <button className="btn-secondary" style={{ marginTop: 20 }} onClick={() => navigate("/login")}>Back to Login</button>
        </div>
      </div>
    );
  }

  return (
    <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: "100vh" }}>
      <div className="card" style={{ width: 400, padding: 32 }}>
        <h1 style={{ fontSize: 22, fontWeight: 700, marginBottom: 8 }}>Create Your Account</h1>
        <p style={{ color: "var(--muted)", marginBottom: 24 }}>You've been invited to Motivated Seller Finder.</p>

        <form onSubmit={submit} style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          {[
            { label: "Full Name", value: name, setter: setName, type: "text", placeholder: "John Smith" },
            { label: "Email", value: email, setter: setEmail, type: "email", placeholder: "you@example.com" },
            { label: "Password", value: password, setter: setPassword, type: "password", placeholder: "Min. 8 characters" },
            { label: "Confirm Password", value: confirm, setter: setConfirm, type: "password", placeholder: "Repeat password" },
          ].map(({ label, value, setter, type, placeholder }) => (
            <div key={label}>
              <label style={{ display: "block", marginBottom: 4, color: "var(--muted)", fontSize: 12 }}>{label}</label>
              <input type={type} value={value} onChange={(e) => setter(e.target.value)} required placeholder={placeholder} />
            </div>
          ))}

          {error && (
            <div style={{ color: "var(--red)", fontSize: 13, padding: "8px 12px", background: "rgba(239,68,68,0.1)", borderRadius: "var(--radius)" }}>
              {error}
            </div>
          )}

          <button type="submit" className="btn-primary" disabled={loading} style={{ marginTop: 4, padding: "10px 0" }}>
            {loading ? "Creating account…" : "Create Account"}
          </button>
        </form>
      </div>
    </div>
  );
}
