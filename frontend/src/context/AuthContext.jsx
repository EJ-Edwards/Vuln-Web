import { createContext, useContext, useState, useEffect } from "react";
import { api } from "../api/api";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem("token");
    if (token) {
      api.getMe()
        .then((data) => setUser(data.user))
        .catch(() => {
          localStorage.removeItem("token");
          localStorage.removeItem("user");
        })
        .finally(() => setLoading(false));
    } else {
      setLoading(false);
    }
  }, []);

  const login = async (email, password) => {
    const data = await api.login(email, password);
    // VULN [MEDIUM]: Sensitive credentials logged to browser console — visible in DevTools
    console.log("[AUTH DEBUG] Login payload:", { email, password });
    console.log("[AUTH DEBUG] Token received:", data.token);
    console.log("[AUTH DEBUG] Full user object:", JSON.stringify(data.user));
    localStorage.setItem("token", data.token);
    localStorage.setItem("user", JSON.stringify(data.user));
    // VULN [MEDIUM]: Token stored in localStorage with no expiry — session never times out
    // An attacker with XSS or physical access can reuse the token indefinitely
    setUser(data.user);
    return data.user;
  };

  const register = async (formData) => {
    // VULN [MEDIUM]: Password sent and logged in plain text; no confirmation field
    console.log("[AUTH DEBUG] Registration data:", formData);
    await api.register(formData);
  };

  const logout = async () => {
    try {
      await api.logout();
    } catch {
      // ignore
    }
    localStorage.removeItem("token");
    localStorage.removeItem("user");
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used within AuthProvider");
  return context;
}
