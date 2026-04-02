"""
VulnWeb - Intentionally Vulnerable Web Application
====================================================
WARNING: This application contains INTENTIONAL security vulnerabilities.
         It is designed for educational purposes and penetration testing practice.
         DO NOT deploy this on any public-facing server or production environment.
         Run ONLY in an isolated lab/VM environment.

Vulnerabilities included:
  1.  SQL Injection (Login, Search, User lookup)
  2.  Reflected XSS (Search, Error pages)
  3.  Stored XSS (Guestbook)
  4.  Command Injection (Ping utility)
  5.  Insecure File Upload (Unrestricted upload)
  6.  IDOR (Notes, Product details)
  7.  Path Traversal (File download)
  8.  CSRF (Profile update, Password change)
  9.  Broken Authentication (Plaintext passwords, No rate limiting, Weak session)
  10. Security Misconfiguration (Debug mode, Verbose errors, Info disclosure)
  11. Open Redirect
  12. Server-Side Template Injection (SSTI)
  13. Insecure Deserialization
  14. XML External Entity (XXE)
  15. Broken Access Control (Admin panel)
  16. SSRF — Server-Side Request Forgery (URL fetcher)
  17. JWT Forgery (Weak secret, "none" algorithm)
  18. Blind SQL Injection (Boolean-based)
  19. Mass Assignment / Privilege Escalation (Registration)
  20. CRLF / HTTP Header Injection
  21. Weak Cryptography (Broken "encryption")
  22. Race Condition (Coupon redemption)
  23. Host Header Injection (Password reset)
  24. Regex DoS (ReDoS)
"""

import os
import re
import json
import sqlite3
import subprocess
import pickle
import base64
import hashlib
import hmac
import time
import urllib.request
from xml.etree import ElementTree as ET

from flask import (
    Flask,
    render_template_string,
    request,
    redirect,
    url_for,
    session,
    make_response,
    send_file,
    g,
    flash,
    jsonify,
    Response,
)

from setup_db import init_db, DB_PATH

app = Flask(__name__)
# Vulnerability: Weak/hardcoded secret key
app.secret_key = "super_secret_key_123"

UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# ─── Database Helper ──────────────────────────────────────────────────────────
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


