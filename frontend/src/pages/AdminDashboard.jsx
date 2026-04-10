import { useEffect, useState } from "react";
import { api } from "../api/api";

export default function AdminDashboard() {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadStats();
  }, []);

  const loadStats = async () => {
    try {
      const data = await api.getAdminStats();
      setStats(data);
    } catch {
      // ignore
    }
    setLoading(false);
  };

  const handleStatusChange = async (bookingId, status) => {
    try {
      await api.updateBookingStatus(bookingId, status);
      loadStats();
    } catch {
      // ignore
    }
  };

  if (loading) return <div className="loading">Loading...</div>;
  if (!stats) return <div className="loading">Error loading dashboard</div>;

  const statusColors = {
    confirmed: "status-confirmed",
    checked_in: "status-active",
    checked_out: "status-completed",
    cancelled: "status-cancelled",
  };

  return (
    <div className="page">
      <div className="container">
        <div className="page-header">
          <h1>Admin Dashboard</h1>
          <p>Hotel management overview</p>
        </div>

        <div className="stats-grid">
          <div className="stat-card">
            <div className="stat-icon">🏨</div>
            <div className="stat-info">
              <span className="stat-value">{stats.total_rooms}</span>
              <span className="stat-label">Total Rooms</span>
            </div>
          </div>
          <div className="stat-card">
            <div className="stat-icon">📋</div>
            <div className="stat-info">
              <span className="stat-value">{stats.total_bookings}</span>
              <span className="stat-label">Active Bookings</span>
            </div>
          </div>
          <div className="stat-card">
            <div className="stat-icon">💰</div>
            <div className="stat-info">
              <span className="stat-value">${stats.total_revenue.toLocaleString()}</span>
              <span className="stat-label">Total Revenue</span>
            </div>
          </div>
          <div className="stat-card">
            <div className="stat-icon">👥</div>
            <div className="stat-info">
              <span className="stat-value">{stats.total_guests}</span>
              <span className="stat-label">Registered Guests</span>
            </div>
          </div>
        </div>

        <div className="admin-section">
          <h2>Recent Bookings</h2>
          <div className="table-wrapper">
            <table className="admin-table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Guest</th>
                  <th>Room</th>
                  <th>Check-in</th>
                  <th>Check-out</th>
                  <th>Total</th>
                  <th>Status</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {stats.recent_bookings.map((b) => (
                  <tr key={b.id}>
                    <td>#{b.id}</td>
                    <td>{b.user_name}</td>
                    <td>{b.room_name}</td>
                    <td>{b.check_in}</td>
                    <td>{b.check_out}</td>
                    <td>${b.total_price.toFixed(2)}</td>
                    <td>
                      <span className={`status-badge ${statusColors[b.status]}`}>
                        {b.status.replace("_", " ")}
                      </span>
                    </td>
                    <td>
                      <select
                        value={b.status}
                        onChange={(e) => handleStatusChange(b.id, e.target.value)}
                        className="status-select"
                      >
                        <option value="confirmed">Confirmed</option>
                        <option value="checked_in">Checked In</option>
                        <option value="checked_out">Checked Out</option>
                        <option value="cancelled">Cancelled</option>
                      </select>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
