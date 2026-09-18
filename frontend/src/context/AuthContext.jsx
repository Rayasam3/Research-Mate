import { createContext, useEffect, useState } from "react";

import { apiClient } from "../api/client";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => localStorage.getItem("token"));
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;

    async function checkAuth() {
      if (!token) {
        if (!cancelled) setLoading(false);
        return;
      }

      apiClient.defaults.headers.common["Authorization"] = `Bearer ${token}`;

      try {
        const res = await apiClient.get("/api/auth/me");
        if (!cancelled) setUser(res.data);
      } catch {
        if (!cancelled) {
          setToken(null);
          localStorage.removeItem("token");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    checkAuth();

    return () => {
      cancelled = true;
    };
  }, [token]);

  function login(newToken) {
    localStorage.setItem("token", newToken);
    apiClient.defaults.headers.common["Authorization"] = `Bearer ${newToken}`;
    setToken(newToken);
  }

  function logout() {
    localStorage.removeItem("token");
    delete apiClient.defaults.headers.common["Authorization"];
    setToken(null);
    setUser(null);
  }

  const value = { token, user, loading, login, logout };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export default AuthContext;