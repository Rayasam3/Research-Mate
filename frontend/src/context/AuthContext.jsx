import { createContext, useContext, useEffect, useState } from "react";

import { apiClient } from "../api/client";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => localStorage.getItem("token"));
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!token) {
      setLoading(false);
      return;
    }
    apiClient.defaults.headers.common["Authorization"] = `Bearer ${token}`;
    apiClient
      .get("/api/auth/me")
      .then((res) => setUser(res.data))
      .catch(() => {
        setToken(null);
        localStorage.removeItem("token");
      })
      .finally(() => setLoading(false));
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

  return (
    <AuthContext.Provider value={{ token, user, loading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}