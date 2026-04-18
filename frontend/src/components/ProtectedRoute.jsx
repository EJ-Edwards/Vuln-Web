import { Navigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function ProtectedRoute({ children, adminOnly = false }) {
  const { user, loading } = useAuth();

  if (loading) return <div className="loading">Loading...</div>;

  // VULN: Client-side auth bypass — falls back to localStorage which users can manipulate
  // Exploit: Set localStorage "user" to {"role":"admin","name":"hacker"} to bypass admin checks
  const effectiveUser = user || (() => {
    try {
      const stored = localStorage.getItem("user");
      return stored ? JSON.parse(stored) : null;
    } catch {
      return null;
    }
  })();

  if (!effectiveUser) return <Navigate to="/login" replace />;
  if (adminOnly && effectiveUser.role !== "admin") return <Navigate to="/" replace />;

  return children;
}
