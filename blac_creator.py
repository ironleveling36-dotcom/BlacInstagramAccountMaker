#!/usr/bin/env python3
"""
Blac – Pure HTTP Instagram Account Creator
Handles 429, rotates proxies, supports HTTP & SOCKS5.
"""
import time
import random
import json
import re
import requests
from datetime import datetime, timedelta
from typing import Dict, Optional

# If you have the proxy manager modules, import them; otherwise define inline.
# For simplicity, we'll include proxy management inline.

PROXY_FILE = "proxies.txt"

def load_proxies() -> list:
    """Load proxies from file, one per line, in any format:
       http://user:pass@host:port
       socks5://user:pass@host:port
       host:port:user:pass
       host:port
    """
    proxies = []
    try:
        with open(PROXY_FILE, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                proxies.append(line)
    except FileNotFoundError:
        print("[!] proxies.txt not found")
    return proxies

PROXY_LIST = load_proxies()
BAD_PROXIES = set()

def get_proxy() -> Optional[str]:
    """Return a random working proxy string (as used in requests)."""
    available = [p for p in PROXY_LIST if p not in BAD_PROXIES]
    if not available:
        return None
    return random.choice(available)

def mark_proxy_bad(proxy_str: str):
    BAD_PROXIES.add(proxy_str)
    print(f"[!] Marked bad: {proxy_str[:50]}...")

def get_shared_data(proxy: Optional[str] = None) -> Dict:
    """
    Fetch CSRF token and cookies using a realistic browser handshake.
    Returns: {'csrf': str, 'cookies': dict}
    """
    sess = requests.Session()
    if proxy:
        # For socks5, requests expects 'socks5://...'
        sess.proxies = {'http': proxy, 'https': proxy}
    
    sess.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
        'sec-ch-ua': '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1',
        'Cache-Control': 'max-age=0',
    })
    
    # First, visit homepage to get base cookies
    home = sess.get("https://www.instagram.com/", timeout=15)
    home.raise_for_status()
    
    # Then go to signup page
    resp = sess.get("https://www.instagram.com/accounts/emailsignup/", timeout=15)
    resp.raise_for_status()
    
    # Try to get CSRF from cookie (most reliable)
    csrf = sess.cookies.get('csrftoken')
    if csrf:
        return {"csrf": csrf, "cookies": sess.cookies.get_dict()}
    
    # Fallback: extract from HTML
    html = resp.text
    match = re.search(r'"csrf_token":"([^"]+)"', html)
    if match:
        csrf = match.group(1)
        return {"csrf": csrf, "cookies": sess.cookies.get_dict()}
    
    # Last resort: __NEXT_DATA__
    match = re.search(r'<script[^>]*id="__NEXT_DATA__"[^>]*>([^<]+)</script>', html)
    if match:
        try:
            data = json.loads(match.group(1))
            csrf = data.get('props', {}).get('pageProps', {}).get('csrf_token')
            if csrf:
                return {"csrf": csrf, "cookies": sess.cookies.get_dict()}
        except:
            pass
    
    raise Exception("Could not obtain CSRF token (blocked or bad proxy)")

def generate_client_id() -> str:
    return f"wp-{''.join(random.choices('abcdef0123456789', k=10))}"

def create_account(proxy_str: Optional[str] = None) -> bool:
    # 1. Get CSRF and initial cookies
    try:
        shared = get_shared_data(proxy_str)
        csrf = shared['csrf']
        init_cookies = shared['cookies']
    except Exception as e:
        print(f"[!] Failed to get CSRF: {e}")
        return False

    # 2. Create session with proper headers
    sess = requests.Session()
    if proxy_str:
        sess.proxies = {'http': proxy_str, 'https': proxy_str}
    
    sess.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
        'X-CSRFToken': csrf,
        'X-Instagram-AJAX': '1',
        'X-Requested-With': 'XMLHttpRequest',
        'Content-Type': 'application/x-www-form-urlencoded',
        'Referer': 'https://www.instagram.com/accounts/emailsignup/',
        'Origin': 'https://www.instagram.com',
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'same-origin',
    })
    
    for name, value in init_cookies.items():
        sess.cookies.set(name, value, domain='.instagram.com')
    
    # 3. Generate account data
    from blac_core.account_generator import generate_username, generate_fullname
    from blac_core.temp_mail import get_temp_email
    from blac_core.session_saver import save_account
    
    email = get_temp_email()
    fullname = generate_fullname()
    username = generate_username()
    password = "blac@123"
    ts = int(time.time())
    enc_password = f"#PWD_INSTAGRAM_BROWSER:10:{ts}:6:{password}"
    client_id = generate_client_id()
    
    data = {
        'email': email,
        'fullname': fullname,
        'username': username,
        'password': password,
        'enc_password': enc_password,
        'client_id': client_id,
        'seamless_login_enabled': '1',
        'tos_version': 'eu',
        'opt_into_one_tap': 'false',
        'use_new_segmenting': '1'
    }
    
    # 4. POST to signup endpoint
    try:
        resp = sess.post("https://www.instagram.com/accounts/web_create_ajax/", data=data, timeout=15)
        if resp.status_code == 429:
            print("[!] Rate limited (429).")
            return False
        if resp.status_code != 200:
            print(f"[!] HTTP {resp.status_code} – {resp.text[:200]}")
            return False
        result = resp.json()
    except Exception as e:
        print(f"[!] Request failed: {e}")
        return False
    
    # 5. Process response
    if result.get('account_created', False):
        print(f"[✓] Account created: {username}")
        session_id = sess.cookies.get('sessionid', '')
        expiry = (datetime.now() + timedelta(days=30)).isoformat()
        save_account(username, password, email, session_id, expiry, "accounts.json")
        return True
    elif result.get('checkpoint_url'):
        print(f"[!] Checkpoint – need verification: {username}")
        return False
    elif 'spam' in str(result).lower():
        print(f"[!] Spam block – proxy flagged.")
        return False
    else:
        print(f"[?] Unknown response: {result}")
        return False

def main():
    print("Blac – Pure HTTP Instagram Account Creator")
    while True:
        proxy_str = get_proxy()
        if not proxy_str:
            print("[!] No working proxies. Add proxies to proxies.txt")
            time.sleep(60)
            continue
        print(f"[*] Using proxy: {proxy_str[:80]}...")
        success = create_account(proxy_str)
        if success:
            # Success: keep proxy, wait longer
            delay = random.randint(120, 300)
            print(f"[✓] Success. Waiting {delay}s before next account...")
        else:
            # Failure: mark proxy as bad, immediately retry with new proxy
            mark_proxy_bad(proxy_str)
            delay = random.randint(5, 15)
            print(f"[!] Failure. Retrying with new proxy in {delay}s...")
        time.sleep(delay)

if __name__ == "__main__":
    main()