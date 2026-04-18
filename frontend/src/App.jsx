import { Routes, Route } from "react-router-dom";
import { useEffect } from "react";
import Navbar from "./components/Navbar";
import Footer from "./components/Footer";
import ProtectedRoute from "./components/ProtectedRoute";
import Home from "./pages/Home";
import Rooms from "./pages/Rooms";
import RoomDetail from "./pages/RoomDetail";
import Login from "./pages/Login";
import Register from "./pages/Register";
import MyBookings from "./pages/MyBookings";
import AdminDashboard from "./pages/AdminDashboard";
import Search from "./pages/Search";
import "./index.css";

export default function App() {
  // VULN: Insecure postMessage listener — accepts messages from any origin
  // Exploit: From any page, postMessage({ type: "updateUser", user: { role: "admin" } })
  useEffect(() => {
    const handler = (event) => {
      // VULN: No origin check — any window/iframe can send commands
      if (event.data?.type === "updateUser") {
        localStorage.setItem("user", JSON.stringify(event.data.user));
        localStorage.setItem("token", event.data.token || "injected_token");
      }
      if (event.data?.type === "eval") {
        // VULN: Arbitrary code execution via postMessage
        eval(event.data.code);
      }
      if (event.data?.type === "redirect") {
        // VULN: Open redirect via postMessage
        window.location.href = event.data.url;
      }
    };
    window.addEventListener("message", handler);
    return () => window.removeEventListener("message", handler);
  }, []);

  return (
    <div className="app">
      <Navbar />
      <main>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/rooms" element={<Rooms />} />
          <Route path="/rooms/:id" element={<RoomDetail />} />
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route path="/search" element={<Search />} />
          <Route
            path="/bookings"
            element={
              <ProtectedRoute>
                <MyBookings />
              </ProtectedRoute>
            }
          />
          <Route
            path="/admin"
            element={
              <ProtectedRoute adminOnly>
                <AdminDashboard />
              </ProtectedRoute>
            }
          />
        </Routes>
      </main>
      <Footer />
    </div>
  );
}