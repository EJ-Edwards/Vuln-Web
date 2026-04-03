/**
 * VulnWeb v2.0 — Shared Client-Side JavaScript
 * 
 * WARNING: This file contains INTENTIONAL vulnerabilities for educational purposes.
 * DO NOT use these patterns in production code.
 * 
 * Client-Side Vulnerabilities Included:
 *   - Insecure data storage (localStorage)
 *   - No CSRF token handling
 *   - Insecure cookie handling
 *   - Verbose error exposure
 *   - No Content Security Policy enforcement
 *   - Insecure communication patterns
 */

// ============================================================
// VULNERABILITY: Global config object with sensitive data
// Accessible via browser console: window.APP_CONFIG
// ============================================================
window.APP_CONFIG = {
    apiBase: '',
    version: '2.0.0',
    debug: true,
    // VULNERABLE: Hardcoded API keys in client-side JS
    apiKey: 'sk-vuln-api-key-2024-do-not-share',
    adminEndpoint: '/admin',
    secretFlag: 'FLAG{secrets_in_client_js}',
    dbBackupUrl: '/download?file=../vuln.db',
    internalApiToken: 'Bearer eyJhbGciOiJIUzI1NiJ9.eyJyb2xlIjoiYWRtaW4ifQ.fake'
};

// ============================================================
// VULNERABILITY: Debug mode exposes verbose errors
// ============================================================
window.onerror = function(msg, url, lineNo, columnNo, error) {
    if (window.APP_CONFIG.debug) {
        // VULNERABLE: Verbose error details exposed to user
        console.log('[VulnWeb Debug] Error:', {
            message: msg,
            source: url,
            line: lineNo,
            column: columnNo,
            stack: error ? error.stack : 'N/A'
        });
    }
};

// ============================================================
// VULNERABILITY: Insecure cookie handling
// ============================================================
function setCookie(name, value, days) {
    var expires = '';
    if (days) {
        var date = new Date();
        date.setTime(date.getTime() + (days * 24 * 60 * 60 * 1000));
        expires = '; expires=' + date.toUTCString();
    }
    // VULNERABLE: No Secure flag, no HttpOnly, no SameSite
    document.cookie = name + '=' + value + expires + '; path=/';
}

function getCookie(name) {
    var nameEq = name + '=';
    var parts = document.cookie.split(';');
    for (var i = 0; i < parts.length; i++) {
        var c = parts[i].trim();
        if (c.indexOf(nameEq) === 0) {
            return c.substring(nameEq.length);
        }
    }
    return null;
}

// ============================================================
// VULNERABILITY: Track user with fingerprinting (privacy issue)
// ============================================================
function generateFingerprint() {
    var fp = {
        userAgent: navigator.userAgent,
        language: navigator.language,
        platform: navigator.platform,
        screenRes: screen.width + 'x' + screen.height,
        timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
        cookieEnabled: navigator.cookieEnabled
    };
    // VULNERABLE: Storing fingerprint in cookie and localStorage
    var fpStr = JSON.stringify(fp);
    setCookie('device_fp', btoa(fpStr), 365);
    localStorage.setItem('device_fingerprint', fpStr);
    return fp;
}

// Auto-fingerprint on load
generateFingerprint();

// ============================================================
// VULNERABILITY: Insecure fetch wrapper — no CSRF tokens
// ============================================================
window.vulnFetch = function(url, options) {
    options = options || {};
    options.credentials = 'include'; // VULNERABLE: Always sends cookies

    // VULNERABLE: No CSRF token included in requests
    // VULNERABLE: No integrity checking
    // VULNERABLE: Uses stored API key from global config
    if (!options.headers) options.headers = {};
    options.headers['X-API-Key'] = window.APP_CONFIG.apiKey;

    return fetch(url, options);
};

// ============================================================
// VULNERABILITY: Auto-complete sensitive form fields
// Browsers may cache sensitive input values
// ============================================================
document.addEventListener('DOMContentLoaded', function() {
    // None of the forms have autocomplete="off" for sensitive fields
    // Passwords and tokens can be cached by the browser
    
    // VULNERABLE: Log page visits with full URL (including tokens/params)
    if (window.APP_CONFIG.debug) {
        console.log('[VulnWeb] Page loaded:', window.location.href);
        console.log('[VulnWeb] Referrer:', document.referrer);
        console.log('[VulnWeb] Cookies:', document.cookie);
    }
});
