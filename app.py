"""
Grand Hotel - Hotel Management Booking System API
WARNING: This application is INTENTIONALLY VULNERABLE for educational purposes.
"""
import os
import sqlite3
import secrets
import subprocess
import pickle
import base64
import re
import time
import json
import urllib.request
import hmac
import hashlib as stdlib_hashlib
import codecs
from datetime import datetime, timedelta
from functools import wraps
from xml.etree import ElementTree

from flask import Flask, request, jsonify, g, send_from_directory, redirect, make_response
from jinja2 import Template
from setup_db import init_db, DB_PATH, hash_password, verify_password

STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "frontend", "dist")
app = Flask(__name__, static_folder=STATIC_DIR, static_url_path="")
app.secret_key = "super_secret_key_123"  # VULN: Hardcoded weak secret key

CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",  # VULN: Wildcard CORS — allows any origin
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
    # VULN: Mass assignment - server accepts role parameter from user input
    # Exploit: add "role": "admin" to registration JSON to become admin
    role = data.get("role", "guest")

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
        "INSERT INTO users (name, email, password_hash, phone, role) VALUES (?, ?, ?, ?, ?)",
        (name, email, pw_hash, phone, role),
    )
    db.commit()
    return jsonify({"message": "Registration successful"}), 201


@app.route("/api/auth/login", methods=["POST"])
def login():
    data = request.get_json()
    email = data.get("email", "").strip()
    password = data.get("password", "")

    db = get_db()
    # VULN: SQL Injection via string concatenation on email field
    # Bypass: email = admin@grandhotel.com' --   password = anything
    query = f"SELECT * FROM users WHERE email = '{email}'"
    try:
        user = db.execute(query).fetchone()
    except Exception as e:
        # VULN: Leaks SQL query and error details
        return jsonify({"error": str(e), "query": query}), 500

    if not user:
        return jsonify({"error": "Invalid email or password"}), 401

    # Normal password check still works for legitimate logins
    # But SQL injection on email bypasses needing correct email match
    if user["email"].lower() == email.lower():
        if not verify_password(password, user["password_hash"]):
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

    # VULN: Mass assignment — client can override total_price and status
    # Exploit: add "total_price": 0.01 or "status": "checked_out" to request body
    if "total_price" in data:
        total_price = data["total_price"]
    status = data.get("status", "confirmed")

    db.execute(
        """INSERT INTO bookings (user_id, room_id, guest_name, guest_email, guest_phone,
           check_in, check_out, num_guests, special_requests, total_price, status)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (g.user["id"], room_id, g.user["name"], g.user["email"],
         g.user.get("phone", ""), check_in, check_out, num_guests, special_requests, total_price, status),
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


# ══════════════════════════════════════════════════════════════════════════════
# INTENTIONALLY VULNERABLE ENDPOINTS — Educational / Pen-Test Practice Only
# ══════════════════════════════════════════════════════════════════════════════

UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
JWT_SECRET = "secret"  # VULN: Weak/known JWT secret


# --- 1. SQL Injection: Search ---
@app.route("/api/search", methods=["GET"])
def vuln_search():
    q = request.args.get("q", "")
    db = get_db()
    # VULN: SQL injection via string concatenation
    query = f"SELECT id, name, type, price_per_night, image_url FROM rooms WHERE name LIKE '%{q}%' OR description LIKE '%{q}%'"
    try:
        results = db.execute(query).fetchall()
        # VULN: Reflected XSS — query echoed back unsanitized
        return jsonify({"query": q, "results": dict_rows(results)})
    except Exception as e:
        # VULN: Verbose error leaks SQL query
        return jsonify({"query": q, "error": str(e), "sql": query}), 500


# --- 2. SQL Injection: User Lookup ---
@app.route("/api/user/<user_id>", methods=["GET"])
def get_user(user_id):
    db = get_db()
    # VULN: SQL injection via string concatenation on numeric parameter
    query = f"SELECT id, name, email, phone, role FROM users WHERE id = {user_id}"
    try:
        user = db.execute(query).fetchone()
        if not user:
            return jsonify({"error": "User not found"}), 404
        return jsonify(dict_row(user))
    except Exception as e:
        return jsonify({"error": str(e), "sql": query}), 500


# --- 3. Blind SQL Injection: Username Checker ---
@app.route("/api/blind", methods=["GET"])
def blind_sqli():
    username = request.args.get("username", "")
    db = get_db()
    # VULN: Boolean-based blind SQL injection
    query = f"SELECT COUNT(*) as c FROM users WHERE name = '{username}'"
    try:
        result = db.execute(query).fetchone()
        exists = result["c"] > 0
        return jsonify({"exists": exists})
    except:
        return jsonify({"exists": False})


# --- 4. Reflected XSS: 404 page ---
@app.route("/api/404")
def not_found_page():
    path = request.args.get("path", "")
    # VULN: Reflected XSS — user input reflected in HTML without encoding
    html = f"<html><body><h1>404 Not Found</h1><p>The page '{path}' was not found on this server.</p></body></html>"
    return html, 404, {"Content-Type": "text/html"}


# --- 5. Stored XSS: Guestbook ---
@app.route("/api/guestbook", methods=["GET"])
def get_guestbook():
    db = get_db()
    entries = db.execute("SELECT * FROM guestbook ORDER BY created_at DESC").fetchall()
    return jsonify(dict_rows(entries))


@app.route("/api/guestbook", methods=["POST"])
def post_guestbook():
    data = request.get_json()
    name = data.get("name", "")
    message = data.get("message", "")
    if not name or not message:
        return jsonify({"error": "Name and message are required"}), 400
    db = get_db()
    # VULN: Stored XSS — no input sanitization, messages rendered raw
    db.execute("INSERT INTO guestbook (name, message) VALUES (?, ?)", (name, message))
    db.commit()
    return jsonify({"message": "Entry added"}), 201


# --- 6. Command Injection: Ping Utility ---
@app.route("/api/ping", methods=["POST"])
def ping():
    data = request.get_json()
    host = data.get("host", "")
    if not host:
        return jsonify({"error": "Host is required"}), 400
    # VULN: Command injection — user input passed directly to OS shell
    # Exploit: host = "127.0.0.1; whoami" or "127.0.0.1 | cat /etc/passwd"
    try:
        cmd = f"ping -n 2 {host}" if os.name == "nt" else f"ping -c 2 {host}"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
        return jsonify({"command": cmd, "output": result.stdout + result.stderr})
    except subprocess.TimeoutExpired:
        return jsonify({"output": "Command timed out"}), 408


# --- 7. Unrestricted File Upload ---
@app.route("/api/upload", methods=["POST"])
def upload_file():
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400
    f = request.files["file"]
    # VULN: No file type validation, no filename sanitization
    filepath = os.path.join(UPLOAD_FOLDER, f.filename)
    f.save(filepath)
    return jsonify({"message": "File uploaded", "path": f"/uploads/{f.filename}"}), 201


@app.route("/uploads/<path:filename>")
def serve_upload(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)


# --- 8. IDOR: Notes ---
@app.route("/api/notes", methods=["GET"])
@login_required
def get_my_notes():
    db = get_db()
    notes = db.execute("SELECT * FROM notes WHERE user_id = ?", (g.user["id"],)).fetchall()
    return jsonify(dict_rows(notes))


@app.route("/api/notes/<int:note_id>", methods=["GET"])
@login_required
def get_note(note_id):
    db = get_db()
    # VULN: IDOR — no check that the note belongs to the current user
    # Exploit: change note_id to access other users' private notes
    note = db.execute("SELECT * FROM notes WHERE id = ?", (note_id,)).fetchone()
    if not note:
        return jsonify({"error": "Note not found"}), 404
    return jsonify(dict_row(note))


# --- 9. Path Traversal: File Download ---
@app.route("/api/download", methods=["GET"])
def download_file():
    filename = request.args.get("file", "")
    if not filename:
        return jsonify({"error": "Filename required"}), 400
    # VULN: Path traversal — no sanitization allows ../../../etc/passwd
    files_dir = os.path.join(os.path.dirname(__file__), "files")
    filepath = os.path.join(files_dir, filename)
    try:
        with open(filepath, "r") as f:
            content = f.read()
        return jsonify({"filename": filename, "content": content})
    except FileNotFoundError:
        return jsonify({"error": "File not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# --- 10. Open Redirect ---
@app.route("/api/redirect", methods=["GET"])
def open_redirect():
    url = request.args.get("url", "")
    if not url:
        return jsonify({"error": "URL required"}), 400
    # VULN: No validation of redirect target — can redirect to malicious sites
    return redirect(url)


# --- 11. SSTI: Server-Side Template Injection ---
@app.route("/api/ssti", methods=["POST"])
def ssti():
    data = request.get_json()
    name = data.get("name", "World")
    # VULN: User input injected directly into Jinja2 template string
    # Exploit: name = "{{7*7}}" or "{{config.items()}}"
    template = Template(f"Hello {name}! Welcome to Grand Hotel.")
    return jsonify({"greeting": template.render()})


# --- 12. Insecure Deserialization ---
@app.route("/api/deserialize", methods=["POST"])
def deserialize():
    data = request.get_json()
    payload = data.get("data", "")
    if not payload:
        return jsonify({"error": "Data required"}), 400
    # VULN: Pickle deserialization of user-controlled data — RCE possible
    try:
        obj = pickle.loads(base64.b64decode(payload))
        return jsonify({"result": str(obj)})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


# --- 13. XXE: XML External Entity ---
@app.route("/api/xxe", methods=["POST"])
def xxe():
    xml_data = request.data.decode("utf-8")
    if not xml_data:
        return jsonify({"error": "XML data required"}), 400
    # VULN: XML parsing without disabling external entities
    try:
        root = ElementTree.fromstring(xml_data)
        result = {child.tag: child.text for child in root}
        return jsonify({"parsed": result})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


# --- 14. Broken Access Control: Admin Users (no auth) ---
@app.route("/api/admin/users", methods=["GET"])
def admin_users():
    # VULN: No authentication or role check — anyone can list all users
    db = get_db()
    users = db.execute("SELECT id, name, email, phone, role, password_hash, created_at FROM users").fetchall()
    return jsonify(dict_rows(users))


# --- 15. Information Disclosure: API Users ---
@app.route("/api/users", methods=["GET"])
def list_users():
    # VULN: Unauthenticated endpoint leaking all user data including password hashes
    db = get_db()
    users = db.execute("SELECT * FROM users").fetchall()
    return jsonify(dict_rows(users))


# --- 16. SSRF: Server-Side Request Forgery ---
@app.route("/api/fetch", methods=["POST"])
def fetch_url():
    data = request.get_json()
    url = data.get("url", "")
    if not url:
        return jsonify({"error": "URL required"}), 400
    # VULN: Server fetches any URL — can reach internal services, cloud metadata
    # Exploit: url = "http://169.254.169.254/latest/meta-data/" or "file:///etc/passwd"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "GrandHotel/1.0"})
        response = urllib.request.urlopen(req, timeout=5)
        content = response.read().decode("utf-8", errors="replace")[:5000]
        return jsonify({"url": url, "status": response.status, "content": content})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# --- 17. JWT Token Forgery ---
def jwt_base64_encode(data):
    return base64.urlsafe_b64encode(json.dumps(data).encode()).rstrip(b"=").decode()


def jwt_base64_decode(data):
    padding = 4 - len(data) % 4
    data += "=" * padding
    return json.loads(base64.urlsafe_b64decode(data))


@app.route("/api/jwt/generate", methods=["POST"])
def jwt_generate():
    data = request.get_json()
    username = data.get("username", "guest")
    role = data.get("role", "user")
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {"sub": username, "role": role, "iat": int(time.time())}
    header_b64 = jwt_base64_encode(header)
    payload_b64 = jwt_base64_encode(payload)
    # VULN: Weak/known secret "secret"
    signature = hmac.new(JWT_SECRET.encode(), f"{header_b64}.{payload_b64}".encode(), stdlib_hashlib.sha256).digest()
    sig_b64 = base64.urlsafe_b64encode(signature).rstrip(b"=").decode()
    token = f"{header_b64}.{payload_b64}.{sig_b64}"
    return jsonify({"token": token})


@app.route("/api/jwt/verify", methods=["POST"])
def jwt_verify():
    data = request.get_json()
    token = data.get("token", "")
    parts = token.split(".")
    if len(parts) != 3:
        return jsonify({"error": "Invalid JWT format"}), 400
    try:
        header = jwt_base64_decode(parts[0])
        payload = jwt_base64_decode(parts[1])
        # VULN: Accepts "none" algorithm — skip signature verification entirely
        if header.get("alg") == "none":
            return jsonify({"valid": True, "payload": payload, "warning": "No signature verification"})
        expected_sig = hmac.new(JWT_SECRET.encode(), f"{parts[0]}.{parts[1]}".encode(), stdlib_hashlib.sha256).digest()
        expected_b64 = base64.urlsafe_b64encode(expected_sig).rstrip(b"=").decode()
        if parts[2] == expected_b64:
            return jsonify({"valid": True, "payload": payload})
        return jsonify({"valid": False, "error": "Invalid signature"}), 401
    except Exception as e:
        return jsonify({"error": str(e)}), 400


# --- 18. CRLF / HTTP Header Injection ---
@app.route("/api/header", methods=["GET"])
def header_injection():
    lang = request.args.get("lang", "en")
    response = make_response(jsonify({"message": f"Language set to {lang}"}))
    # VULN: User input injected into response header — CRLF injection possible
    response.headers["X-Custom-Lang"] = lang
    return response


# --- 19. Weak Cryptography ---
@app.route("/api/crypto/encrypt", methods=["POST"])
def crypto_encrypt():
    data = request.get_json()
    plaintext = data.get("text", "")
    method = data.get("method", "base64")

    if method == "base64":
        # VULN: base64 is encoding, not encryption
        result = base64.b64encode(plaintext.encode()).decode()
    elif method == "md5":
        # VULN: MD5 is broken for cryptographic purposes
        result = stdlib_hashlib.md5(plaintext.encode()).hexdigest()
    elif method == "rot13":
        # VULN: ROT13 is trivially reversible
        result = codecs.encode(plaintext, "rot13")
    elif method == "xor":
        # VULN: Single-byte XOR key — trivially broken
        key = 42
        result = base64.b64encode(bytes(ord(c) ^ key for c in plaintext)).decode()
    else:
        return jsonify({"error": "Unknown method. Use: base64, md5, rot13, xor"}), 400

    return jsonify({"method": method, "result": result, "label": "Military Grade AES-256 Encryption"})


# --- 20. Race Condition: Coupon Redemption ---
@app.route("/api/coupon/redeem", methods=["POST"])
def redeem_coupon():
    data = request.get_json()
    code = data.get("code", "")
    db = get_db()
    coupon = db.execute("SELECT * FROM coupons WHERE code = ? AND active = 1", (code,)).fetchone()
    if not coupon:
        return jsonify({"error": "Invalid or inactive coupon"}), 404

    # VULN: Race condition — check-then-act with processing delay
    # Exploit: send many concurrent requests to redeem one-time coupon multiple times
    if coupon["times_used"] >= coupon["max_uses"]:
        return jsonify({"error": "Coupon already fully redeemed"}), 400

    time.sleep(0.5)  # Simulated processing delay widens the race window

    db.execute("UPDATE coupons SET times_used = times_used + 1 WHERE code = ?", (code,))
    db.commit()
    return jsonify({"message": f"Coupon redeemed! Discount: ${coupon['discount']}", "discount": coupon["discount"]})


# --- 21. Host Header Injection: Password Reset ---
@app.route("/api/reset", methods=["POST"])
def password_reset():
    data = request.get_json()
    email = data.get("email", "")
    db = get_db()
    user = db.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    if not user:
        return jsonify({"message": "If the email exists, a reset link has been sent."})

    token = secrets.token_hex(16)
    db.execute("INSERT INTO password_reset_tokens (user_id, token) VALUES (?, ?)", (user["id"], token))
    db.commit()

    # VULN: Reset link built from Host header — attacker can inject malicious host
    host = request.headers.get("Host", "localhost:5000")
    reset_link = f"http://{host}/reset?token={token}"

    return jsonify({
        "message": "If the email exists, a reset link has been sent.",
        "debug_link": reset_link,   # VULN: Exposes reset link in response
        "debug_token": token,       # VULN: Exposes token in response
    })


# --- 22. ReDoS: Regular Expression DoS ---
@app.route("/api/regex", methods=["POST"])
def regex_test():
    data = request.get_json()
    pattern = data.get("pattern", "")
    test_string = data.get("text", "")

    # VULN: User-controlled regex can cause catastrophic backtracking
    # Exploit: pattern = "^(a+)+$", text = "aaaaaaaaaaaaaaaaaaaaaaaa!"
    try:
        match = re.search(pattern, test_string)
        return jsonify({
            "pattern": pattern,
            "text": test_string,
            "match": match.group() if match else None,
            "matched": bool(match),
        })
    except re.error as e:
        return jsonify({"error": str(e)}), 400


# --- 23. Products with Internal Notes Exposed ---
@app.route("/api/products", methods=["GET"])
def get_products():
    db = get_db()
    # VULN: Internal notes exposed to all unauthenticated users
    products = db.execute("SELECT * FROM products").fetchall()
    return jsonify(dict_rows(products))


@app.route("/api/products/<int:product_id>", methods=["GET"])
def get_product(product_id):
    db = get_db()
    product = db.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
    if not product:
        return jsonify({"error": "Product not found"}), 404
    return jsonify(dict_row(product))


# --- 24. robots.txt Leaking Paths ---
@app.route("/robots.txt")
def robots():
    # VULN: Discloses hidden/sensitive paths
    content = """User-agent: *
Disallow: /api/admin/
Disallow: /api/users
Disallow: /uploads/
Disallow: /api/debug/
Disallow: /api/backup/
Disallow: /files/
"""
    return content, 200, {"Content-Type": "text/plain"}


# --- 25. Debug Info Endpoint ---
@app.route("/api/debug", methods=["GET"])
def debug_info():
    # VULN: Exposes server internals — Python version, secret key, env vars
    import sys
    return jsonify({
        "python_version": sys.version,
        "flask_version": "3.0.0",
        "debug_mode": app.debug,
        "secret_key": app.secret_key,
        "database": DB_PATH,
        "cwd": os.getcwd(),
    })


# ══════════════════════════════════════════════════════════════════════════════
# SERVER-RENDERED VULNERABLE HTML PAGES — These are what scanners crawl
# ══════════════════════════════════════════════════════════════════════════════

VULN_PAGE_STYLE = """
<style>
  body { font-family: -apple-system, 'Segoe UI', Roboto, sans-serif; margin: 0; background: #0a0a0a; color: #e0e0e0; }
  .nav { background: #111; padding: 12px 24px; display: flex; gap: 16px; flex-wrap: wrap; align-items: center; border-bottom: 1px solid #333; }
  .nav a { color: #4fc3f7; text-decoration: none; font-size: 14px; }
  .nav a:hover { text-decoration: underline; }
  .nav .brand { color: #ffd54f; font-weight: bold; font-size: 16px; margin-right: 20px; }
  .container { max-width: 900px; margin: 30px auto; padding: 0 20px; }
  h1 { color: #ffd54f; } h2 { color: #4fc3f7; }
  form { background: #1a1a1a; padding: 20px; border-radius: 8px; margin: 16px 0; border: 1px solid #333; }
  input, textarea, select { width: 100%; padding: 10px; margin: 8px 0 16px; background: #222; color: #e0e0e0; border: 1px solid #444; border-radius: 4px; box-sizing: border-box; }
  button, .btn { background: #4fc3f7; color: #000; padding: 10px 24px; border: none; border-radius: 4px; cursor: pointer; font-weight: bold; text-decoration: none; display: inline-block; }
  button:hover, .btn:hover { background: #039be5; }
  .result { background: #1a2a1a; padding: 16px; border-radius: 8px; margin: 16px 0; border: 1px solid #2e7d32; white-space: pre-wrap; word-break: break-all; }
  .error { background: #2a1a1a; border-color: #c62828; }
  table { width: 100%; border-collapse: collapse; margin: 16px 0; }
  th, td { padding: 10px; text-align: left; border-bottom: 1px solid #333; }
  th { background: #1a1a1a; color: #ffd54f; }
  .warning { background: #2a2000; padding: 12px; border-radius: 4px; border: 1px solid #f9a825; margin: 16px 0; color: #ffd54f; }
  .guestbook-entry { background: #1a1a1a; padding: 12px; border-radius: 8px; margin: 8px 0; border: 1px solid #333; }
  pre { background: #111; padding: 12px; border-radius: 4px; overflow-x: auto; }
</style>
"""

VULN_NAV = """
<div class="nav">
  <a href="/" class="brand">🏨 Grand Hotel</a>
  <a href="/vuln">Vuln Hub</a>
  <a href="/vuln/login">SQL Login</a>
  <a href="/vuln/search">Search/XSS</a>
  <a href="/vuln/guestbook">Guestbook</a>
  <a href="/vuln/ping">Ping</a>
  <a href="/vuln/upload">Upload</a>
  <a href="/vuln/download">Download</a>
  <a href="/vuln/users">Users</a>
  <a href="/vuln/profile">Profile</a>
  <a href="/vuln/ssti">SSTI</a>
  <a href="/vuln/fetch">SSRF</a>
  <a href="/vuln/crypto">Crypto</a>
  <a href="/vuln/redirect?url=/">Redirect</a>
</div>
"""


def vuln_page(title, body):
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>{title} - Grand Hotel</title>{VULN_PAGE_STYLE}</head>
<body>{VULN_NAV}<div class="container">{body}</div></body></html>"""


# --- Vuln Hub Index ---
@app.route("/vuln")
def vuln_index():
    body = """
    <h1>🔓 Vulnerability Testing Hub</h1>
    <p class="warning">⚠️ This section is intentionally vulnerable for educational &amp; penetration testing purposes.</p>
    <h2>Available Vulnerable Pages</h2>
    <table>
      <tr><th>#</th><th>Vulnerability</th><th>Page</th><th>Severity</th></tr>
      <tr><td>1</td><td>SQL Injection (Auth Bypass)</td><td><a href="/vuln/login">Login</a></td><td>🔴 HIGH</td></tr>
      <tr><td>2</td><td>SQL Injection (UNION) + Reflected XSS</td><td><a href="/vuln/search">Search</a></td><td>🔴 HIGH</td></tr>
      <tr><td>3</td><td>Stored XSS</td><td><a href="/vuln/guestbook">Guestbook</a></td><td>🔴 HIGH</td></tr>
      <tr><td>4</td><td>Command Injection</td><td><a href="/vuln/ping">Ping</a></td><td>🔴 HIGH</td></tr>
      <tr><td>5</td><td>Unrestricted File Upload</td><td><a href="/vuln/upload">Upload</a></td><td>🔴 HIGH</td></tr>
      <tr><td>6</td><td>Path Traversal</td><td><a href="/vuln/download">Download</a></td><td>🔴 HIGH</td></tr>
      <tr><td>7</td><td>Information Disclosure</td><td><a href="/vuln/users">Users</a></td><td>🟡 MEDIUM</td></tr>
      <tr><td>8</td><td>Stored XSS (Profile Bio)</td><td><a href="/vuln/profile">Profile</a></td><td>🔴 HIGH</td></tr>
      <tr><td>9</td><td>SSTI (Template Injection)</td><td><a href="/vuln/ssti">SSTI</a></td><td>🔴 HIGH</td></tr>
      <tr><td>10</td><td>SSRF (Server-Side Request Forgery)</td><td><a href="/vuln/fetch">URL Fetcher</a></td><td>🔴 CRITICAL</td></tr>
      <tr><td>11</td><td>Weak Cryptography</td><td><a href="/vuln/crypto">Crypto Vault</a></td><td>🟡 MEDIUM</td></tr>
      <tr><td>12</td><td>Open Redirect</td><td><a href="/vuln/redirect?url=https://evil.com">Redirect</a></td><td>🟡 LOW</td></tr>
      <tr><td>13</td><td>CSRF (No Token)</td><td><a href="/vuln/profile">Profile Update</a></td><td>🟡 MEDIUM</td></tr>
      <tr><td>14</td><td>IDOR</td><td><a href="/vuln/notes">Notes</a></td><td>🟡 MEDIUM</td></tr>
      <tr><td>15</td><td>Blind SQL Injection</td><td><a href="/vuln/blind">Username Check</a></td><td>🔴 HIGH</td></tr>
    </table>
    """
    return vuln_page("Vulnerability Hub", body)


# --- 1. SQL Injection Login Page ---
@app.route("/vuln/login", methods=["GET", "POST"])
def vuln_login():
    result = ""
    if request.method == "POST":
        email = request.form.get("email", "")
        password = request.form.get("password", "")
        db = get_db()
        # VULN: SQL Injection via string concatenation
        query = f"SELECT * FROM users WHERE email = '{email}' AND password_hash = '{password}'"
        try:
            user = db.execute(query).fetchone()
            if user:
                result = f'<div class="result">✅ Login successful!<br>Welcome, {user["name"]}!<br>Role: {user["role"]}<br>Email: {user["email"]}</div>'
            else:
                result = '<div class="result error">❌ Invalid credentials</div>'
        except Exception as e:
            result = f'<div class="result error">❌ SQL Error: {e}<br><br>Query: {query}</div>'

    body = f"""
    <h1>🔐 Login</h1>
    <p class="warning">💡 Hint: Try <code>' OR '1'='1' --</code> in the email field</p>
    <form method="POST" action="/vuln/login">
      <label>Email</label>
      <input type="text" name="email" placeholder="admin@grandhotel.com" autocomplete="off">
      <label>Password</label>
      <input type="text" name="password" placeholder="password" autocomplete="off">
      <button type="submit">Login</button>
    </form>
    {result}
    """
    return vuln_page("SQL Injection Login", body)


# --- 2. Search with SQL Injection + Reflected XSS ---
@app.route("/vuln/search")
def vuln_search_page():
    q = request.args.get("q", "")
    result = ""
    if q:
        db = get_db()
        # VULN: SQL Injection + Reflected XSS — query echoed in HTML unescaped
        query = f"SELECT id, name, type, price_per_night FROM rooms WHERE name LIKE '%{q}%' OR description LIKE '%{q}%'"
        try:
            rows = db.execute(query).fetchall()
            result = f'<h2>Results for: {q}</h2>'  # VULN: Reflected XSS
            if rows:
                result += "<table><tr><th>ID</th><th>Name</th><th>Type</th><th>Price</th></tr>"
                for r in rows:
                    result += f"<tr><td>{r['id']}</td><td>{r['name']}</td><td>{r['type']}</td><td>${r['price_per_night']}</td></tr>"
                result += "</table>"
            else:
                result += '<p>No rooms found.</p>'
        except Exception as e:
            result = f'<div class="result error">SQL Error: {e}<br>Query: {query}</div>'

    body = f"""
    <h1>🔍 Room Search</h1>
    <p class="warning">💡 Try XSS: <code>&lt;script&gt;alert('XSS')&lt;/script&gt;</code> or SQLi: <code>' UNION SELECT 1,email,password_hash,phone FROM users--</code></p>
    <form method="GET" action="/vuln/search">
      <label>Search Rooms</label>
      <input type="text" name="q" value="{q}" placeholder="Search rooms..." autocomplete="off">
      <button type="submit">Search</button>
    </form>
    {result}
    """
    return vuln_page("Search (SQLi + XSS)", body)


# --- 3. Guestbook with Stored XSS ---
@app.route("/vuln/guestbook", methods=["GET", "POST"])
def vuln_guestbook():
    db = get_db()
    if request.method == "POST":
        name = request.form.get("name", "")
        message = request.form.get("message", "")
        if name and message:
            # VULN: Stored XSS — no sanitization
            db.execute("INSERT INTO guestbook (name, message) VALUES (?, ?)", (name, message))
            db.commit()

    entries = db.execute("SELECT * FROM guestbook ORDER BY created_at DESC").fetchall()
    entries_html = ""
    for e in entries:
        # VULN: Stored XSS — raw HTML output
        entries_html += f'<div class="guestbook-entry"><strong>{e["name"]}</strong><br>{e["message"]}<br><small>{e["created_at"]}</small></div>'

    body = f"""
    <h1>📝 Guestbook</h1>
    <p class="warning">💡 Try: <code>&lt;script&gt;alert('Stored XSS')&lt;/script&gt;</code> or <code>&lt;img src=x onerror=alert('XSS')&gt;</code></p>
    <form method="POST" action="/vuln/guestbook">
      <label>Your Name</label>
      <input type="text" name="name" placeholder="Enter your name" autocomplete="off">
      <label>Message</label>
      <textarea name="message" rows="3" placeholder="Leave a message..."></textarea>
      <button type="submit">Post Message</button>
    </form>
    <h2>Messages</h2>
    {entries_html}
    """
    return vuln_page("Guestbook (Stored XSS)", body)


# --- 4. Command Injection Ping ---
@app.route("/vuln/ping", methods=["GET", "POST"])
def vuln_ping_page():
    result = ""
    if request.method == "POST":
        host = request.form.get("host", "")
        if host:
            # VULN: Command injection — user input passed to shell
            cmd = f"ping -n 2 {host}" if os.name == "nt" else f"ping -c 2 {host}"
            try:
                output = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
                result = f'<div class="result"><strong>Command:</strong> {cmd}<br><br><pre>{output.stdout}{output.stderr}</pre></div>'
            except subprocess.TimeoutExpired:
                result = '<div class="result error">Command timed out</div>'

    body = f"""
    <h1>🌐 Network Ping Utility</h1>
    <p class="warning">💡 Try: <code>127.0.0.1 &amp; whoami</code> or <code>127.0.0.1 | dir</code></p>
    <form method="POST" action="/vuln/ping">
      <label>Host / IP Address</label>
      <input type="text" name="host" placeholder="127.0.0.1" autocomplete="off">
      <button type="submit">Ping</button>
    </form>
    {result}
    """
    return vuln_page("Command Injection (Ping)", body)


# --- 5. Unrestricted File Upload ---
@app.route("/vuln/upload", methods=["GET", "POST"])
def vuln_upload_page():
    result = ""
    if request.method == "POST":
        if "file" in request.files:
            f = request.files["file"]
            if f.filename:
                # VULN: No file type validation, no filename sanitization
                filepath = os.path.join(UPLOAD_FOLDER, f.filename)
                f.save(filepath)
                result = f'<div class="result">✅ File uploaded: <a href="/uploads/{f.filename}">{f.filename}</a></div>'

    # List uploaded files
    files_html = ""
    if os.path.exists(UPLOAD_FOLDER):
        files = os.listdir(UPLOAD_FOLDER)
        if files:
            files_html = "<h2>Uploaded Files</h2><ul>"
            for fn in files:
                files_html += f'<li><a href="/uploads/{fn}">{fn}</a></li>'
            files_html += "</ul>"

    body = f"""
    <h1>📁 File Upload</h1>
    <p class="warning">💡 No file type restrictions! Try uploading .php, .html, .py, .exe files</p>
    <form method="POST" action="/vuln/upload" enctype="multipart/form-data">
      <label>Choose File</label>
      <input type="file" name="file">
      <button type="submit">Upload</button>
    </form>
    {result}
    {files_html}
    """
    return vuln_page("Unrestricted File Upload", body)


# --- 6. Path Traversal Download ---
@app.route("/vuln/download", methods=["GET"])
def vuln_download_page():
    filename = request.args.get("file", "")
    result = ""
    if filename:
        # VULN: Path traversal — no sanitization
        files_dir = os.path.join(os.path.dirname(__file__), "files")
        filepath = os.path.join(files_dir, filename)
        try:
            with open(filepath, "r") as f:
                content = f.read()
            result = f'<div class="result"><strong>File: {filename}</strong><br><pre>{content}</pre></div>'
        except FileNotFoundError:
            result = f'<div class="result error">File not found: {filename}</div>'
        except Exception as e:
            result = f'<div class="result error">Error: {e}</div>'

    body = f"""
    <h1>📥 File Download</h1>
    <p class="warning">💡 Try: <code>../app.py</code> or <code>../setup_db.py</code> or <code>../../../../etc/passwd</code></p>
    <form method="GET" action="/vuln/download">
      <label>Filename</label>
      <input type="text" name="file" value="{filename}" placeholder="readme.txt" autocomplete="off">
      <button type="submit">Download</button>
    </form>
    <p>Available files: <a href="/vuln/download?file=readme.txt">readme.txt</a> | <a href="/vuln/download?file=report.txt">report.txt</a></p>
    {result}
    """
    return vuln_page("Path Traversal (Download)", body)


# --- 7. Information Disclosure: Users ---
@app.route("/vuln/users")
def vuln_users_page():
    db = get_db()
    # VULN: Unauthenticated user data with password hashes
    users = db.execute("SELECT id, name, email, phone, role, password_hash, created_at FROM users").fetchall()
    rows_html = ""
    for u in users:
        rows_html += f"<tr><td>{u['id']}</td><td>{u['name']}</td><td>{u['email']}</td><td>{u['role']}</td><td><code>{u['password_hash'][:40]}...</code></td></tr>"

    body = f"""
    <h1>👥 User Directory</h1>
    <p class="warning">⚠️ This page exposes all user data including password hashes — no authentication required!</p>
    <table>
      <tr><th>ID</th><th>Name</th><th>Email</th><th>Role</th><th>Password Hash</th></tr>
      {rows_html}
    </table>
    """
    return vuln_page("Information Disclosure (Users)", body)


# --- 8. Stored XSS + CSRF: Profile ---
@app.route("/vuln/profile", methods=["GET", "POST"])
def vuln_profile():
    db = get_db()
    result = ""
    if request.method == "POST":
        # VULN: CSRF — no token required. Also stored XSS via bio field.
        name = request.form.get("name", "")
        bio = request.form.get("bio", "")
        password = request.form.get("new_password", "")
        result = f'<div class="result">✅ Profile updated!<br><strong>Name:</strong> {name}<br><strong>Bio:</strong> {bio}</div>'
        if password:
            # VULN: No old password required for password change
            result += f'<div class="result">🔑 Password changed (no old password required!)</div>'

    body = f"""
    <h1>👤 My Profile</h1>
    <p class="warning">💡 No CSRF token! Bio field has stored XSS. Password change requires no old password.</p>
    <form method="POST" action="/vuln/profile">
      <label>Display Name</label>
      <input type="text" name="name" placeholder="Your name" autocomplete="off">
      <label>Bio (supports HTML!)</label>
      <textarea name="bio" rows="3" placeholder="Tell us about yourself... try <img src=x onerror=alert(1)>"></textarea>
      <label>New Password (no old password needed!)</label>
      <input type="text" name="new_password" placeholder="New password" autocomplete="off">
      <button type="submit">Update Profile</button>
    </form>
    {result}
    """
    return vuln_page("Profile (XSS + CSRF)", body)


# --- 9. SSTI Page ---
@app.route("/vuln/ssti", methods=["GET", "POST"])
def vuln_ssti_page():
    result = ""
    if request.method == "POST":
        name = request.form.get("name", "World")
        # VULN: Server-Side Template Injection
        try:
            template = Template(f"Hello {name}! Welcome to Grand Hotel.")
            rendered = template.render()
            result = f'<div class="result">{rendered}</div>'
        except Exception as e:
            result = f'<div class="result error">Error: {e}</div>'

    body = f"""
    <h1>🎄 Greeting Card Generator</h1>
    <p class="warning">💡 Try: <code>{{{{7*7}}}}</code> or <code>{{{{config.items()}}}}</code> or <code>{{{{self.__init__.__globals__}}}}</code></p>
    <form method="POST" action="/vuln/ssti">
      <label>Your Name</label>
      <input type="text" name="name" placeholder="Enter your name" autocomplete="off">
      <button type="submit">Generate Greeting</button>
    </form>
    {result}
    """
    return vuln_page("SSTI (Template Injection)", body)


# --- 10. SSRF Page ---
@app.route("/vuln/fetch", methods=["GET", "POST"])
def vuln_fetch_page():
    result = ""
    if request.method == "POST":
        url = request.form.get("url", "")
        if url:
            # VULN: SSRF — server fetches any URL
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "GrandHotel/1.0"})
                response = urllib.request.urlopen(req, timeout=5)
                content = response.read().decode("utf-8", errors="replace")[:5000]
                result = f'<div class="result"><strong>URL:</strong> {url}<br><strong>Status:</strong> {response.status}<br><pre>{content}</pre></div>'
            except Exception as e:
                result = f'<div class="result error">Error fetching URL: {e}</div>'

    body = f"""
    <h1>🌍 URL Fetcher</h1>
    <p class="warning">💡 Try: <code>http://169.254.169.254/latest/meta-data/</code> or <code>file:///etc/passwd</code></p>
    <form method="POST" action="/vuln/fetch">
      <label>URL to Fetch</label>
      <input type="text" name="url" placeholder="https://example.com" autocomplete="off">
      <button type="submit">Fetch</button>
    </form>
    {result}
    """
    return vuln_page("SSRF (URL Fetcher)", body)


# --- 11. Weak Crypto Page ---
@app.route("/vuln/crypto", methods=["GET", "POST"])
def vuln_crypto_page():
    result = ""
    if request.method == "POST":
        text = request.form.get("text", "")
        method = request.form.get("method", "base64")
        if text:
            if method == "base64":
                encrypted = base64.b64encode(text.encode()).decode()
            elif method == "md5":
                encrypted = stdlib_hashlib.md5(text.encode()).hexdigest()
            elif method == "rot13":
                encrypted = codecs.encode(text, "rot13")
            elif method == "xor":
                encrypted = base64.b64encode(bytes(ord(c) ^ 42 for c in text)).decode()
            else:
                encrypted = text
            result = f'<div class="result"><strong>Method:</strong> {method}<br><strong>Input:</strong> {text}<br><strong>"Encrypted":</strong> <code>{encrypted}</code></div>'

    body = f"""
    <h1>🔐 Military-Grade Crypto Vault™</h1>
    <p class="warning">💡 "Military grade" = base64 / md5 / rot13 / single-byte XOR. All trivially broken.</p>
    <form method="POST" action="/vuln/crypto">
      <label>Text to Encrypt</label>
      <input type="text" name="text" placeholder="Enter secret text" autocomplete="off">
      <label>Encryption Method</label>
      <select name="method">
        <option value="base64">AES-256 (actually Base64)</option>
        <option value="md5">SHA-512 (actually MD5)</option>
        <option value="rot13">RSA-4096 (actually ROT13)</option>
        <option value="xor">Quantum Encryption (actually XOR with key=42)</option>
      </select>
      <button type="submit">Encrypt</button>
    </form>
    {result}
    """
    return vuln_page("Weak Cryptography", body)


# --- 12. Open Redirect Page ---
@app.route("/vuln/redirect")
def vuln_redirect_page():
    url = request.args.get("url", "")
    if url and url != "/":
        # VULN: Open redirect — no validation
        return redirect(url)

    body = """
    <h1>🔗 URL Redirect Service</h1>
    <p class="warning">💡 No URL validation! Try: <code>/vuln/redirect?url=https://evil.com</code></p>
    <form method="GET" action="/vuln/redirect">
      <label>Redirect URL</label>
      <input type="text" name="url" placeholder="https://example.com" autocomplete="off">
      <button type="submit">Redirect</button>
    </form>
    <p>Examples:</p>
    <ul>
      <li><a href="/vuln/redirect?url=https://google.com">/vuln/redirect?url=https://google.com</a></li>
      <li><a href="/vuln/redirect?url=javascript:alert(1)">/vuln/redirect?url=javascript:alert(1)</a></li>
    </ul>
    """
    return vuln_page("Open Redirect", body)


# --- 13. IDOR Notes Page ---
@app.route("/vuln/notes")
def vuln_notes_page():
    note_id = request.args.get("id", "")
    result = ""
    if note_id:
        db = get_db()
        # VULN: IDOR — no auth, anyone can read any note by ID
        note = db.execute("SELECT n.*, u.name as author FROM notes n JOIN users u ON n.user_id = u.id WHERE n.id = ?", (note_id,)).fetchone()
        if note:
            result = f'<div class="result"><strong>{note["title"]}</strong> (by {note["author"]})<br><br>{note["content"]}</div>'
        else:
            result = '<div class="result error">Note not found</div>'

    all_ids = ""
    db = get_db()
    notes = db.execute("SELECT id, title FROM notes").fetchall()
    for n in notes:
        all_ids += f'<li><a href="/vuln/notes?id={n["id"]}">{n["title"]} (ID: {n["id"]})</a></li>'

    body = f"""
    <h1>📒 Notes</h1>
    <p class="warning">💡 IDOR — change the <code>id</code> parameter to read other users' private notes!</p>
    <form method="GET" action="/vuln/notes">
      <label>Note ID</label>
      <input type="text" name="id" value="{note_id}" placeholder="1" autocomplete="off">
      <button type="submit">View Note</button>
    </form>
    {result}
    <h2>All Notes</h2>
    <ul>{all_ids}</ul>
    """
    return vuln_page("IDOR (Notes)", body)


# --- 14. Blind SQL Injection Page ---
@app.route("/vuln/blind", methods=["GET"])
def vuln_blind_page():
    username = request.args.get("username", "")
    result = ""
    if username:
        db = get_db()
        # VULN: Blind SQL injection
        query = f"SELECT COUNT(*) as c FROM users WHERE name = '{username}'"
        try:
            row = db.execute(query).fetchone()
            exists = row["c"] > 0
            result = f'<div class="result">Username "{username}": {"✅ EXISTS" if exists else "❌ NOT FOUND"}</div>'
        except Exception as e:
            result = f'<div class="result error">Error: {e}</div>'

    body = f"""
    <h1>🔍 Username Checker</h1>
    <p class="warning">💡 Boolean-based blind SQLi. Try: <code>Admin' AND 1=1--</code> vs <code>Admin' AND 1=2--</code></p>
    <form method="GET" action="/vuln/blind">
      <label>Check Username</label>
      <input type="text" name="username" value="{username}" placeholder="Admin" autocomplete="off">
      <button type="submit">Check</button>
    </form>
    {result}
    """
    return vuln_page("Blind SQL Injection", body)


# ─── Serve React app ─────────────────────────────────────────────────────────
@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve_react(path):
    # If frontend isn't built, redirect to the vuln hub
    index_path = os.path.join(STATIC_DIR, "index.html")
    if not os.path.exists(index_path):
        return redirect("/vuln")
    if path and os.path.exists(os.path.join(STATIC_DIR, path)):
        return send_from_directory(STATIC_DIR, path)
    return send_from_directory(STATIC_DIR, "index.html")


# ─── Init ─────────────────────────────────────────────────────────────────────
if not os.path.exists(DB_PATH):
    init_db()

if __name__ == "__main__":
    app.run(debug=True, port=5000)
