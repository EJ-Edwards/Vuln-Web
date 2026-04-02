# VulnWeb — Intentionally Vulnerable Web Application

> **⚠️ WARNING: This application is deliberately insecure. It is designed ONLY for
> educational purposes and penetration testing practice. NEVER deploy it on a
> public network or production server. Run it in an isolated VM or lab only.**

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Initialize the database
python setup_db.py

# 3. Run the application
python app.py

# 4. Open in browser
# http://127.0.0.1:5000
```

## Default Credentials

| Username | Password  | Role  |
|----------|-----------|-------|
| admin    | admin123  | admin |
| user1    | password  | user  |
| john     | letmein   | user  |
| jane     | qwerty    | user  |
| test     | test      | user  |

## Vulnerabilities Included

### 1. SQL Injection (HIGH)
- **Login page** (`/login`): Classic auth bypass via string concatenation
- **Search page** (`/search`): UNION-based data extraction
- **User lookup** (`/user/<id>`): Numeric parameter injection

### 2. Reflected XSS (HIGH)
- **Search page** (`/search`): Search query reflected without encoding
- **404 page**: URL path reflected in error message

### 3. Stored XSS (HIGH)
- **Guestbook** (`/guestbook`): Messages stored and rendered without sanitization
- **Profile bio** (`/profile`): Bio field rendered without escaping

### 4. Command Injection (HIGH)
- **Ping utility** (`/ping`): User input passed directly to OS shell

### 5. Unrestricted File Upload (HIGH)
- **Upload page** (`/upload`): No file type validation, no filename sanitization

### 6. IDOR — Insecure Direct Object References (MEDIUM)
- **Notes** (`/note/<id>`): Access any user's notes by changing the ID
- **Products** (`/product/<id>`): Internal notes exposed to all users

### 7. Path Traversal (HIGH)
- **File download** (`/download?file=`): No filename sanitization allows `../` traversal

### 8. CSRF — Cross-Site Request Forgery (MEDIUM)
- **Profile update** (`/profile`): No CSRF token
- **Password change** (`/change-password`): No CSRF token, no old password required

### 9. Broken Authentication
- Plaintext password storage
- No account lockout / rate limiting
- Weak/hardcoded session secret key (`super_secret_key_123`)
- No old password required for password change

### 10. Security Misconfiguration
- Flask debug mode enabled (Werkzeug debugger exposed)
- Verbose error messages expose SQL queries
- `robots.txt` discloses hidden paths
- Hardcoded secret key

### 11. Open Redirect (LOW)
- **Redirect** (`/redirect?url=`): No validation of redirect target

### 12. Server-Side Template Injection — SSTI (HIGH)
- **Greeting card** (`/ssti`): User input injected into Jinja2 template

### 13. Insecure Deserialization (HIGH)
- **Deserializer** (`/deserialize`): Accepts and unpickles user-supplied data

### 14. XXE — XML External Entity (HIGH)
- **XML parser** (`/xxe`): XML input parsed without disabling external entities

### 15. Broken Access Control (HIGH)
- **Admin panel** (`/admin`): No role verification — any logged-in user can access
- **API endpoint** (`/api/users`): Unauthenticated API leaking user data

### 16. Information Disclosure
- `/robots.txt` reveals hidden paths
- `/api/users` exposes user data without auth
- Admin panel shows plaintext passwords
- Product detail pages show internal notes

### 17. SSRF — Server-Side Request Forgery (CRITICAL)
- **URL Fetcher** (`/fetch`): Server fetches any URL — can reach internal services, cloud metadata (`169.254.169.254`), local files (`file://`)

### 18. JWT Token Forgery (CRITICAL)
- **JWT API** (`/jwt`, `/api/jwt/*`): Weak secret (`"secret"`), accepts `"none"` algorithm — forge admin tokens without a valid signature

### 19. Blind SQL Injection (HIGH)
- **Username Checker** (`/blind`): Boolean-based blind SQLi — only true/false response, extract data character by character

### 20. Mass Assignment / Privilege Escalation (CRITICAL)
- **Registration** (`/register`): Server accepts hidden `role` parameter — register as admin by adding `role=admin` to the request

### 21. CRLF / HTTP Header Injection (MEDIUM)
- **Language Preference** (`/header`): User input injected into response headers — inject Set-Cookie, redirect, or XSS via CRLF

### 22. Weak Cryptography (HIGH)
- **Crypto Vault** (`/crypto`): "Military Grade AES-256" is actually base64, MD5 hashes, ROT13, single-byte XOR — all trivially broken

### 23. Race Condition (HIGH)
- **Coupon Redemption** (`/coupon`): Check-then-act pattern with processing delay — redeem one-time coupon multiple times via concurrent requests

### 24. Host Header Injection (CRITICAL)
- **Password Reset** (`/reset`): Reset link built from `Host` header — inject malicious host to steal reset tokens

### 25. ReDoS — Regular Expression DoS (HIGH)
- **Regex Tester** (`/regex`): User-controlled regex patterns — cause catastrophic backtracking (e.g., `^(a+)+$` with `aaaaaa!`)

## Practice Tips

1. **Start with reconnaissance**: Check `/robots.txt`, try `/api/users`
2. **Try SQL injection on login**: `' OR '1'='1' --`
3. **Use Burp Suite or OWASP ZAP** as an intercepting proxy
4. **Test XSS payloads** on the guestbook and search pages
5. **Try command injection** with `; whoami` or `| dir` on the ping page
6. **Enumerate IDOR** by incrementing IDs on notes and products
7. **Craft CSRF PoCs** to change passwords without user interaction
8. **Upload web shells** via the unrestricted file upload
9. **Use path traversal** to download `../app.py` or `../vuln.db`
10. **Forge session cookies** using the hardcoded secret key

## Tools You Can Practice With

- [Burp Suite](https://portswigger.net/burp)
- [OWASP ZAP](https://www.zaproxy.org/)
- [sqlmap](https://sqlmap.org/)
- [Nikto](https://github.com/sullo/nikto)
- [ffuf](https://github.com/ffuf/ffuf) (fuzzing)
- [flask-unsign](https://github.com/Paradoxis/Flask-Unsign) (session cookie forging)
- Browser DevTools

## Disclaimer

This application is provided for **educational purposes only**. Use it to learn about web
security in a safe, controlled environment. Never use these techniques against systems you
do not own or have explicit written permission to test.
