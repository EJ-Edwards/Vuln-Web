import { Link } from "react-router-dom";
import { useEffect, useState } from "react";
import { api } from "../api/api";
import RoomCard from "../components/RoomCard";

export default function Home() {
  const [featuredRooms, setFeaturedRooms] = useState([]);

  useEffect(() => {
    api.getRooms().then((rooms) => setFeaturedRooms(rooms.slice(0, 3)));
  }, []);

  return (
    <div className="home">
      {/* Hero */}
      <section className="hero">
        <div className="hero-overlay" />
        <div className="hero-content">
          <h1>Welcome to Grand Hotel</h1>
          <p>Experience unparalleled luxury and comfort in the heart of paradise</p>
          <div className="hero-actions">
            <Link to="/rooms" className="btn btn-primary btn-lg">
              Explore Rooms
            </Link>
            <Link to="/register" className="btn btn-outline btn-lg">
              Join Now
            </Link>
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="features">
        <div className="container">
          <div className="features-grid">
            <div className="feature-card">
              <div className="feature-icon">🏨</div>
              <h3>Luxury Rooms</h3>
              <p>Choose from our collection of beautifully designed rooms and suites</p>
            </div>
            <div className="feature-card">
              <div className="feature-icon">🍽️</div>
              <h3>Fine Dining</h3>
              <p>Savor world-class cuisine prepared by our award-winning chefs</p>
            </div>
            <div className="feature-card">
              <div className="feature-icon">💆</div>
              <h3>Spa & Wellness</h3>
              <p>Rejuvenate your body and mind at our full-service wellness center</p>
            </div>
            <div className="feature-card">
              <div className="feature-icon">🏊</div>
              <h3>Pool & Beach</h3>
              <p>Relax by our infinity pool or on our private stretch of beach</p>
            </div>
          </div>
        </div>
      </section>

      {/* Featured Rooms */}
      <section className="section">
        <div className="container">
          <div className="section-header">
            <h2>Featured Rooms</h2>
            <p>Discover our most popular accommodations</p>
          </div>
          <div className="rooms-grid">
            {featuredRooms.map((room) => (
              <RoomCard key={room.id} room={room} />
            ))}
          </div>
          <div className="section-footer">
            <Link to="/rooms" className="btn btn-outline">
              View All Rooms →
            </Link>
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="cta-section">
        <div className="container">
          <h2>Ready for an Unforgettable Stay?</h2>
          <p>Book your room today and enjoy exclusive member benefits</p>
          <Link to="/rooms" className="btn btn-primary btn-lg">
            Book Now
          </Link>
        </div>
      </section>
    </div>
  );
}
