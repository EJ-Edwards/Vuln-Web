import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { api } from "../api/api";
import { useAuth } from "../context/AuthContext";

export default function RoomDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const [room, setRoom] = useState(null);
  const [loading, setLoading] = useState(true);
  const [booking, setBooking] = useState({
    check_in: "",
    check_out: "",
    num_guests: 1,
    special_requests: "",
  });
  const [bookingMsg, setBookingMsg] = useState(null);
  const [review, setReview] = useState({ rating: 5, comment: "" });
  const [reviewMsg, setReviewMsg] = useState(null);

  useEffect(() => {
    api.getRoom(id)
      .then(setRoom)
      .catch(() => navigate("/rooms"))
      .finally(() => setLoading(false));
  }, [id, navigate]);

  const handleBook = async (e) => {
    e.preventDefault();
    setBookingMsg(null);
    if (!user) {
      navigate("/login");
      return;
    }
    try {
      const res = await api.createBooking({ room_id: parseInt(id), ...booking });
      setBookingMsg({ type: "success", text: `${res.message} ${res.nights} night(s) — $${res.total_price}` });
      setBooking({ check_in: "", check_out: "", num_guests: 1, special_requests: "" });
    } catch (err) {
      setBookingMsg({ type: "error", text: err.message });
    }
  };

  const handleReview = async (e) => {
    e.preventDefault();
    setReviewMsg(null);
    if (!user) {
      navigate("/login");
      return;
    }
    try {
      await api.createReview(id, review);
      setReviewMsg({ type: "success", text: "Review submitted!" });
      setReview({ rating: 5, comment: "" });
      const updated = await api.getRoom(id);
      setRoom(updated);
    } catch (err) {
      setReviewMsg({ type: "error", text: err.message });
    }
  };

  if (loading) return <div className="loading">Loading...</div>;
  if (!room) return null;

  const nights =
    booking.check_in && booking.check_out
      ? Math.max(0, Math.ceil((new Date(booking.check_out) - new Date(booking.check_in)) / 86400000))
      : 0;

  return (
    <div className="page">
      <div className="container">
        <div className="room-detail">
          <div className="room-detail-image">
            <img src={room.image_url} alt={room.name} />
          </div>

          <div className="room-detail-content">
            <div className="room-detail-info">
              <span className={`room-badge badge-${room.type}`}>{room.type}</span>
              <h1>{room.name}</h1>
              <div className="room-detail-meta">
                <span>👥 Up to {room.capacity} guests</span>
                {room.avg_rating > 0 && (
                  <span>★ {room.avg_rating} ({room.review_count} reviews)</span>
                )}
              </div>
              <p className="room-detail-desc">{room.description}</p>
              <div className="room-detail-price">
                <span className="price-amount">${room.price_per_night}</span>
                <span className="price-label">/ night</span>
              </div>
              <div className="amenities-list">
                <h3>Amenities</h3>
                <div className="amenities-grid">
                  {room.amenities?.map((a) => (
                    <span key={a} className="amenity-tag">{a}</span>
                  ))}
                </div>
              </div>
            </div>

            {/* Booking Form */}
            <div className="booking-card">
              <h3>Book This Room</h3>
              {bookingMsg && (
                <div className={`alert alert-${bookingMsg.type}`}>{bookingMsg.text}</div>
              )}
              <form onSubmit={handleBook}>
                <div className="form-row">
                  <div className="form-group">
                    <label>Check-in</label>
                    <input
                      type="date"
                      required
                      value={booking.check_in}
                      onChange={(e) => setBooking({ ...booking, check_in: e.target.value })}
                    />
                  </div>
                  <div className="form-group">
                    <label>Check-out</label>
                    <input
                      type="date"
                      required
                      value={booking.check_out}
                      onChange={(e) => setBooking({ ...booking, check_out: e.target.value })}
                    />
                  </div>
                </div>
                <div className="form-group">
                  <label>Number of Guests</label>
                  <select
                    value={booking.num_guests}
                    onChange={(e) => setBooking({ ...booking, num_guests: parseInt(e.target.value) })}
                  >
                    {Array.from({ length: room.capacity }, (_, i) => (
                      <option key={i + 1} value={i + 1}>{i + 1} Guest{i > 0 ? "s" : ""}</option>
                    ))}
                  </select>
                </div>
                <div className="form-group">
                  <label>Special Requests</label>
                  <textarea
                    rows="3"
                    placeholder="Any special requirements..."
                    value={booking.special_requests}
                    onChange={(e) => setBooking({ ...booking, special_requests: e.target.value })}
                  />
                </div>
                {nights > 0 && (
                  <div className="booking-summary">
                    <span>{nights} night{nights > 1 ? "s" : ""}</span>
                    <span className="booking-total">${(nights * room.price_per_night).toFixed(2)}</span>
                  </div>
                )}
                <button type="submit" className="btn btn-primary btn-block">
                  {user ? "Confirm Booking" : "Login to Book"}
                </button>
              </form>
            </div>
          </div>

          {/* Reviews */}
          <div className="reviews-section">
            <h2>Guest Reviews</h2>
            {user && (
              <form className="review-form" onSubmit={handleReview}>
                {reviewMsg && (
                  <div className={`alert alert-${reviewMsg.type}`}>{reviewMsg.text}</div>
                )}
                <div className="form-row">
                  <div className="form-group">
                    <label>Rating</label>
                    <select value={review.rating} onChange={(e) => setReview({ ...review, rating: parseInt(e.target.value) })}>
                      {[5, 4, 3, 2, 1].map((r) => (
                        <option key={r} value={r}>{"★".repeat(r)}{"☆".repeat(5 - r)}</option>
                      ))}
                    </select>
                  </div>
                  <div className="form-group" style={{ flex: 2 }}>
                    <label>Comment</label>
                    <input
                      type="text"
                      placeholder="Share your experience..."
                      value={review.comment}
                      onChange={(e) => setReview({ ...review, comment: e.target.value })}
                    />
                  </div>
                  <button type="submit" className="btn btn-primary" style={{ alignSelf: "flex-end" }}>
                    Submit
                  </button>
                </div>
              </form>
            )}
            {room.reviews?.length === 0 ? (
              <p className="empty-state">No reviews yet. Be the first to review!</p>
            ) : (
              <div className="reviews-list">
                {room.reviews?.map((r) => (
                  <div key={r.id} className="review-card">
                    <div className="review-header">
                      <strong>{r.user_name}</strong>
                      <span className="review-stars">{"★".repeat(r.rating)}{"☆".repeat(5 - r.rating)}</span>
                    </div>
                    <p>{r.comment}</p>
                    <small>{new Date(r.created_at).toLocaleDateString()}</small>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