# ─── Base Template ────────────────────────────────────────────────────────────
BASE_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>VulnWeb - {{ title }}</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Segoe UI', Tahoma, sans-serif; background: #0a0a0a; color: #e0e0e0; }
        .navbar {
            background: linear-gradient(135deg, #1a1a2e, #16213e);
            padding: 1rem 2rem;
            display: flex; align-items: center; justify-content: space-between;
            border-bottom: 2px solid #e94560;
        }
        .navbar .brand { color: #e94560; font-size: 1.5rem; font-weight: bold; text-decoration: none; }
        .navbar .brand span { color: #0f3460; }
        .nav-links a {
            color: #a0a0a0; text-decoration: none; margin-left: 1.5rem; transition: color 0.3s;
        }
        .nav-links a:hover { color: #e94560; }
        .container { max-width: 960px; margin: 2rem auto; padding: 0 1rem; }
        .card {
            background: #1a1a2e; border-radius: 8px; padding: 2rem;
            margin-bottom: 1.5rem; border: 1px solid #16213e;
        }
        h1, h2, h3 { color: #e94560; margin-bottom: 1rem; }
        input[type="text"], input[type="password"], textarea, select {
            width: 100%; padding: 0.75rem; margin: 0.5rem 0 1rem;
            background: #0f3460; border: 1px solid #1a1a2e; border-radius: 4px;
            color: #e0e0e0; font-size: 1rem;
        }
        button, .btn {
            padding: 0.75rem 1.5rem; background: #e94560; color: white;
            border: none; border-radius: 4px; cursor: pointer; font-size: 1rem;
            text-decoration: none; display: inline-block; transition: background 0.3s;
        }
        button:hover, .btn:hover { background: #c73e54; }
        .btn-secondary { background: #0f3460; }
        .btn-secondary:hover { background: #1a1a4e; }
        table { width: 100%; border-collapse: collapse; margin-top: 1rem; }
        th, td { padding: 0.75rem; text-align: left; border-bottom: 1px solid #16213e; }
        th { background: #0f3460; color: #e94560; }
        tr:hover { background: #16213e; }
        .alert { padding: 1rem; border-radius: 4px; margin-bottom: 1rem; }
        .alert-danger { background: #5c1a1a; border: 1px solid #e94560; }
        .alert-success { background: #1a5c1a; border: 1px solid #45e960; }
        .alert-warning { background: #5c5c1a; border: 1px solid #e9e945; }
        .flash { padding: 0.75rem; margin-bottom: 1rem; border-radius: 4px; }
        pre { background: #0a0a1a; padding: 1rem; border-radius: 4px; overflow-x: auto; color: #45e960; }
        .vuln-badge {
            display: inline-block; padding: 0.2rem 0.6rem; border-radius: 3px;
            font-size: 0.75rem; font-weight: bold; margin-left: 0.5rem;
        }
        .vuln-high { background: #e94560; color: white; }
        .vuln-med { background: #e9a345; color: black; }
        .vuln-low { background: #45a0e9; color: white; }
        footer { text-align: center; padding: 2rem; color: #555; font-size: 0.85rem; }
        .warning-banner {
            background: #e94560; color: white; text-align: center; padding: 0.5rem;
            font-weight: bold; font-size: 0.85rem;
        }
    </style>
</head>
<body>
    <div class="warning-banner">
        ⚠️ INTENTIONALLY VULNERABLE APPLICATION — FOR EDUCATIONAL USE ONLY — DO NOT DEPLOY ON PUBLIC NETWORKS ⚠️
    </div>
    <nav class="navbar">
        <a href="/" class="brand">Vuln<span>Web</span></a>
        <div class="nav-links">
            <a href="/">Home</a>
            <a href="/search">Search</a>
            <a href="/guestbook">Guestbook</a>
            <a href="/ping">Ping</a>
            <a href="/upload">Upload</a>
            <a href="/notes">Notes</a>
            <a href="/products">Products</a>
            <a href="/profile">Profile</a>
            <a href="/fetch">Fetch</a>
            <a href="/jwt">JWT</a>
            <a href="/blind">Blind</a>
            <a href="/register">Register</a>
            <a href="/crypto">Crypto</a>
            <a href="/coupon">Coupon</a>
            <a href="/admin">Admin</a>
            {% if session.get('username') %}
                <a href="/logout">Logout ({{ session['username'] }})</a>
            {% else %}
                <a href="/login">Login</a>
            {% endif %}
        </div>
    </nav>
    <div class="container">
        {% with messages = get_flashed_messages() %}
        {% if messages %}
            {% for msg in messages %}
                <div class="flash alert-warning">{{ msg }}</div>
            {% endfor %}
        {% endif %}
        {% endwith %}
        {{ content }}
    </div>
    <footer>VulnWeb v1.0 — Intentionally Vulnerable — Practice Responsibly</footer>
</body>
</html>
"""


def render_page(title, content_html):
    return render_template_string(
        BASE_TEMPLATE, title=title, content=content_html
    )


# ─── ROUTES ───────────────────────────────────────────────────────────────────

# ──── Home ────────────────────────────────────────────────────────────────────
@app.route("/")
def home():
    content = """
    <div class="card">
        <h1>Welcome to VulnWeb</h1>
        <p>A deliberately vulnerable web application for practicing penetration testing.</p>
        <br>
        <h3>Available Challenges:</h3>
        <table>
            <tr><th>Page</th><th>Vulnerability</th><th>Severity</th></tr>
            <tr><td><a href="/login">Login</a></td><td>SQL Injection, Broken Auth</td>
                <td><span class="vuln-badge vuln-high">HIGH</span></td></tr>
            <tr><td><a href="/search">Search</a></td><td>SQL Injection, Reflected XSS</td>
                <td><span class="vuln-badge vuln-high">HIGH</span></td></tr>
            <tr><td><a href="/guestbook">Guestbook</a></td><td>Stored XSS</td>
                <td><span class="vuln-badge vuln-high">HIGH</span></td></tr>
            <tr><td><a href="/ping">Ping Utility</a></td><td>Command Injection</td>
                <td><span class="vuln-badge vuln-high">HIGH</span></td></tr>
            <tr><td><a href="/upload">File Upload</a></td><td>Unrestricted File Upload</td>
                <td><span class="vuln-badge vuln-high">HIGH</span></td></tr>
            <tr><td><a href="/notes">Notes</a></td><td>IDOR</td>
                <td><span class="vuln-badge vuln-med">MEDIUM</span></td></tr>
            <tr><td><a href="/products">Products</a></td><td>IDOR, Info Disclosure</td>
                <td><span class="vuln-badge vuln-med">MEDIUM</span></td></tr>
            <tr><td><a href="/profile">Profile</a></td><td>CSRF, Stored XSS</td>
                <td><span class="vuln-badge vuln-med">MEDIUM</span></td></tr>
            <tr><td><a href="/download?file=readme.txt">Download</a></td><td>Path Traversal</td>
                <td><span class="vuln-badge vuln-high">HIGH</span></td></tr>
            <tr><td><a href="/redirect?url=/">Redirect</a></td><td>Open Redirect</td>
                <td><span class="vuln-badge vuln-low">LOW</span></td></tr>
            <tr><td><a href="/ssti">Template</a></td><td>Server-Side Template Injection</td>
                <td><span class="vuln-badge vuln-high">HIGH</span></td></tr>
            <tr><td><a href="/deserialize">Deserialize</a></td><td>Insecure Deserialization</td>
                <td><span class="vuln-badge vuln-high">HIGH</span></td></tr>
            <tr><td><a href="/xxe">XXE</a></td><td>XML External Entity</td>
                <td><span class="vuln-badge vuln-high">HIGH</span></td></tr>
            <tr><td><a href="/admin">Admin Panel</a></td><td>Broken Access Control</td>
                <td><span class="vuln-badge vuln-high">HIGH</span></td></tr>
            <tr><td><a href="/fetch">URL Fetcher</a></td><td>SSRF — Server-Side Request Forgery</td>
                <td><span class="vuln-badge vuln-high">CRITICAL</span></td></tr>
            <tr><td><a href="/jwt">JWT API</a></td><td>JWT Forgery (none algo, weak secret)</td>
                <td><span class="vuln-badge vuln-high">CRITICAL</span></td></tr>
            <tr><td><a href="/blind">Blind Check</a></td><td>Blind SQL Injection (Boolean-based)</td>
                <td><span class="vuln-badge vuln-high">HIGH</span></td></tr>
            <tr><td><a href="/register">Register</a></td><td>Mass Assignment / Privilege Escalation</td>
                <td><span class="vuln-badge vuln-high">CRITICAL</span></td></tr>
            <tr><td><a href="/header">Header</a></td><td>CRLF / HTTP Header Injection</td>
                <td><span class="vuln-badge vuln-med">MEDIUM</span></td></tr>
            <tr><td><a href="/crypto">Crypto</a></td><td>Weak Cryptography</td>
                <td><span class="vuln-badge vuln-high">HIGH</span></td></tr>
            <tr><td><a href="/coupon">Coupon</a></td><td>Race Condition</td>
                <td><span class="vuln-badge vuln-high">HIGH</span></td></tr>
            <tr><td><a href="/reset">Password Reset</a></td><td>Host Header Injection</td>
                <td><span class="vuln-badge vuln-high">CRITICAL</span></td></tr>
            <tr><td><a href="/regex">Regex</a></td><td>ReDoS — Regex Denial of Service</td>
                <td><span class="vuln-badge vuln-high">HIGH</span></td></tr>
        </table>
        <br>
        <div class="alert alert-danger">
            <strong>Default credentials:</strong> admin / admin123 &nbsp;|&nbsp; user1 / password &nbsp;|&nbsp; test / test
        </div>
    </div>
    """
    return render_page("Home", content)


# ──── 1. SQL Injection — Login ────────────────────────────────────────────────
@app.route("/login", methods=["GET", "POST"])
def login():
    error = ""
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")

        # VULNERABILITY: SQL Injection — string concatenation in query
        db = get_db()
        query = f"SELECT * FROM users WHERE username = '{username}' AND password = '{password}'"
        try:
            result = db.execute(query).fetchone()
            if result:
                session["username"] = result["username"]
                session["user_id"] = result["id"]
                session["role"] = result["role"]
                return redirect(url_for("home"))
            else:
                error = "Invalid username or password"
        except Exception as e:
            # VULNERABILITY: Verbose error messages expose query
            error = f"Database error: {e}<br>Query: {query}"

    content = f"""
    <div class="card">
        <h2>Login <span class="vuln-badge vuln-high">SQL Injection</span></h2>
        {"<div class='alert alert-danger'>" + error + "</div>" if error else ""}
        <form method="POST">
            <label>Username:</label>
            <input type="text" name="username" placeholder="admin">
            <label>Password:</label>
            <input type="password" name="password" placeholder="admin123">
            <button type="submit">Login</button>
        </form>
        <br>
        <details>
            <summary style="color:#e94560;cursor:pointer;">💡 Hint</summary>
            <pre>Try: ' OR '1'='1' -- </pre>
        </details>
    </div>
    """
    return render_page("Login", content)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ──── 2. SQL Injection + Reflected XSS — Search ──────────────────────────────
@app.route("/search")
def search():
    q = request.args.get("q", "")
    results = []
    error = ""

    if q:
        db = get_db()
        # VULNERABILITY: SQL Injection in search query
        query = f"SELECT id, username, email FROM users WHERE username LIKE '%{q}%' OR email LIKE '%{q}%'"
        try:
            results = db.execute(query).fetchall()
        except Exception as e:
            error = f"Error: {e}"

    # VULNERABILITY: Reflected XSS — user input rendered without escaping
    results_html = ""
    if results:
        results_html = "<table><tr><th>ID</th><th>Username</th><th>Email</th></tr>"
        for r in results:
            results_html += f"<tr><td>{r['id']}</td><td>{r['username']}</td><td>{r['email']}</td></tr>"
        results_html += "</table>"

    content = f"""
    <div class="card">
        <h2>User Search <span class="vuln-badge vuln-high">SQLi + XSS</span></h2>
        <form method="GET">
            <input type="text" name="q" value="{q}" placeholder="Search users...">
            <button type="submit">Search</button>
        </form>
        {"<div class='alert alert-danger'>" + error + "</div>" if error else ""}
        {"<p>Results for: <strong>" + q + "</strong></p>" if q else ""}
        {results_html}
        <br>
        <details>
            <summary style="color:#e94560;cursor:pointer;">💡 Hints</summary>
            <pre>XSS: &lt;script&gt;alert('XSS')&lt;/script&gt;
SQLi: ' UNION SELECT 1,username,password FROM users --</pre>
        </details>
    </div>
    """
    return render_page("Search", content)


# ──── 3. Stored XSS — Guestbook ──────────────────────────────────────────────
@app.route("/guestbook", methods=["GET", "POST"])
def guestbook():
    db = get_db()

    if request.method == "POST":
        author = request.form.get("author", "Anonymous")
        message = request.form.get("message", "")
        # VULNERABILITY: Stored XSS — no sanitization of user input
        if message:
            db.execute("INSERT INTO guestbook (author, message) VALUES (?, ?)", (author, message))
            db.commit()
        return redirect(url_for("guestbook"))

    entries = db.execute("SELECT * FROM guestbook ORDER BY created_at DESC").fetchall()

    entries_html = ""
    for e in entries:
        # VULNERABILITY: Rendering stored content without escaping
        entries_html += f"""
        <div class="card" style="padding:1rem;">
            <strong>{e['author']}</strong> <small style="color:#666;">({e['created_at']})</small>
            <p style="margin-top:0.5rem;">{e['message']}</p>
        </div>
        """

    content = f"""
    <div class="card">
        <h2>Guestbook <span class="vuln-badge vuln-high">Stored XSS</span></h2>
        <form method="POST">
            <label>Name:</label>
            <input type="text" name="author" placeholder="Your name">
            <label>Message:</label>
            <textarea name="message" rows="3" placeholder="Leave a message..."></textarea>
            <button type="submit">Post Message</button>
        </form>
        <br>
        <details>
            <summary style="color:#e94560;cursor:pointer;">💡 Hint</summary>
            <pre>&lt;img src=x onerror="alert('Stored XSS')"&gt;</pre>
        </details>
    </div>
    <h3>Messages:</h3>
    {entries_html}
    """
    return render_page("Guestbook", content)


# ──── 4. Command Injection — Ping ─────────────────────────────────────────────
@app.route("/ping", methods=["GET", "POST"])
def ping():
    output = ""
    host = ""
    if request.method == "POST":
        host = request.form.get("host", "")
        if host:
            # VULNERABILITY: Command Injection — unsanitized input passed to shell
            try:
                result = subprocess.run(
                    f"ping -n 2 {host}" if os.name == "nt" else f"ping -c 2 {host}",
                    shell=True, capture_output=True, text=True, timeout=10
                )
                output = result.stdout + result.stderr
            except subprocess.TimeoutExpired:
                output = "Command timed out."
            except Exception as e:
                output = str(e)

    content = f"""
    <div class="card">
        <h2>Ping Utility <span class="vuln-badge vuln-high">Command Injection</span></h2>
        <form method="POST">
            <label>Host to ping:</label>
            <input type="text" name="host" value="{host}" placeholder="127.0.0.1">
            <button type="submit">Ping</button>
        </form>
        {"<pre>" + output + "</pre>" if output else ""}
        <br>
        <details>
            <summary style="color:#e94560;cursor:pointer;">💡 Hint</summary>
            <pre>Try: 127.0.0.1 & whoami
Or:  127.0.0.1 | dir
Or:  127.0.0.1 ; cat /etc/passwd</pre>
        </details>
    </div>
    """
    return render_page("Ping", content)


# ──── 5. Unrestricted File Upload ─────────────────────────────────────────────
@app.route("/upload", methods=["GET", "POST"])
def upload():
    msg = ""
    if request.method == "POST":
        f = request.files.get("file")
        if f and f.filename:
            # VULNERABILITY: No file type validation, no filename sanitization
            filepath = os.path.join(UPLOAD_FOLDER, f.filename)
            f.save(filepath)
            msg = f"<div class='alert alert-success'>File uploaded: <a href='/uploads/{f.filename}'>{f.filename}</a></div>"
        else:
            msg = "<div class='alert alert-danger'>No file selected.</div>"

    # List uploaded files
    files = os.listdir(UPLOAD_FOLDER) if os.path.exists(UPLOAD_FOLDER) else []
    files_html = ""
    if files:
        files_html = "<h3>Uploaded Files:</h3><ul>"
        for fn in files:
            files_html += f"<li><a href='/uploads/{fn}' style='color:#45a0e9;'>{fn}</a></li>"
        files_html += "</ul>"

    content = f"""
    <div class="card">
        <h2>File Upload <span class="vuln-badge vuln-high">Unrestricted Upload</span></h2>
        {msg}
        <form method="POST" enctype="multipart/form-data">
            <label>Select a file:</label>
            <input type="file" name="file" style="margin:0.5rem 0;color:#e0e0e0;">
            <br><br>
            <button type="submit">Upload</button>
        </form>
        <br>
        <details>
            <summary style="color:#e94560;cursor:pointer;">💡 Hint</summary>
            <pre>Try uploading a .php, .jsp, .py, or .html file with malicious content.
No file type restrictions are enforced.</pre>
        </details>
    </div>
    {files_html}
    """
    return render_page("Upload", content)


# Serve uploaded files (vulnerability: serves any uploaded file)
@app.route("/uploads/<path:filename>")
def serve_upload(filename):
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    if os.path.exists(filepath):
        return send_file(filepath)
    return "File not found", 404


# ──── 6. IDOR — Notes ─────────────────────────────────────────────────────────
@app.route("/notes")
def notes():
    if not session.get("user_id"):
        return redirect(url_for("login"))

    db = get_db()
    # Shows only current user's notes in listing
    user_notes = db.execute("SELECT * FROM notes WHERE user_id = ?", (session["user_id"],)).fetchall()

    notes_html = "<table><tr><th>ID</th><th>Title</th><th>Actions</th></tr>"
    for n in user_notes:
        notes_html += f"<tr><td>{n['id']}</td><td>{n['title']}</td><td><a href='/note/{n['id']}' class='btn btn-secondary' style='padding:0.3rem 0.8rem;font-size:0.85rem;'>View</a></td></tr>"
    notes_html += "</table>"

    content = f"""
    <div class="card">
        <h2>My Notes <span class="vuln-badge vuln-med">IDOR</span></h2>
        {notes_html}
        <br>
        <details>
            <summary style="color:#e94560;cursor:pointer;">💡 Hint</summary>
            <pre>Try changing the note ID in /note/1, /note/2, /note/3, /note/4
to access other users' notes — no authorization check!</pre>
        </details>
    </div>
    """
    return render_page("Notes", content)


@app.route("/note/<int:note_id>")
def view_note(note_id):
    if not session.get("user_id"):
        return redirect(url_for("login"))

    db = get_db()
    # VULNERABILITY: IDOR — does NOT check if the note belongs to the logged-in user
    note = db.execute("SELECT * FROM notes WHERE id = ?", (note_id,)).fetchone()

    if not note:
        return render_page("Note Not Found", "<div class='card'><h2>Note not found</h2></div>")

    content = f"""
    <div class="card">
        <h2>{note['title']}</h2>
        <p>Note ID: {note['id']} | Owner User ID: {note['user_id']}</p>
        <hr style="border-color:#16213e;margin:1rem 0;">
        <p>{note['content']}</p>
        <br>
        <a href="/notes" class="btn btn-secondary">Back to Notes</a>
    </div>
    """
    return render_page("Note", content)


# ──── 7. IDOR — Products ─────────────────────────────────────────────────────
@app.route("/products")
def products():
    db = get_db()
    prods = db.execute("SELECT id, name, price, description FROM products").fetchall()

    rows = ""
    for p in prods:
        rows += f"<tr><td>{p['id']}</td><td>{p['name']}</td><td>${p['price']:.2f}</td><td>{p['description']}</td><td><a href='/product/{p['id']}' class='btn btn-secondary' style='padding:0.3rem 0.8rem;font-size:0.85rem;'>Details</a></td></tr>"

    content = f"""
    <div class="card">
        <h2>Products <span class="vuln-badge vuln-med">IDOR</span></h2>
        <table>
            <tr><th>ID</th><th>Name</th><th>Price</th><th>Description</th><th></th></tr>
            {rows}
        </table>
        <br>
        <details>
            <summary style="color:#e94560;cursor:pointer;">💡 Hint</summary>
            <pre>The detail page reveals "secret_notes" — try accessing /product/4</pre>
        </details>
    </div>
    """
    return render_page("Products", content)


@app.route("/product/<int:product_id>")
def product_detail(product_id):
    db = get_db()
    # VULNERABILITY: Exposes secret_notes field
    p = db.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
    if not p:
        return render_page("Not Found", "<div class='card'><h2>Product not found</h2></div>")

    content = f"""
    <div class="card">
        <h2>{p['name']}</h2>
        <p><strong>Price:</strong> ${p['price']:.2f}</p>
        <p><strong>Description:</strong> {p['description']}</p>
        <p><strong>Internal Notes:</strong> {p['secret_notes']}</p>
        <br>
        <a href="/products" class="btn btn-secondary">Back</a>
    </div>
    """
    return render_page("Product Detail", content)


# ──── 8. CSRF — Profile ──────────────────────────────────────────────────────
@app.route("/profile", methods=["GET", "POST"])
def profile():
    if not session.get("user_id"):
        return redirect(url_for("login"))

    db = get_db()
    msg = ""

    if request.method == "POST":
        new_email = request.form.get("email", "")
        new_bio = request.form.get("bio", "")
        # VULNERABILITY: No CSRF token validation
        # VULNERABILITY: Stored XSS via bio field
        db.execute("UPDATE users SET email = ?, bio = ? WHERE id = ?",
                    (new_email, new_bio, session["user_id"]))
        db.commit()
        msg = "<div class='alert alert-success'>Profile updated!</div>"

    user = db.execute("SELECT * FROM users WHERE id = ?", (session["user_id"],)).fetchone()

    content = f"""
    <div class="card">
        <h2>My Profile <span class="vuln-badge vuln-med">CSRF + XSS</span></h2>
        {msg}
        <p><strong>Username:</strong> {user['username']}</p>
        <p><strong>Role:</strong> {user['role']}</p>
        <form method="POST">
            <label>Email:</label>
            <input type="text" name="email" value="{user['email']}">
            <label>Bio:</label>
            <textarea name="bio" rows="3">{user['bio']}</textarea>
            <button type="submit">Update Profile</button>
        </form>
        <br>
        <details>
            <summary style="color:#e94560;cursor:pointer;">💡 Hint</summary>
            <pre>No CSRF token — create an external HTML page that auto-submits a form to this endpoint.
Bio field is vulnerable to stored XSS — try injecting script tags.</pre>
        </details>
    </div>
    """
    return render_page("Profile", content)


# ──── 9. Password Change (No old password required, CSRF) ────────────────────
@app.route("/change-password", methods=["GET", "POST"])
def change_password():
    if not session.get("user_id"):
        return redirect(url_for("login"))

    msg = ""
    if request.method == "POST":
        new_pass = request.form.get("new_password", "")
        # VULNERABILITY: No CSRF token, no old password verification, plaintext storage
        if new_pass:
            db = get_db()
            db.execute("UPDATE users SET password = ? WHERE id = ?", (new_pass, session["user_id"]))
            db.commit()
            msg = "<div class='alert alert-success'>Password changed!</div>"

    content = f"""
    <div class="card">
        <h2>Change Password <span class="vuln-badge vuln-high">CSRF + Broken Auth</span></h2>
        {msg}
        <form method="POST">
            <label>New Password:</label>
            <input type="password" name="new_password" placeholder="New password">
            <button type="submit">Change Password</button>
        </form>
        <br>
        <details>
            <summary style="color:#e94560;cursor:pointer;">💡 Hint</summary>
            <pre>No old password required! No CSRF token!
An attacker can change any logged-in user's password via a crafted form.</pre>
        </details>
    </div>
    """
    return render_page("Change Password", content)


# ──── 10. Path Traversal — File Download ─────────────────────────────────────
@app.route("/download")
def download():
    filename = request.args.get("file", "")
    if filename:
        # VULNERABILITY: Path Traversal — no sanitization of filename
        filepath = os.path.join(os.path.dirname(__file__), "files", filename)
        try:
            return send_file(filepath, as_attachment=True)
        except Exception as e:
            return render_page("Error", f"<div class='card'><h2>Error</h2><pre>{e}</pre></div>")

    content = """
    <div class="card">
        <h2>File Download <span class="vuln-badge vuln-high">Path Traversal</span></h2>
        <p>Download files from the server:</p>
        <ul>
            <li><a href="/download?file=readme.txt" style="color:#45a0e9;">readme.txt</a></li>
            <li><a href="/download?file=report.txt" style="color:#45a0e9;">report.txt</a></li>
        </ul>
        <br>
        <details>
            <summary style="color:#e94560;cursor:pointer;">💡 Hint</summary>
            <pre>Try: /download?file=../vuln.db
Or:  /download?file=../../../etc/passwd
Or:  /download?file=..\\app.py (Windows)</pre>
        </details>
    </div>
    """
    return render_page("Download", content)


# ──── 11. Open Redirect ──────────────────────────────────────────────────────
@app.route("/redirect")
def open_redirect():
    url = request.args.get("url", "/")
    # VULNERABILITY: Open Redirect — no validation of redirect target
    return redirect(url)


# ──── 12. Server-Side Template Injection (SSTI) ──────────────────────────────
@app.route("/ssti", methods=["GET", "POST"])
def ssti():
    output = ""
    name = ""
    if request.method == "POST":
        name = request.form.get("name", "")
        # VULNERABILITY: SSTI — user input directly in template string
        template = f"<p>Hello, {name}!</p>"
        try:
            output = render_template_string(template)
        except Exception as e:
            output = f"<pre>Error: {e}</pre>"

    content = f"""
    <div class="card">
        <h2>Greeting Card <span class="vuln-badge vuln-high">SSTI</span></h2>
        <form method="POST">
            <label>Enter your name:</label>
            <input type="text" name="name" value="{name}" placeholder="Your name">
            <button type="submit">Generate</button>
        </form>
        <div style="margin-top:1rem;">{output}</div>
        <br>
        <details>
            <summary style="color:#e94560;cursor:pointer;">💡 Hint</summary>
            <pre>Try: {{{{ 7*7 }}}}
Or:  {{{{ config }}}}
Or:  {{{{ ''.__class__.__mro__[1].__subclasses__() }}}}</pre>
        </details>
    </div>
    """
    return render_page("SSTI", content)


# ──── 13. Insecure Deserialization ────────────────────────────────────────────
@app.route("/deserialize", methods=["GET", "POST"])
def deserialize():
    output = ""
    if request.method == "POST":
        data = request.form.get("data", "")
        if data:
            try:
                # VULNERABILITY: Insecure deserialization of user-supplied data
                obj = pickle.loads(base64.b64decode(data))
                output = f"<div class='alert alert-success'>Deserialized: {obj}</div>"
            except Exception as e:
                output = f"<div class='alert alert-danger'>Error: {e}</div>"

    content = f"""
    <div class="card">
        <h2>Data Deserializer <span class="vuln-badge vuln-high">Insecure Deserialization</span></h2>
        <p>Paste a base64-encoded serialized Python object:</p>
        <form method="POST">
            <textarea name="data" rows="4" placeholder="Base64-encoded pickle data..."></textarea>
            <button type="submit">Deserialize</button>
        </form>
        {output}
        <br>
        <details>
            <summary style="color:#e94560;cursor:pointer;">💡 Hint</summary>
            <pre>Create a malicious pickle payload:
import pickle, base64, os
class Exploit:
    def __reduce__(self):
        return (os.system, ('whoami',))
print(base64.b64encode(pickle.dumps(Exploit())).decode())</pre>
        </details>
    </div>
    """
    return render_page("Deserialize", content)


# ──── 14. XXE — XML External Entity ──────────────────────────────────────────
@app.route("/xxe", methods=["GET", "POST"])
def xxe():
    output = ""
    if request.method == "POST":
        xml_data = request.form.get("xml", "")
        if xml_data:
            try:
                # VULNERABILITY: XXE — parsing XML without disabling external entities
                # Note: ElementTree in Python is partially protected, but we simulate the vuln
                root = ET.fromstring(xml_data)
                output = f"<div class='alert alert-success'>Parsed XML root tag: &lt;{root.tag}&gt;<br>"
                for child in root:
                    output += f"  &lt;{child.tag}&gt;: {child.text}<br>"
                output += "</div>"
            except Exception as e:
                output = f"<div class='alert alert-danger'>Parse error: {e}</div>"

    content = f"""
    <div class="card">
        <h2>XML Parser <span class="vuln-badge vuln-high">XXE</span></h2>
        <p>Submit XML data for processing:</p>
        <form method="POST">
            <textarea name="xml" rows="6" placeholder='<?xml version="1.0"?>
<data>
  <name>Test</name>
  <value>123</value>
</data>'></textarea>
            <button type="submit">Parse XML</button>
        </form>
        {output}
        <br>
        <details>
            <summary style="color:#e94560;cursor:pointer;">💡 Hint</summary>
            <pre>&lt;?xml version="1.0"?&gt;
&lt;!DOCTYPE foo [
  &lt;!ENTITY xxe SYSTEM "file:///etc/passwd"&gt;
]&gt;
&lt;data&gt;&lt;name&gt;&amp;xxe;&lt;/name&gt;&lt;/data&gt;</pre>
        </details>
    </div>
    """
    return render_page("XXE", content)


# ──── 15. Broken Access Control — Admin Panel ────────────────────────────────
@app.route("/admin")
def admin():
    # VULNERABILITY: Broken Access Control — only checks if logged in, not if admin
    # (also accessible by manipulating session cookie since secret key is weak)
    if not session.get("username"):
        return redirect(url_for("login"))

    db = get_db()
    users = db.execute("SELECT id, username, password, role, email FROM users").fetchall()

    rows = ""
    for u in users:
        # VULNERABILITY: Exposes all passwords
        rows += f"<tr><td>{u['id']}</td><td>{u['username']}</td><td>{u['password']}</td><td>{u['role']}</td><td>{u['email']}</td></tr>"

    content = f"""
    <div class="card">
        <h2>Admin Panel <span class="vuln-badge vuln-high">Broken Access Control</span></h2>
        <p>Full user database (passwords visible!):</p>
        <table>
            <tr><th>ID</th><th>Username</th><th>Password</th><th>Role</th><th>Email</th></tr>
            {rows}
        </table>
        <br>
        <details>
            <summary style="color:#e94560;cursor:pointer;">💡 Hint</summary>
            <pre>Any logged-in user can access /admin — there's no role check!
The secret key is hardcoded: "super_secret_key_123"
Try forging a session cookie with flask-unsign.</pre>
        </details>
    </div>
    """
    return render_page("Admin", content)


# ──── 16. User Lookup (additional SQLi) ──────────────────────────────────────
@app.route("/user/<user_id>")
def user_lookup(user_id):
    db = get_db()
    # VULNERABILITY: SQL Injection in URL parameter
    query = f"SELECT username, email, bio FROM users WHERE id = {user_id}"
    try:
        user = db.execute(query).fetchone()
        if user:
            content = f"""
            <div class="card">
                <h2>{user['username']}</h2>
                <p><strong>Email:</strong> {user['email']}</p>
                <p><strong>Bio:</strong> {user['bio']}</p>
            </div>
            """
        else:
            content = "<div class='card'><h2>User not found</h2></div>"
    except Exception as e:
        content = f"<div class='card'><h2>Error</h2><pre>{e}</pre></div>"

    return render_page("User Profile", content)


# ──── 17. SSRF — Server-Side Request Forgery ─────────────────────────────────
@app.route("/fetch", methods=["GET", "POST"])
def ssrf_fetch():
    output = ""
    target_url = ""
    if request.method == "POST":
        target_url = request.form.get("url", "")
        if target_url:
            try:
                # VULNERABILITY: SSRF — fetches any URL the server can reach
                # No allowlist, no blocklist — can hit internal services, cloud metadata, etc.
                req = urllib.request.Request(target_url, headers={"User-Agent": "VulnWeb/1.0"})
                resp = urllib.request.urlopen(req, timeout=5)
                data = resp.read(10000).decode("utf-8", errors="replace")
                output = f"<div class='alert alert-success'>Response from {target_url}:</div><pre>{data}</pre>"
            except Exception as e:
                output = f"<div class='alert alert-danger'>Error fetching URL: {e}</div>"

    content = f"""
    <div class="card">
        <h2>URL Fetcher <span class="vuln-badge vuln-high">SSRF</span></h2>
        <p>Fetch the contents of any URL from the server side:</p>
        <form method="POST">
            <label>URL:</label>
            <input type="text" name="url" value="{target_url}" placeholder="https://example.com">
            <button type="submit">Fetch</button>
        </form>
        {output}
        <br>
        <details>
            <summary style="color:#e94560;cursor:pointer;">💡 Hint</summary>
            <pre>Try fetching internal resources:
  http://127.0.0.1:5000/api/users  (internal API)
  http://169.254.169.254/latest/meta-data/  (AWS metadata)
  http://localhost:5000/admin  (admin panel from server-side)
  file:///etc/passwd  (local files via file://)
The server fetches the URL — no client-side restrictions apply.</pre>
        </details>
    </div>
    """
    return render_page("SSRF", content)


# ──── 18. JWT Token Forgery ───────────────────────────────────────────────────
JWT_SECRET = "secret"  # VULNERABILITY: Extremely weak JWT secret


def jwt_base64_encode(data):
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def jwt_base64_decode(data):
    padding = 4 - len(data) % 4
    data += "=" * padding
    return base64.urlsafe_b64decode(data)


def create_jwt(payload, secret=JWT_SECRET, algorithm="HS256"):
    header = {"alg": algorithm, "typ": "JWT"}
    h = jwt_base64_encode(json.dumps(header).encode())
    p = jwt_base64_encode(json.dumps(payload).encode())
    if algorithm == "HS256":
        sig = hmac.new(secret.encode(), f"{h}.{p}".encode(), hashlib.sha256).digest()
        s = jwt_base64_encode(sig)
    else:
        s = ""
    return f"{h}.{p}.{s}"


def verify_jwt(token):
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None, "Invalid token format"

        header = json.loads(jwt_base64_decode(parts[0]))
        payload = json.loads(jwt_base64_decode(parts[1]))

        # VULNERABILITY: Accepts "none" algorithm — signature bypass!
        if header.get("alg") == "none" or header.get("alg") == "None":
            return payload, None

        # VULNERABILITY: Weak secret "secret" — easily brute-forced
        if header.get("alg") == "HS256":
            expected_sig = hmac.new(JWT_SECRET.encode(), f"{parts[0]}.{parts[1]}".encode(), hashlib.sha256).digest()
            actual_sig = jwt_base64_decode(parts[2])
            if hmac.compare_digest(expected_sig, actual_sig):
                return payload, None
            return None, "Invalid signature"

        return None, f"Unsupported algorithm: {header.get('alg')}"
    except Exception as e:
        return None, str(e)


@app.route("/jwt", methods=["GET"])
def jwt_page():
    content = """
    <div class="card">
        <h2>JWT API <span class="vuln-badge vuln-high">JWT Forgery</span></h2>
        <p>This API uses JSON Web Tokens for authentication.</p>
        <h3>Endpoints:</h3>
        <table>
            <tr><th>Method</th><th>Endpoint</th><th>Description</th></tr>
            <tr><td>POST</td><td>/api/jwt/login</td><td>Get a JWT token (JSON body: username, password)</td></tr>
            <tr><td>GET</td><td>/api/jwt/protected</td><td>Access protected data (Header: Authorization: Bearer &lt;token&gt;)</td></tr>
            <tr><td>GET</td><td>/api/jwt/admin</td><td>Admin-only endpoint (requires role=admin in JWT)</td></tr>
        </table>
        <br>
        <h3>Quick Test:</h3>
        <pre>
# Get a token
curl -X POST /api/jwt/login -H "Content-Type: application/json" \\
     -d '{"username":"user1","password":"password"}'

# Use the token
curl /api/jwt/protected -H "Authorization: Bearer &lt;token&gt;"
        </pre>
        <br>
        <details>
            <summary style="color:#e94560;cursor:pointer;">💡 Hints</summary>
            <pre>1. The JWT secret is extremely weak — try "secret"
2. The server accepts alg:"none" — forge tokens without a signature!
3. Change "role":"user" to "role":"admin" in the payload
4. Tools: jwt.io, jwt_tool, flask-unsign

Forge a token with "none" algorithm:
  Header: {"alg":"none","typ":"JWT"}
  Payload: {"username":"admin","role":"admin"}
  Base64url encode each, join with dots, leave signature empty:
  eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0.eyJ1c2VybmFtZSI6ImFkbWluIiwicm9sZSI6ImFkbWluIn0.</pre>
        </details>
    </div>
    """
    return render_page("JWT", content)


@app.route("/api/jwt/login", methods=["POST"])
def jwt_login():
    data = request.get_json(silent=True) or {}
    username = data.get("username", "")
    password = data.get("password", "")

    db = get_db()
    user = db.execute("SELECT * FROM users WHERE username = ? AND password = ?", (username, password)).fetchone()
    if user:
        token = create_jwt({"username": user["username"], "role": user["role"], "iat": int(time.time())})
        return jsonify({"token": token, "message": f"Welcome {user['username']}!"})
    return jsonify({"error": "Invalid credentials"}), 401


@app.route("/api/jwt/protected")
def jwt_protected():
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return jsonify({"error": "Missing Authorization header. Use: Bearer <token>"}), 401

    token = auth[7:]
    payload, error = verify_jwt(token)
    if error:
        return jsonify({"error": error}), 401

    return jsonify({"message": f"Hello {payload.get('username')}!", "your_role": payload.get("role"), "token_data": payload})


@app.route("/api/jwt/admin")
def jwt_admin():
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return jsonify({"error": "Missing Authorization header"}), 401

    token = auth[7:]
    payload, error = verify_jwt(token)
    if error:
        return jsonify({"error": error}), 401

    # VULNERABILITY: Role is trusted from JWT payload without server-side check
    if payload.get("role") != "admin":
        return jsonify({"error": "Admin access required", "your_role": payload.get("role")}), 403

    return jsonify({
        "message": "Welcome to the admin API!",
        "flag": "FLAG{jwt_none_algorithm_bypass}",
        "secret_data": "Database backup password: Sup3rS3cr3t!",
        "admin_users": ["admin"]
    })


# ──── 19. Blind SQL Injection (Boolean-based) ────────────────────────────────
@app.route("/blind", methods=["GET", "POST"])
def blind_sqli():
    result = ""
    username = ""
    if request.method == "POST":
        username = request.form.get("username", "")
        db = get_db()
        # VULNERABILITY: Blind SQL Injection — only reveals exists/not exists
        query = f"SELECT 1 FROM users WHERE username = '{username}'"
        try:
            row = db.execute(query).fetchone()
            if row:
                result = "<div class='alert alert-success'>✓ User exists!</div>"
            else:
                result = "<div class='alert alert-danger'>✗ User does not exist.</div>"
        except Exception:
            result = "<div class='alert alert-danger'>✗ User does not exist.</div>"

    content = f"""
    <div class="card">
        <h2>Username Checker <span class="vuln-badge vuln-high">Blind SQLi</span></h2>
        <p>Check if a username is already taken:</p>
        <form method="POST">
            <label>Username:</label>
            <input type="text" name="username" value="{username}" placeholder="admin">
            <button type="submit">Check</button>
        </form>
        {result}
        <br>
        <details>
            <summary style="color:#e94560;cursor:pointer;">💡 Hint</summary>
            <pre>Boolean-based blind SQLi — only true/false responses.
Extract data one character at a time:

Check if admin password starts with 'a':
  admin' AND SUBSTR((SELECT password FROM users WHERE username='admin'),1,1)='a' --

Automate with sqlmap:
  sqlmap -u "http://target/blind" --data="username=admin" --technique=B</pre>
        </details>
    </div>
    """
    return render_page("Blind SQLi", content)


# ──── 20. Mass Assignment / Privilege Escalation ─────────────────────────────
@app.route("/register", methods=["GET", "POST"])
def register():
    msg = ""
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        email = request.form.get("email", "")
        # VULNERABILITY: Mass Assignment — all form fields go directly into the DB
        # Hidden "role" field can be injected to escalate to admin
        role = request.form.get("role", "user")
        bio = request.form.get("bio", "")

        if username and password:
            db = get_db()
            existing = db.execute("SELECT 1 FROM users WHERE username = ?", (username,)).fetchone()
            if existing:
                msg = "<div class='alert alert-danger'>Username already taken!</div>"
            else:
                db.execute("INSERT INTO users (username, password, role, email, bio) VALUES (?, ?, ?, ?, ?)",
                           (username, password, role, email, bio))
                db.commit()
                msg = f"<div class='alert alert-success'>Account created! Username: {username}, Role: {role}</div>"
        else:
            msg = "<div class='alert alert-danger'>Username and password are required.</div>"

    content = f"""
    <div class="card">
        <h2>Register <span class="vuln-badge vuln-high">Mass Assignment</span></h2>
        {msg}
        <form method="POST">
            <label>Username:</label>
            <input type="text" name="username" placeholder="newuser">
            <label>Password:</label>
            <input type="password" name="password" placeholder="password">
            <label>Email:</label>
            <input type="text" name="email" placeholder="user@example.com">
            <!-- No "role" field visible in the form -->
            <button type="submit">Register</button>
        </form>
        <br>
        <details>
            <summary style="color:#e94560;cursor:pointer;">💡 Hint</summary>
            <pre>The server blindly accepts ALL form parameters.
Add a hidden "role" field to the request:

With curl:
  curl -X POST /register -d "username=hacker&password=hacker&role=admin"

With Burp Suite:
  Intercept the POST and add: role=admin

Or add in browser devtools:
  document.forms[0].innerHTML += '&lt;input name="role" value="admin"&gt;'</pre>
        </details>
    </div>
    """
    return render_page("Register", content)


# ──── 21. CRLF / HTTP Header Injection ───────────────────────────────────────
@app.route("/header")
def header_injection():
    lang = request.args.get("lang", "en")
    # VULNERABILITY: CRLF injection — user input placed directly in response header
    response = make_response(render_page("Header Injection", f"""
    <div class="card">
        <h2>Language Preference <span class="vuln-badge vuln-med">CRLF Injection</span></h2>
        <p>Current language: <strong>{lang}</strong></p>
        <form method="GET">
            <label>Set language:</label>
            <input type="text" name="lang" value="{lang}" placeholder="en">
            <button type="submit">Set</button>
        </form>
        <br>
        <details>
            <summary style="color:#e94560;cursor:pointer;">💡 Hint</summary>
            <pre>The "lang" parameter is reflected into a response header.
Inject CRLF characters to add arbitrary headers:

  /header?lang=en%0d%0aSet-Cookie:%20hacked=true
  /header?lang=en%0d%0a%0d%0a&lt;script&gt;alert('XSS via CRLF')&lt;/script&gt;

URL-encoded: %0d = CR (\\r), %0a = LF (\\n)</pre>
        </details>
    </div>
    """))
    # VULNERABILITY: User input injected directly into response header
    response.headers["X-Custom-Lang"] = lang
    return response


# ──── 22. Weak Cryptography ──────────────────────────────────────────────────
@app.route("/crypto", methods=["GET", "POST"])
def weak_crypto():
    output = ""
    if request.method == "POST":
        action = request.form.get("action", "encrypt")
        text = request.form.get("text", "")
        method = request.form.get("method", "base64")

        if text:
            if method == "base64":
                # VULNERABILITY: Base64 is encoding, not encryption
                if action == "encrypt":
                    result = base64.b64encode(text.encode()).decode()
                else:
                    try:
                        result = base64.b64decode(text.encode()).decode()
                    except Exception:
                        result = "Invalid base64"
            elif method == "md5":
                # VULNERABILITY: MD5 is broken for security purposes
                result = hashlib.md5(text.encode()).hexdigest()
            elif method == "rot13":
                # VULNERABILITY: ROT13 is not encryption
                result = text.translate(str.maketrans(
                    'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz',
                    'NOPQRSTUVWXYZABCDEFGHIJKLMnopqrstuvwxyzabcdefghijklm'))
            elif method == "xor":
                # VULNERABILITY: Single-byte XOR with known key
                key = 0x42
                result = ''.join(f'{ord(c) ^ key:02x}' for c in text)
            else:
                result = text

            output = f"<div class='alert alert-success'><strong>Result:</strong><br><pre>{result}</pre></div>"

    content = f"""
    <div class="card">
        <h2>Crypto Vault <span class="vuln-badge vuln-high">Weak Crypto</span></h2>
        <p>"Securely" encrypt your sensitive data:</p>
        <form method="POST">
            <label>Text:</label>
            <textarea name="text" rows="3" placeholder="Secret message..."></textarea>
            <label>Method:</label>
            <select name="method">
                <option value="base64">AES-256 Military Grade™ (base64)</option>
                <option value="md5">Secure Hash (MD5)</option>
                <option value="rot13">ROT13 Cipher</option>
                <option value="xor">XOR Encryption (key: 0x42)</option>
            </select>
            <label>Action:</label>
            <select name="action">
                <option value="encrypt">Encrypt</option>
                <option value="decrypt">Decrypt</option>
            </select>
            <button type="submit">Process</button>
        </form>
        {output}
        <br>
        <p style="color:#666;">Encrypted admin credentials stored: <code>YWRtaW4xMjM=</code></p>
        <br>
        <details>
            <summary style="color:#e94560;cursor:pointer;">💡 Hint</summary>
            <pre>"AES-256 Military Grade" is actually just base64 encoding!
  echo "YWRtaW4xMjM=" | base64 -d  → admin123

MD5 is cryptographically broken — use rainbow tables:
  https://crackstation.net/

ROT13 is a Caesar cipher with shift 13 — trivially reversible.
XOR with a known single-byte key is trivially breakable.</pre>
        </details>
    </div>
    """
    return render_page("Crypto", content)


# ──── 23. Race Condition — Coupon Redemption ─────────────────────────────────
@app.route("/coupon", methods=["GET", "POST"])
def coupon():
    # Store balance and coupon state in session
    if "balance" not in session:
        session["balance"] = 0.0
        session["coupon_used"] = False

    msg = ""
    if request.method == "POST":
        code = request.form.get("code", "")
        if code == "FREEBIE50":
            # VULNERABILITY: Race Condition — check-then-act without locking
            # Send many requests simultaneously to redeem multiple times
            if not session.get("coupon_used"):
                # Simulate processing delay that widens the race window
                time.sleep(0.1)
                session["balance"] = session.get("balance", 0) + 50.0
                session["coupon_used"] = True
                msg = "<div class='alert alert-success'>Coupon applied! +$50.00</div>"
            else:
                msg = "<div class='alert alert-danger'>Coupon already used!</div>"
        else:
            msg = "<div class='alert alert-danger'>Invalid coupon code.</div>"

    # Reset button
    if request.args.get("reset") == "1":
        session["balance"] = 0.0
        session["coupon_used"] = False
        return redirect(url_for("coupon"))

    content = f"""
    <div class="card">
        <h2>Coupon Redemption <span class="vuln-badge vuln-high">Race Condition</span></h2>
        <p>Current Balance: <strong style="color:#45e960;">${session.get('balance', 0):.2f}</strong></p>
        <p>Coupon Used: {'Yes' if session.get('coupon_used') else 'No'}</p>
        {msg}
        <form method="POST">
            <label>Coupon Code:</label>
            <input type="text" name="code" placeholder="Enter coupon code">
            <button type="submit">Redeem</button>
        </form>
        <br>
        <a href="/coupon?reset=1" class="btn btn-secondary">Reset Balance</a>
        <br><br>
        <details>
            <summary style="color:#e94560;cursor:pointer;">💡 Hint</summary>
            <pre>Valid coupon: FREEBIE50 (one-time use, adds $50)

The check-then-act pattern has a race window.
Send many requests simultaneously:

  # Using curl in parallel:
  for i in $(seq 1 20); do
    curl -X POST /coupon -d "code=FREEBIE50" -b "session=..." &
  done

  # Using Burp Intruder with "Pitchfork" or Turbo Intruder
  # to send 50+ requests at exactly the same time.

If timed correctly, balance will exceed $50!</pre>
        </details>
    </div>
    """
    return render_page("Coupon", content)


# ──── 24. Host Header Injection — Password Reset ─────────────────────────────
@app.route("/reset", methods=["GET", "POST"])
def host_header_reset():
    msg = ""
    if request.method == "POST":
        email = request.form.get("email", "")
        if email:
            # VULNERABILITY: Host Header Injection — uses Host header to build reset link
            host = request.headers.get("Host", "localhost:5000")
            reset_token = base64.b64encode(f"{email}:{int(time.time())}".encode()).decode()
            reset_link = f"http://{host}/reset-confirm?token={reset_token}"
            # In a real app this would be emailed — here we display it
            msg = f"""<div class='alert alert-success'>
                Password reset link generated!<br>
                <strong>Debug (would be emailed):</strong><br>
                <a href="{reset_link}" style="color:#45a0e9;word-break:break-all;">{reset_link}</a>
            </div>"""

    content = f"""
    <div class="card">
        <h2>Password Reset <span class="vuln-badge vuln-high">Host Header Injection</span></h2>
        {msg}
        <form method="POST">
            <label>Email Address:</label>
            <input type="text" name="email" placeholder="admin@vulnweb.local">
            <button type="submit">Send Reset Link</button>
        </form>
        <br>
        <details>
            <summary style="color:#e94560;cursor:pointer;">💡 Hint</summary>
            <pre>The reset link is built using the Host header from the request.
Inject a malicious host to steal the reset token:

  curl -X POST /reset -d "email=admin@vulnweb.local" \\
       -H "Host: evil-attacker.com"

The generated link will point to evil-attacker.com,
sending the reset token to your server when the victim clicks it.

Also try X-Forwarded-Host header injection.</pre>
        </details>
    </div>
    """
    return render_page("Password Reset", content)


@app.route("/reset-confirm")
def reset_confirm():
    token = request.args.get("token", "")
    msg = ""
    if token:
        try:
            decoded = base64.b64decode(token).decode()
            email, ts = decoded.rsplit(":", 1)
            msg = f"<div class='alert alert-success'>Reset token valid for: {email}<br>You can now set a new password.</div>"
        except Exception:
            msg = "<div class='alert alert-danger'>Invalid or expired token.</div>"

    content = f"""
    <div class="card">
        <h2>Confirm Password Reset</h2>
        {msg}
        <form method="POST" action="/change-password">
            <label>New Password:</label>
            <input type="password" name="new_password" placeholder="New password">
            <button type="submit">Change Password</button>
        </form>
    </div>
    """
    return render_page("Reset Confirm", content)


# ──── 25. ReDoS — Regular Expression Denial of Service ───────────────────────
@app.route("/regex", methods=["GET", "POST"])
def regex_dos():
    output = ""
    pattern = ""
    text = ""
    if request.method == "POST":
        pattern = request.form.get("pattern", "")
        text = request.form.get("text", "")
        if pattern and text:
            try:
                start = time.time()
                # VULNERABILITY: User-controlled regex — can cause catastrophic backtracking
                match = re.search(pattern, text)
                elapsed = time.time() - start
                if match:
                    output = f"<div class='alert alert-success'>Match found: '{match.group()}' (took {elapsed:.4f}s)</div>"
                else:
                    output = f"<div class='alert alert-danger'>No match (took {elapsed:.4f}s)</div>"
            except re.error as e:
                output = f"<div class='alert alert-danger'>Regex error: {e}</div>"
            except Exception as e:
                output = f"<div class='alert alert-danger'>Error: {e}</div>"

    content = f"""
    <div class="card">
        <h2>Regex Tester <span class="vuln-badge vuln-high">ReDoS</span></h2>
        <p>Test your regular expressions against sample text:</p>
        <form method="POST">
            <label>Pattern:</label>
            <input type="text" name="pattern" value="{pattern}" placeholder="^(a+)+$">
            <label>Test String:</label>
            <input type="text" name="text" value="{text}" placeholder="aaaaaaaaaaaaaaaaaaaaaaaa!">
            <button type="submit">Test</button>
        </form>
        {output}
        <br>
        <details>
            <summary style="color:#e94560;cursor:pointer;">💡 Hint</summary>
            <pre>Certain regex patterns cause exponential backtracking (ReDoS):

Evil pattern: ^(a+)+$
Evil input:   aaaaaaaaaaaaaaaaaaaaaaaa!

Other dangerous patterns:
  (a|a)*b          with "aaaaaaaaaaaaaaaa!"
  ([a-z]+)+$       with "aaaaaaaaaaaaaaaa!"
  (a+){lbrace}10{rbrace}  with "aaaaaaaaaaaaaaaa!"

The server hangs while the regex engine backtracks exponentially.
This is a Denial of Service attack using CPU exhaustion.</pre>
        </details>
    </div>
    """
    return render_page("Regex", content)


# ──── Robots.txt (info disclosure) ────────────────────────────────────────────
@app.route("/robots.txt")
def robots():
    # VULNERABILITY: Information Disclosure
    return """User-agent: *
Disallow: /admin
Disallow: /uploads
Disallow: /backup
Disallow: /secret-api-key-abc123
""", 200, {"Content-Type": "text/plain"}


# ──── Hidden API endpoint ─────────────────────────────────────────────────────
@app.route("/api/users")
def api_users():
    # VULNERABILITY: Unauthenticated API endpoint exposing user data
    db = get_db()
    users = db.execute("SELECT id, username, email, role FROM users").fetchall()
    return {"users": [dict(u) for u in users]}


# ──── Error Handlers (verbose errors) ────────────────────────────────────────
@app.errorhandler(404)
def not_found(e):
    # VULNERABILITY: Reflected content in error page
    path = request.path
    content = f"""
    <div class="card">
        <h2>404 — Page Not Found</h2>
        <p>The page <strong>{path}</strong> does not exist.</p>
    </div>
    """
    return render_page("404", content), 404


@app.errorhandler(500)
def internal_error(e):
    # VULNERABILITY: Verbose error
    content = f"""
    <div class="card">
        <h2>500 — Internal Server Error</h2>
        <pre>{e}</pre>
    </div>
    """
    return render_page("500", content), 500


# ─── Auto-init DB (needed for Render / Gunicorn) ─────────────────────────────
if not os.path.exists(DB_PATH):
    init_db()

# ─── Main ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("  VulnWeb — Intentionally Vulnerable Web Application")
    print("  WARNING: For educational/lab use ONLY!")
    print("  DO NOT expose to public networks!")
    print("=" * 60)
    print(f"\n  → http://127.0.0.1:5000\n")

    # VULNERABILITY: Debug mode enabled — exposes Werkzeug debugger
    app.run(debug=True, host="127.0.0.1", port=5000)
