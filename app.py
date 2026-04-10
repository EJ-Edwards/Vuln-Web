"""
Grand Hotel - Hotel Management Booking System API
"""
import os
import sqlite3
import secrets
from datetime import datetime, timedelta
from functools import wraps

from flask import Flask, request, jsonify, g, send_from_directory
from setup_db import init_db, DB_PATH, hash_password, verify_password

app = Flask(__name__, static_folder="frontend/dist", static_url_path="")
app.secret_key = secrets.token_hex(32)

CORS_HEADERS = {
    "Access-Control-Allow-Origin": "http://localhost:5173",
    "Access-Control-Allow-Headers": "Content-Type, Authorization",
    "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
    "Access-Control-Allow-Credentials": "true",
}

# Simple token store (in production, use JWT or Redis)
active_tokens = {}


@app.after_request
def add_cors(response):
    for key, value in CORS_HEADERS.items():
        response.headers[key] = value
    return response


@app.before_request
def handle_options():
    if request.method == "OPTIONS":
        response = jsonify({"ok": True})
        for key, value in CORS_HEADERS.items():
            response.headers[key] = value
        return response, 200


# ─── Database ─────────────────────────────────────────────────────────────────
def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(exc):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def dict_row(row):
    return dict(row) if row else None


def dict_rows(rows):
    return [dict(r) for r in rows]


# ─── Auth helpers ─────────────────────────────────────────────────────────────
def get_current_user():
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return None
    token = auth[7:]
    user_id = active_tokens.get(token)
    if user_id is None:
        return None
    db = get_db()
    user = db.execute("SELECT id, name, email, phone, role, created_at FROM users WHERE id = ?", (user_id,)).fetchone()
    return dict_row(user)


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        user = get_current_user()
        if not user:
            return jsonify({"error": "Authentication required"}), 401
        g.user = user
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        user = get_current_user()
        if not user:
            return jsonify({"error": "Authentication required"}), 401
        if user["role"] != "admin":
            return jsonify({"error": "Admin access required"}), 403
        g.user = user
        return f(*args, **kwargs)
    return decorated


# ─── Auth endpoints ───────────────────────────────────────────────────────────
@app.route("/api/auth/register", methods=["POST"])
def register():
    data = request.get_json()
    name = data.get("name", "").strip()
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")
    phone = data.get("phone", "").strip()

    if not name or not email or not password:
        return jsonify({"error": "Name, email, and password are required"}), 400
    if len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters"}), 400

    db = get_db()
    existing = db.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
    if existing:
        return jsonify({"error": "Email already registered"}), 409

    pw_hash = hash_password(password)
    db.execute(
        "INSERT INTO users (name, email, password_hash, phone, role) VALUES (?, ?, ?, ?, 'guest')",
        (name, email, pw_hash, phone),
    )
    db.commit()
    return jsonify({"message": "Registration successful"}), 201


@app.route("/api/auth/login", methods=["POST"])
def login():
    data = request.get_json()
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")

    db = get_db()
    user = db.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    if not user or not verify_password(password, user["password_hash"]):
        return jsonify({"error": "Invalid email or password"}), 401

    token = secrets.token_hex(32)
    active_tokens[token] = user["id"]

    return jsonify({
        "token": token,
        "user": {
            "id": user["id"],
            "name": user["name"],
            "email": user["email"],
            "phone": user["phone"],
            "role": user["role"],
        },
    })


@app.route("/api/auth/logout", methods=["POST"])
@login_required
def logout():
    auth = request.headers.get("Authorization", "")
    token = auth[7:]
    active_tokens.pop(token, None)
    return jsonify({"message": "Logged out"})


@app.route("/api/auth/me", methods=["GET"])
@login_required
def me():
    return jsonify({"user": g.user})


