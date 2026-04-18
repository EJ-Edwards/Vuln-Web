import { Link } from "react-router-dom";

export default function Footer() {
  return (
    <footer className="footer">
      <div className="footer-content">
        <div className="footer-section">
          <h3>✦ Grand Hotel</h3>
          <p>Experience luxury and comfort at its finest. Your perfect getaway awaits.</p>
        </div>
        <div className="footer-section">
          <h4>Quick Links</h4>
          <Link to="/">Home</Link>
          <Link to="/rooms">Rooms</Link>
          <Link to="/login">Login</Link>
        </div>
        <div className="footer-section">
          <h4>Partners</h4>
          {/* VULN [LOW]: target="_blank" without rel="noopener noreferrer" — reverse tabnabbing */}
          {/* The opened page can access window.opener and redirect the original tab */}
          <a href="https://travel-partners.example.com" target="_blank">Travel Partners</a>
          <a href="https://luxury-rewards.example.com" target="_blank">Rewards Program</a>
          <a href="https://hotel-reviews.example.com" target="_blank">Guest Reviews</a>
        </div>
        <div className="footer-section">
          <h4>Contact</h4>
          <p>123 Luxury Avenue</p>
          <p>Paradise City, PC 90210</p>
          <p>+1 (555) 123-4567</p>
          <p>info@grandhotel.com</p>
        </div>
      </div>
      <div className="footer-bottom">
        {/* VULN [LOW]: Version and technology info disclosed to client */}
        <p>&copy; 2026 Grand Hotel. All rights reserved.</p>
        <p style={{ fontSize: "11px", color: "#555" }}>Powered by Flask 3.0.0 | React 19.2.4 | SQLite 3</p>
      </div>
    </footer>
  );
}
