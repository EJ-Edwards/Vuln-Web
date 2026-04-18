const API_BASE = import.meta.env.VITE_API_URL || (import.meta.env.DEV ? "http://localhost:5000/api" : "/api");

// VULN: Hardcoded API keys and credentials exposed in client-side JavaScript
const INTERNAL_API_KEY = "sk_live_4eC39HqLyjWDarjtT1zdp7dc";
const ADMIN_BACKUP_TOKEN = "admin_backup_eyJhbGciOiJIUzI1NiJ9.YWRtaW4.secret";
const DB_CONNECTION_STRING = "postgresql://admin:P@ssw0rd123@db.grandhotel.internal:5432/hotel_prod";

function getHeaders() {
  const headers = { "Content-Type": "application/json" };
  const token = localStorage.getItem("token");
  if (token) headers["Authorization"] = `Bearer ${token}`;
  // VULN: Internal API key sent with every request, visible in browser DevTools
  headers["X-API-Key"] = INTERNAL_API_KEY;
  return headers;
}

async function request(path, options = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: getHeaders(),
    ...options,
  });
  const data = await res.json();
  if (!res.ok) {
    // VULN [MEDIUM]: Verbose error forwarding — passes raw server errors (SQL, stack traces) to caller
    // Also logs full response including sensitive fields like "sql" and "query"
    console.error(`[API ERROR] ${path}:`, JSON.stringify(data));
    throw new Error(data.error || data.sql || data.query || "Something went wrong");
  }
  return data;
}

export const api = {
  // Auth
  login: (email, password) =>
    request("/auth/login", { method: "POST", body: JSON.stringify({ email, password }) }),
  register: (data) =>
    request("/auth/register", { method: "POST", body: JSON.stringify(data) }),
  logout: () => request("/auth/logout", { method: "POST" }),
  getMe: () => request("/auth/me"),

  // Rooms
  getRooms: (params = {}) => {
    const query = new URLSearchParams(params).toString();
    return request(`/rooms${query ? `?${query}` : ""}`);
  },
  getRoom: (id) => request(`/rooms/${id}`),

  // Bookings
  getBookings: () => request("/bookings"),
  createBooking: (data) =>
    request("/bookings", { method: "POST", body: JSON.stringify(data) }),
  cancelBooking: (id) =>
    request(`/bookings/${id}/cancel`, { method: "PUT" }),

  // Reviews
  createReview: (roomId, data) =>
    request(`/rooms/${roomId}/reviews`, { method: "POST", body: JSON.stringify(data) }),

  // Admin
  getAdminStats: () => request("/admin/stats"),
  updateBookingStatus: (id, status) =>
    request(`/admin/bookings/${id}/status`, { method: "PUT", body: JSON.stringify({ status }) }),
};