# ─── Rooms ────────────────────────────────────────────────────────────────────
@app.route("/api/rooms", methods=["GET"])
def get_rooms():
    db = get_db()
    room_type = request.args.get("type")
    min_price = request.args.get("min_price")
    max_price = request.args.get("max_price")
    capacity = request.args.get("capacity")

    query = "SELECT * FROM rooms WHERE available = 1"
    params = []

    if room_type:
        query += " AND type = ?"
        params.append(room_type)
    if min_price:
        query += " AND price_per_night >= ?"
        params.append(float(min_price))
    if max_price:
        query += " AND price_per_night <= ?"
        params.append(float(max_price))
    if capacity:
        query += " AND capacity >= ?"
        params.append(int(capacity))

    query += " ORDER BY price_per_night ASC"
    rooms = db.execute(query, params).fetchall()

    result = []
    for room in rooms:
        r = dict_row(room)
        r["amenities"] = r["amenities"].split(",") if r["amenities"] else []
        avg = db.execute("SELECT AVG(rating) as avg_rating, COUNT(*) as count FROM reviews WHERE room_id = ?", (r["id"],)).fetchone()
        r["avg_rating"] = round(avg["avg_rating"], 1) if avg["avg_rating"] else 0
        r["review_count"] = avg["count"]
        result.append(r)

    return jsonify(result)


@app.route("/api/rooms/<int:room_id>", methods=["GET"])
def get_room(room_id):
    db = get_db()
    room = db.execute("SELECT * FROM rooms WHERE id = ?", (room_id,)).fetchone()
    if not room:
        return jsonify({"error": "Room not found"}), 404

    r = dict_row(room)
    r["amenities"] = r["amenities"].split(",") if r["amenities"] else []

    reviews = db.execute(
        """SELECT r.*, u.name as user_name FROM reviews r
           JOIN users u ON r.user_id = u.id WHERE r.room_id = ? ORDER BY r.created_at DESC""",
        (room_id,),
    ).fetchall()
    r["reviews"] = dict_rows(reviews)

    avg = db.execute("SELECT AVG(rating) as avg_rating, COUNT(*) as count FROM reviews WHERE room_id = ?", (room_id,)).fetchone()
    r["avg_rating"] = round(avg["avg_rating"], 1) if avg["avg_rating"] else 0
    r["review_count"] = avg["count"]

    return jsonify(r)


# ─── Bookings ─────────────────────────────────────────────────────────────────
@app.route("/api/bookings", methods=["GET"])
@login_required
def get_bookings():
    db = get_db()
    if g.user["role"] == "admin":
        bookings = db.execute(
            """SELECT b.*, r.name as room_name, r.type as room_type, r.image_url
               FROM bookings b JOIN rooms r ON b.room_id = r.id ORDER BY b.created_at DESC"""
        ).fetchall()
    else:
        bookings = db.execute(
            """SELECT b.*, r.name as room_name, r.type as room_type, r.image_url
               FROM bookings b JOIN rooms r ON b.room_id = r.id
               WHERE b.user_id = ? ORDER BY b.created_at DESC""",
            (g.user["id"],),
        ).fetchall()
    return jsonify(dict_rows(bookings))


