import { Link } from "react-router-dom";

export default function RoomCard({ room }) {
  const typeLabel = {
    standard: "Standard",
    deluxe: "Deluxe",
    suite: "Suite",
    penthouse: "Penthouse",
  };

  return (
    <div className="room-card">
      <div className="room-card-image">
        <img src={room.image_url} alt={room.name} loading="lazy" />
        <span className={`room-badge badge-${room.type}`}>
          {typeLabel[room.type] || room.type}
        </span>
      </div>
      <div className="room-card-body">
        <h3>{room.name}</h3>
        <p className="room-description">{room.description}</p>
        <div className="room-meta">
          <span className="room-capacity">👥 Up to {room.capacity} guests</span>
          {room.avg_rating > 0 && (
            <span className="room-rating">
              ★ {room.avg_rating} ({room.review_count})
            </span>
          )}
        </div>
        <div className="room-amenities">
          {room.amenities?.slice(0, 4).map((a) => (
            <span key={a} className="amenity-tag">{a}</span>
          ))}
          {room.amenities?.length > 4 && (
            <span className="amenity-tag amenity-more">+{room.amenities.length - 4}</span>
          )}
        </div>
        <div className="room-card-footer">
          <div className="room-price">
            <span className="price-amount">${room.price_per_night}</span>
            <span className="price-label">/ night</span>
          </div>
          <Link to={`/rooms/${room.id}`} className="btn btn-primary">
            View Details
          </Link>
        </div>
      </div>
    </div>
  );
}
