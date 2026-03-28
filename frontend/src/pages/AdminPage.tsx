import { useEffect, useState } from "react";
import { adminApi, authApi } from "../api";
import type { User, Invite } from "../types";

interface Props { user: User; onLogout: () => void; }

export default function AdminPage({ user, onLogout }: Props) {
  const [users, setUsers] = useState<User[]>([]);
  const [invites, setInvites] = useState<Invite[]>([]);
  const [inviteEmail, setInviteEmail] = useState("");
  const [message, setMessage] = useState("");
  const [newInvite, setNewInvite] = useState<Invite | null>(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    Promise.all([adminApi.listUsers(), adminApi.listInvites()])
      .then(([u, i]) => { setUsers(u.data); setInvites(i.data); });
  }, []);

  const createInvite = async () => {
    const res = await adminApi.createInvite(inviteEmail || undefined);
    setNewInvite(res.data);
    setInviteEmail("");
    setInvites((prev) => [res.data, ...prev]);
  };

  const copyLink = () => {
    if (newInvite) {
      navigator.clipboard.writeText(newInvite.invite_url);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const toggleUser = async (u: User) => {
    if (u.is_admin) return;
    if (u.is_active) {
      await adminApi.deactivateUser(u.id);
    } else {
      await adminApi.activateUser(u.id);
    }
    setUsers((prev) => prev.map((x) => x.id === u.id ? { ...x, is_active: !u.is_active } : x));
  };

  const revokeInvite = async (id: string) => {
    await adminApi.revokeInvite(id);
    setInvites((prev) => prev.map((i) => i.id === id ? { ...i, is_active: false } : i));
  };

  const handleLogout = async () => { await authApi.logout(); onLogout(); };

  return (
    <div style={{ maxWidth: 860, margin: "0 auto", padding: 24 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 24 }}>
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 700 }}>Admin Panel</h1>
          <a href="/" style={{ fontSize: 12, color: "var(--muted)" }}>← Back to Dashboard</a>
        </div>
        <button className="btn-secondary" onClick={handleLogout}>Sign Out</button>
      </div>

      {/* Create invite */}
      <div className="card" style={{ marginBottom: 20 }}>
        <h2 style={{ fontSize: 16, fontWeight: 700, marginBottom: 14 }}>Invite a User</h2>
        <div style={{ display: "flex", gap: 10 }}>
          <input
            type="email"
            placeholder="Email (optional — leave blank for a generic link)"
            value={inviteEmail}
            onChange={(e) => setInviteEmail(e.target.value)}
            style={{ flex: 1 }}
          />
          <button className="btn-primary" onClick={createInvite} style={{ whiteSpace: "nowrap" }}>
            Generate Invite Link
          </button>
        </div>

        {newInvite && (
          <div style={{ marginTop: 14, padding: 12, background: "var(--surface2)", borderRadius: "var(--radius)", display: "flex", gap: 10, alignItems: "center" }}>
            <input
              readOnly
              value={newInvite.invite_url}
              style={{ flex: 1, fontSize: 12 }}
              onFocus={(e) => e.target.select()}
            />
            <button className="btn-primary" onClick={copyLink} style={{ whiteSpace: "nowrap", fontSize: 12 }}>
              {copied ? "Copied ✓" : "Copy Link"}
            </button>
          </div>
        )}
        {newInvite && (
          <div style={{ fontSize: 12, color: "var(--muted)", marginTop: 8 }}>
            Expires: {new Date(newInvite.expires_at).toLocaleString()} · Single-use
          </div>
        )}
      </div>

      {/* Users */}
      <div className="card" style={{ marginBottom: 20, padding: 0, overflow: "hidden" }}>
        <div style={{ padding: "12px 16px", background: "var(--surface2)", borderBottom: "1px solid var(--border)" }}>
          <h2 style={{ fontSize: 15, fontWeight: 700 }}>Users ({users.length})</h2>
        </div>
        {users.map((u) => (
          <div key={u.id} style={{ padding: "12px 16px", borderBottom: "1px solid var(--border)", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <div>
              <div style={{ fontWeight: 500, fontSize: 13 }}>
                {u.name}
                {u.is_admin && <span style={{ marginLeft: 8, fontSize: 11, color: "var(--primary)", background: "rgba(92,110,248,0.1)", borderRadius: 4, padding: "1px 6px" }}>Admin</span>}
              </div>
              <div style={{ color: "var(--muted)", fontSize: 12 }}>{u.email}</div>
              <div style={{ color: "var(--muted)", fontSize: 11, marginTop: 2 }}>
                Joined {new Date(u.created_at).toLocaleDateString()}
                {u.last_login_at && ` · Last login ${new Date(u.last_login_at).toLocaleDateString()}`}
              </div>
            </div>
            {!u.is_admin && (
              <button
                className={u.is_active ? "btn-danger" : "btn-secondary"}
                style={{ fontSize: 12, padding: "5px 12px" }}
                onClick={() => toggleUser(u)}
              >
                {u.is_active ? "Deactivate" : "Activate"}
              </button>
            )}
          </div>
        ))}
      </div>

      {/* Active invites */}
      <div className="card" style={{ padding: 0, overflow: "hidden" }}>
        <div style={{ padding: "12px 16px", background: "var(--surface2)", borderBottom: "1px solid var(--border)" }}>
          <h2 style={{ fontSize: 15, fontWeight: 700 }}>Recent Invites</h2>
        </div>
        {invites.length === 0 && (
          <div style={{ padding: 16, color: "var(--muted)", fontSize: 13 }}>No invites yet.</div>
        )}
        {invites.map((inv) => (
          <div key={inv.id} style={{ padding: "12px 16px", borderBottom: "1px solid var(--border)", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <div>
              <div style={{ fontSize: 13, color: inv.is_active ? "var(--text)" : "var(--muted)" }}>
                {inv.email || "Generic invite"}
                {!inv.is_active && <span style={{ marginLeft: 8, fontSize: 11, color: "var(--muted)" }}>(revoked/used)</span>}
                {inv.used_at && <span style={{ marginLeft: 8, fontSize: 11, color: "var(--green)" }}>✓ Used</span>}
              </div>
              <div style={{ fontSize: 11, color: "var(--muted)", marginTop: 2 }}>
                Expires {new Date(inv.expires_at).toLocaleString()}
              </div>
            </div>
            {inv.is_active && !inv.used_at && (
              <button className="btn-danger" style={{ fontSize: 11, padding: "4px 10px" }} onClick={() => revokeInvite(inv.id)}>
                Revoke
              </button>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