@app.route("/api/bookings", methods=["POST"])
@login_required
def create_booking():
    data = request.get_json()
    room_id = data.get("room_id")
    check_in = data.get("check_in")
    check_out = data.get("check_out")
    num_guests = data.get("num_guests", 1)
    special_requests = data.get("special_requests", "")

    if not room_id or not check_in or not check_out:
        return jsonify({"error": "Room, check-in, and check-out dates are required"}), 400

    try:
        ci = datetime.strptime(check_in, "%Y-%m-%d")
        co = datetime.strptime(check_out, "%Y-%m-%d")
    except ValueError:
        return jsonify({"error": "Invalid date format. Use YYYY-MM-DD"}), 400

    if co <= ci:
        return jsonify({"error": "Check-out must be after check-in"}), 400
    if ci < datetime.now().replace(hour=0, minute=0, second=0, microsecond=0):
        return jsonify({"error": "Check-in date cannot be in the past"}), 400

    db = get_db()
    room = db.execute("SELECT * FROM rooms WHERE id = ? AND available = 1", (room_id,)).fetchone()
    if not room:
        return jsonify({"error": "Room not available"}), 404

    if num_guests > room["capacity"]:
        return jsonify({"error": f"Room capacity is {room['capacity']} guests"}), 400

    # Check for overlapping bookings
    overlap = db.execute(
        """SELECT id FROM bookings WHERE room_id = ? AND status != 'cancelled'
           AND check_in < ? AND check_out > ?""",
        (room_id, check_out, check_in),
    ).fetchone()
    if overlap:
        return jsonify({"error": "Room is already booked for these dates"}), 409

    nights = (co - ci).days
    total_price = round(nights * room["price_per_night"], 2)

    db.execute(
        """INSERT INTO bookings (user_id, room_id, guest_name, guest_email, guest_phone,
           check_in, check_out, num_guests, special_requests, total_price)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (g.user["id"], room_id, g.user["name"], g.user["email"],
         g.user.get("phone", ""), check_in, check_out, num_guests, special_requests, total_price),
    )
    db.commit()

    return jsonify({"message": "Booking confirmed!", "total_price": total_price, "nights": nights}), 201


@app.route("/api/bookings/<int:booking_id>/cancel", methods=["PUT"])
@login_required
def cancel_booking(booking_id):
    db = get_db()
    booking = db.execute("SELECT * FROM bookings WHERE id = ?", (booking_id,)).fetchone()
    if not booking:
        return jsonify({"error": "Booking not found"}), 404
    if booking["user_id"] != g.user["id"] and g.user["role"] != "admin":
        return jsonify({"error": "Not authorized"}), 403
    if booking["status"] == "cancelled":
        return jsonify({"error": "Booking already cancelled"}), 400

    db.execute("UPDATE bookings SET status = 'cancelled' WHERE id = ?", (booking_id,))
    db.commit()
    return jsonify({"message": "Booking cancelled"})


# ─── Reviews ──────────────────────────────────────────────────────────────────
@app.route("/api/rooms/<int:room_id>/reviews", methods=["POST"])
@login_required
def create_review(room_id):
    data = request.get_json()
    rating = data.get("rating")
    comment = data.get("comment", "").strip()

    if not rating or not (1 <= int(rating) <= 5):
        return jsonify({"error": "Rating must be between 1 and 5"}), 400

    db = get_db()
    room = db.execute("SELECT id FROM rooms WHERE id = ?", (room_id,)).fetchone()
    if not room:
        return jsonify({"error": "Room not found"}), 404

    db.execute(
        "INSERT INTO reviews (user_id, room_id, rating, comment) VALUES (?, ?, ?, ?)",
        (g.user["id"], room_id, int(rating), comment),
    )
    db.commit()
    return jsonify({"message": "Review submitted"}), 201


# ─── Admin endpoints ─────────────────────────────────────────────────────────
@app.route("/api/admin/stats", methods=["GET"])
@admin_required
def admin_stats():
    db = get_db()
    total_rooms = db.execute("SELECT COUNT(*) as c FROM rooms").fetchone()["c"]
    total_bookings = db.execute("SELECT COUNT(*) as c FROM bookings WHERE status != 'cancelled'").fetchone()["c"]
    total_revenue = db.execute("SELECT COALESCE(SUM(total_price), 0) as s FROM bookings WHERE status != 'cancelled'").fetchone()["s"]
    total_guests = db.execute("SELECT COUNT(*) as c FROM users WHERE role = 'guest'").fetchone()["c"]
    recent_bookings = db.execute(
        """SELECT b.*, r.name as room_name, u.name as user_name
           FROM bookings b JOIN rooms r ON b.room_id = r.id JOIN users u ON b.user_id = u.id
           ORDER BY b.created_at DESC LIMIT 10"""
    ).fetchall()
    return jsonify({
        "total_rooms": total_rooms,
        "total_bookings": total_bookings,
        "total_revenue": round(total_revenue, 2),
        "total_guests": total_guests,
        "recent_bookings": dict_rows(recent_bookings),
    })


@app.route("/api/admin/bookings/<int:booking_id>/status", methods=["PUT"])
@admin_required
def update_booking_status(booking_id):
    data = request.get_json()
    status = data.get("status")
    if status not in ("confirmed", "checked_in", "checked_out", "cancelled"):
        return jsonify({"error": "Invalid status"}), 400
    db = get_db()
    db.execute("UPDATE bookings SET status = ? WHERE id = ?", (status, booking_id))
    db.commit()
    return jsonify({"message": "Status updated"})


# ─── Serve React app ─────────────────────────────────────────────────────────
@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve_react(path):
    if path and os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    return send_from_directory(app.static_folder, "index.html")


# ─── Init ─────────────────────────────────────────────────────────────────────
if not os.path.exists(DB_PATH):
    init_db()

if __name__ == "__main__":
    app.run(debug=True, port=5000)
