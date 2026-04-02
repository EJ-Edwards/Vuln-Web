"""
Initialize the SQLite database with sample data.
WARNING: This application is intentionally vulnerable. For educational use only.
"""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "vuln.db")


def init_db():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Users table - passwords stored in plaintext (vulnerability: insecure password storage)
    c.execute("""
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT DEFAULT 'user',
            email TEXT,
            bio TEXT DEFAULT ''
        )
    """)

    # Messages/guestbook table for stored XSS
    c.execute("""
        CREATE TABLE guestbook (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            author TEXT NOT NULL,
            message TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Products table for IDOR
    c.execute("""
        CREATE TABLE products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            price REAL NOT NULL,
            description TEXT,
            secret_notes TEXT
        )
    """)

    # Private notes for IDOR
    c.execute("""
        CREATE TABLE notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    # Insert sample users (plaintext passwords - intentionally insecure)
    users = [
        ("admin", "admin123", "admin", "admin@vulnweb.local", "I am the administrator."),
        ("user1", "password", "user", "user1@vulnweb.local", "Just a regular user."),
        ("john", "letmein", "user", "john@vulnweb.local", "John likes security."),
        ("jane", "qwerty", "user", "jane@vulnweb.local", "Jane is a developer."),
        ("test", "test", "user", "test@vulnweb.local", "Test account."),
    ]
    c.executemany("INSERT INTO users (username, password, role, email, bio) VALUES (?, ?, ?, ?, ?)", users)

    # Insert sample guestbook messages
    messages = [
        ("Admin", "Welcome to VulnWeb! Feel free to leave a message."),
        ("John", "Great site for learning security!"),
    ]
    c.executemany("INSERT INTO guestbook (author, message) VALUES (?, ?)", messages)

    # Insert sample products
    products = [
        ("Widget A", 9.99, "A basic widget", "Cost price: $2.50, supplier: ACME Corp"),
        ("Widget B", 19.99, "A premium widget", "Cost price: $5.00, supplier: SecretCorp"),
        ("Gadget X", 49.99, "An advanced gadget", "Prototype - not yet released. Patent pending #12345"),
        ("Secret Item", 999.99, "You shouldn't see this", "FLAG{idor_vulnerability_found}"),
    ]
    c.executemany("INSERT INTO products (name, price, description, secret_notes) VALUES (?, ?, ?, ?)", products)

    # Insert sample notes
    notes = [
        (1, "Admin Secret", "The backup server password is: SuperSecret123!"),
        (1, "TODO", "Fix the SQL injection on the search page... eventually."),
        (2, "My Diary", "Dear diary, today I learned about XSS..."),
        (3, "Passwords", "My bank password is 12345678. Don't tell anyone!"),
    ]
    c.executemany("INSERT INTO notes (user_id, title, content) VALUES (?, ?, ?)", notes)

    conn.commit()
    conn.close()
    print(f"[+] Database initialized at {DB_PATH}")
    print("[+] Sample users created:")
    for u in users:
        print(f"    {u[0]} / {u[1]} (role: {u[2]})")


if __name__ == "__main__":
    init_db()
