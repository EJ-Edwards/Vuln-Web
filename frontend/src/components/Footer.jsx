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
          <h4>Contact</h4>
          <p>123 Luxury Avenue</p>
          <p>Paradise City, PC 90210</p>
          <p>+1 (555) 123-4567</p>
          <p>info@grandhotel.com</p>
        </div>
      </div>
      <div className="footer-bottom">
        <p>&copy; 2026 Grand Hotel. All rights reserved.</p>
      </div>
    </footer>
  );
}
