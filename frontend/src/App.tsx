import { Routes, Route, Navigate } from "react-router-dom";
import { useEffect, useState } from "react";
import { authApi } from "./api";
import type { User } from "./types";
import Dashboard from "./pages/Dashboard";
import LoginPage from "./pages/LoginPage";
import RegisterPage from "./pages/RegisterPage";
import AdminPage from "./pages/AdminPage";

export default function App() {
  const [user, setUser] = useState<User | null | undefined>(undefined);

  useEffect(() => {
    authApi.me()
      .then((res) => setUser(res.data))
      .catch(() => setUser(null));
  }, []);

  if (user === undefined) {
    return (
      <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: "100vh" }}>
        <div style={{ color: "var(--muted)" }}>Loading…</div>
      </div>
    );
  }

  return (
    <Routes>
      <Route path="/login" element={user ? <Navigate to="/" /> : <LoginPage onLogin={setUser} />} />
      <Route path="/register" element={<RegisterPage onLogin={setUser} />} />
      <Route
        path="/admin"
        element={user?.is_admin ? <AdminPage user={user} onLogout={() => setUser(null)} /> : <Navigate to="/" />}
      />
      <Route
        path="/*"
        element={user ? <Dashboard user={user} onLogout={() => setUser(null)} /> : <Navigate to="/login" />}
      />
    </Routes>
  );
}
