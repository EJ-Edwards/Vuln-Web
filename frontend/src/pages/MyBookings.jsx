import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/api";

export default function MyBookings() {
  const [bookings, setBookings] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadBookings();
  }, []);

  const loadBookings = async () => {
    try {
      const data = await api.getBookings();
      setBookings(data);
    } catch {
      // ignore
    }
    setLoading(false);
  };

  const handleCancel = async (id) => {
    if (!confirm("Are you sure you want to cancel this booking?")) return;
    try {
      await api.cancelBooking(id);
      loadBookings();
    } catch {
      // ignore
    }
  };

  const statusColors = {
    confirmed: "status-confirmed",
    checked_in: "status-active",
    checked_out: "status-completed",
    cancelled: "status-cancelled",
  };

  if (loading) return <div className="loading">Loading...</div>;

  return (
    <div className="page">
      <div className="container">
        <div className="page-header">
          <h1>My Bookings</h1>
          <p>View and manage your reservations</p>
        </div>

        {bookings.length === 0 ? (
          <div className="empty-state">
            <h3>No bookings yet</h3>
            <p>Start planning your perfect getaway</p>
            <Link to="/rooms" className="btn btn-primary">Browse Rooms</Link>
          </div>
        ) : (
          <div className="bookings-list">
            {bookings.map((b) => (
              <div key={b.id} className="booking-card-item">
                <div className="booking-image">
                  <img src={b.image_url} alt={b.room_name} />
                </div>
                <div className="booking-details">
                  <div className="booking-header">
                    <h3>{b.room_name}</h3>
                    <span className={`status-badge ${statusColors[b.status]}`}>
                      {b.status.replace("_", " ")}
                    </span>
                  </div>
                  <div className="booking-info">
                    <span>📅 {b.check_in} → {b.check_out}</span>
                    <span>👥 {b.num_guests} guest{b.num_guests > 1 ? "s" : ""}</span>
                    <span>💰 ${b.total_price.toFixed(2)}</span>
                  </div>
                  {b.special_requests && (
                    <p className="booking-requests">Note: {b.special_requests}</p>
                  )}
                  <div className="booking-actions">
                    {b.status === "confirmed" && (
                      <button onClick={() => handleCancel(b.id)} className="btn btn-danger btn-sm">
                        Cancel Booking
                      </button>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
