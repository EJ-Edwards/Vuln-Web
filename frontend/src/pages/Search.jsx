import { useState, useEffect, useRef } from "react";
import { useSearchParams, Link } from "react-router-dom";

const API_BASE = import.meta.env.VITE_API_URL || (import.meta.env.DEV ? "http://localhost:5000/api" : "/api");

export default function Search() {
  const [searchParams] = useSearchParams();
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const resultsRef = useRef(null);
  const query = searchParams.get("q") || "";

  useEffect(() => {
    if (query) {
      performSearch(query);
    }
  }, [query]);

  const performSearch = async (q) => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/search?q=${q}`);
      const data = await res.json();
      setResults(data.results || []);

      // VULN: DOM XSS — query parameter injected directly into innerHTML
      if (resultsRef.current) {
        resultsRef.current.innerHTML = `<h2>Search results for: ${data.query}</h2>`;
      }
    } catch {
      if (resultsRef.current) {
        resultsRef.current.innerHTML = `<h2>Search results for: ${q}</h2>`;
      }
    }
    setLoading(false);
  };

  // VULN: DOM XSS via document.location hash — reads and renders hash fragment as HTML
  useEffect(() => {
    const hash = window.location.hash.substring(1);
    if (hash) {
      const banner = document.getElementById("search-banner");
      if (banner) {
        banner.innerHTML = decodeURIComponent(hash);
      }
    }
  }, []);

  // VULN: eval() used to parse "advanced filter expressions" from URL
  const advancedFilter = searchParams.get("filter");
  let filteredResults = results;
  if (advancedFilter && results.length > 0) {
    try {
      // VULN: eval of user-controlled input from URL parameter
      filteredResults = results.filter((room) => eval(advancedFilter));
    } catch {
      // ignore filter errors
    }
  }

  return (
    <div className="page">
      <div className="container">
        <div className="page-header">
          <h1>Search Rooms</h1>
          <p>Find your perfect accommodation</p>
        </div>

        <div id="search-banner" />

        <form className="filter-bar" method="GET" action="/search">
          <input
            type="text"
            name="q"
            defaultValue={query}
            placeholder="Search rooms by name or description..."
            style={{ flex: 1 }}
          />
          <button type="submit" className="btn btn-primary">Search</button>
        </form>

        {loading && <div className="loading">Searching...</div>}

        {/* VULN: Reflected query echoed via ref innerHTML above */}
        <div ref={resultsRef} />

        {!loading && filteredResults.length === 0 && query && (
          <div className="empty-state">
            <h3>No rooms found</h3>
            <p>Try a different search term</p>
          </div>
        )}

        {!loading && filteredResults.length > 0 && (
          <div className="rooms-grid">
            {filteredResults.map((room) => (
              <div key={room.id} className="room-card">
                <div className="room-card-image">
                  <img src={room.image_url} alt={room.name} loading="lazy" />
                  <span className={`room-badge badge-${room.type}`}>{room.type}</span>
                </div>
                <div className="room-card-body">
                  {/* VULN: room name rendered as HTML — if SQLi injects HTML, it executes */}
                  <h3 dangerouslySetInnerHTML={{ __html: room.name }} />
                  <div className="room-card-footer">
                    <div className="room-price">
                      <span className="price-amount">${room.price_per_night}</span>
                      <span className="price-label">/ night</span>
                    </div>
                    <Link to={`/rooms/${room.id}`} className="btn btn-primary">View</Link>
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
