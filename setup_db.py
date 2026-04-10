"""
Grand Hotel - Database Setup
"""
import sqlite3
import os
import hashlib
import secrets

DB_PATH = os.path.join(os.path.dirname(__file__), "hotel.db")


def hash_password(password, salt=None):
    if salt is None:
        salt = secrets.token_hex(16)
    hashed = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100000)
    return f"{salt}${hashed.hex()}"


def verify_password(password, stored):
    salt, _ = stored.split("$", 1)
    return hash_password(password, salt) == stored


def init_db():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute("""
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            phone TEXT,
            role TEXT DEFAULT 'guest' CHECK(role IN ('guest', 'admin')),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    c.execute("""
        CREATE TABLE rooms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            type TEXT NOT NULL CHECK(type IN ('standard', 'deluxe', 'suite', 'penthouse')),
            price_per_night REAL NOT NULL,
            capacity INTEGER NOT NULL DEFAULT 2,
            description TEXT,
            amenities TEXT,
            image_url TEXT,
            available INTEGER DEFAULT 1
        )
    """)

    c.execute("""
        CREATE TABLE bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            room_id INTEGER NOT NULL,
            guest_name TEXT NOT NULL,
            guest_email TEXT NOT NULL,
            guest_phone TEXT,
            check_in DATE NOT NULL,
            check_out DATE NOT NULL,
            num_guests INTEGER DEFAULT 1,
            special_requests TEXT,
            total_price REAL NOT NULL,
            status TEXT DEFAULT 'confirmed' CHECK(status IN ('confirmed', 'checked_in', 'checked_out', 'cancelled')),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (room_id) REFERENCES rooms(id)
        )
    """)

    c.execute("""
        CREATE TABLE reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            room_id INTEGER NOT NULL,
            rating INTEGER NOT NULL CHECK(rating >= 1 AND rating <= 5),
            comment TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (room_id) REFERENCES rooms(id)
        )
    """)

    # Seed admin user
    admin_pw = hash_password("admin123")
    guest_pw = hash_password("guest123")
    c.execute(
        "INSERT INTO users (name, email, password_hash, phone, role) VALUES (?, ?, ?, ?, ?)",
        ("Admin", "admin@grandhotel.com", admin_pw, "+1-555-0100", "admin"),
    )
    c.execute(
        "INSERT INTO users (name, email, password_hash, phone, role) VALUES (?, ?, ?, ?, ?)",
        ("John Doe", "john@example.com", guest_pw, "+1-555-0101", "guest"),
    )

    # Seed rooms
    rooms = [
        ("Ocean View Standard", "standard", 129.99, 2,
         "A comfortable room with stunning ocean views. Features a queen-size bed, work desk, and modern bathroom.",
         "WiFi,TV,Mini Bar,Air Conditioning,Ocean View",
         "https://images.unsplash.com/photo-1611892440504-42a792e24d32?w=800"),
        ("Garden Deluxe", "deluxe", 199.99, 3,
         "Spacious deluxe room overlooking our lush tropical garden. King-size bed with premium linens and sitting area.",
         "WiFi,TV,Mini Bar,Air Conditioning,Garden View,Balcony,Room Service",
         "https://images.unsplash.com/photo-1582719478250-c89cae4dc85b?w=800"),
        ("Royal Suite", "suite", 349.99, 4,
         "Luxurious suite with separate living area, dining space, and panoramic city views. Two bathrooms and a kitchenette.",
         "WiFi,TV,Mini Bar,Air Conditioning,City View,Balcony,Room Service,Jacuzzi,Kitchen",
         "https://images.unsplash.com/photo-1590490360182-c33d57733427?w=800"),
        ("Presidential Penthouse", "penthouse", 599.99, 6,
         "The pinnacle of luxury. Private rooftop terrace, personal butler service, and 360-degree views of the skyline.",
         "WiFi,TV,Mini Bar,Air Conditioning,Skyline View,Rooftop Terrace,Butler Service,Jacuzzi,Kitchen,Private Pool",
         "https://images.unsplash.com/photo-1631049307264-da0ec9d70304?w=800"),
        ("Cozy Standard", "standard", 109.99, 2,
         "Perfect for solo travelers or couples. A warm and inviting room with all the essentials for a comfortable stay.",
         "WiFi,TV,Air Conditioning,Work Desk",
         "https://images.unsplash.com/photo-1566665797739-1674de7a421a?w=800"),
        ("Sunset Deluxe", "deluxe", 229.99, 3,
         "Watch breathtaking sunsets from your private balcony. Features a king bed, rainforest shower, and premium amenities.",
         "WiFi,TV,Mini Bar,Air Conditioning,Sunset View,Balcony,Room Service,Rain Shower",
         "https://images.unsplash.com/photo-1578683010236-d716f9a3f461?w=800"),
        ("Family Suite", "suite", 399.99, 5,
         "Designed for families with connecting rooms, child-friendly amenities, and plenty of space to relax.",
         "WiFi,TV,Mini Bar,Air Conditioning,Connecting Rooms,Room Service,Game Console,Child Amenities",
         "https://images.unsplash.com/photo-1596394516093-501ba68a0ba6?w=800"),
        ("Honeymoon Suite", "suite", 449.99, 2,
         "Romance awaits in this elegantly appointed suite with rose petal turndown, champagne, and couples spa access.",
         "WiFi,TV,Mini Bar,Air Conditioning,Sea View,Balcony,Room Service,Jacuzzi,Champagne,Spa Access",
         "https://images.unsplash.com/photo-1618773928121-c32242e63f39?w=800"),
    ]
    c.executemany(
        "INSERT INTO rooms (name, type, price_per_night, capacity, description, amenities, image_url) VALUES (?, ?, ?, ?, ?, ?, ?)",
        rooms,
    )

    # Seed reviews
    reviews = [
        (2, 1, 5, "Absolutely stunning ocean views! The room was spotless and very comfortable."),
        (2, 2, 4, "Beautiful garden view, very relaxing. Would have liked a bigger bathroom."),
        (2, 3, 5, "The suite is incredible! Worth every penny for a special occasion."),
    ]
    c.executemany(
        "INSERT INTO reviews (user_id, room_id, rating, comment) VALUES (?, ?, ?, ?)",
        reviews,
    )

    # Seed a sample booking
    c.execute(
        """INSERT INTO bookings (user_id, room_id, guest_name, guest_email, guest_phone,
           check_in, check_out, num_guests, total_price, status)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (2, 1, "John Doe", "john@example.com", "+1-555-0101",
         "2026-04-15", "2026-04-18", 2, 389.97, "confirmed"),
    )

    conn.commit()
    conn.close()
    print("Database initialized successfully.")
    print("Admin login: admin@grandhotel.com / admin123")
    print("Guest login: john@example.com / guest123")


if __name__ == "__main__":
    init_db()
