import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function Navbar() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = async () => {
    await logout();
    navigate("/");
  };

  return (
    <nav className="navbar">
      <div className="nav-container">
        <Link to="/" className="nav-brand">
          <span className="brand-icon">✦</span>
          Grand Hotel
        </Link>
        <div className="nav-links">
          <Link to="/">Home</Link>
          <Link to="/rooms">Rooms</Link>
          {user && <Link to="/bookings">My Bookings</Link>}
          {user?.role === "admin" && <Link to="/admin">Dashboard</Link>}
          {user ? (
            <div className="nav-user">
              <span className="nav-user-name">{user.name}</span>
              <button onClick={handleLogout} className="btn btn-outline btn-sm">
                Logout
              </button>
            </div>
          ) : (
            <>
              <Link to="/login">Login</Link>
              <Link to="/register" className="btn btn-primary btn-sm">
                Sign Up
              </Link>
            </>
          )}
        </div>
      </div>
    </nav>
  );
}
