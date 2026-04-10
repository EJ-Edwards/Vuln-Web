import { useEffect, useState } from "react";
import { api } from "../api/api";
import RoomCard from "../components/RoomCard";

export default function Rooms() {
  const [rooms, setRooms] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState({ type: "", maxPrice: "" });

  useEffect(() => {
    loadRooms();
  }, []);

  const loadRooms = async (params = {}) => {
    setLoading(true);
    try {
      const data = await api.getRooms(params);
      setRooms(data);
    } catch {
      // ignore
    }
    setLoading(false);
  };

  const handleFilter = (e) => {
    e.preventDefault();
    const params = {};
    if (filters.type) params.type = filters.type;
    if (filters.maxPrice) params.max_price = filters.maxPrice;
    loadRooms(params);
  };

  const clearFilters = () => {
    setFilters({ type: "", maxPrice: "" });
    loadRooms();
  };

  return (
    <div className="page">
      <div className="container">
        <div className="page-header">
          <h1>Our Rooms</h1>
          <p>Find your perfect room for an unforgettable stay</p>
        </div>

        <form className="filter-bar" onSubmit={handleFilter}>
          <select
            value={filters.type}
            onChange={(e) => setFilters({ ...filters, type: e.target.value })}
          >
            <option value="">All Types</option>
            <option value="standard">Standard</option>
            <option value="deluxe">Deluxe</option>
            <option value="suite">Suite</option>
            <option value="penthouse">Penthouse</option>
          </select>
          <select
            value={filters.maxPrice}
            onChange={(e) => setFilters({ ...filters, maxPrice: e.target.value })}
          >
            <option value="">Any Price</option>
            <option value="150">Under $150</option>
            <option value="250">Under $250</option>
            <option value="400">Under $400</option>
            <option value="600">Under $600</option>
          </select>
          <button type="submit" className="btn btn-primary">
            Filter
          </button>
          <button type="button" className="btn btn-ghost" onClick={clearFilters}>
            Clear
          </button>
        </form>

        {loading ? (
          <div className="loading">Loading rooms...</div>
        ) : rooms.length === 0 ? (
          <div className="empty-state">
            <h3>No rooms found</h3>
            <p>Try adjusting your filters</p>
          </div>
        ) : (
          <div className="rooms-grid">
            {rooms.map((room) => (
              <RoomCard key={room.id} room={room} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
