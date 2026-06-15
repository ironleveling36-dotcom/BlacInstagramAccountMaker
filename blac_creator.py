#!/usr/bin/env python3
"""
Blac – Pure HTTP with Browser Impersonation (curl_cffi)
Bypasses 429 by mimicking real Chrome TLS fingerprint.
"""
import time
import random
import json
import re
from datetime import datetime, timedelta
from curl_cffi import requests as cffi_req
from dotenv import load_dotenv

from blac_core.proxy_manager import rotate_proxy, mark_proxy_bad
from blac_core.account_generator import generate_username, generate_fullname
from blac_core.temp_mail import get_temp_email
from blac_core.session_saver import save_account

load_dotenv()

# Use Chrome impersonation
IMPERSONATE = "chrome131"  # or "chrome120", "safari17_0", etc.

def get_csrf_and_cookies(proxy: str = None) -> tuple:
    """Fetch CSRF token and cookies using impersonated browser session."""
    # Create a session with impersonation
    sess = cffi_req.Session(impersonate=IMPERSONATE, proxies={"http": proxy, "https": proxy} if proxy else None)
    
    # Step 1: Visit homepage
    print("[DEBUG] Fetching homepage...")
    resp = sess.get("https://www.instagram.com/", timeout=20)
    resp.raise_for_status()
    
    # Step 2: Visit signup page
    print("[DEBUG] Fetching signup page...")
    resp = sess.get("https://www.instagram.com/accounts/emailsignup/", timeout=20)
    resp.raise_for_status()
    
    # Extract CSRF token from cookies
    csrf = sess.cookies.get('csrftoken')
    if csrf:
        print(f"[DEBUG] CSRF from cookie: {csrf[:10]}...")
        return csrf, sess.cookies.get_dict()
    
    # Fallback: try to extract from HTML
    html = resp.text
    match = re.search(r'"csrf_token":"([^"]+)"', html)
    if match:
        csrf = match.group(1)
        print(f"[DEBUG] CSRF from HTML: {csrf[:10]}...")
        return csrf, sess.cookies.get_dict()
    
    raise Exception("Could not obtain CSRF token")

def generate_client_id() -> str:
    return f"wp-{''.join(random.choices('abcdef0123456789', k=10))}"

def create_account(proxy: str = None) -> bool:
    try:
        csrf, init_cookies = get_csrf_and_cookies(proxy)
    except Exception as e:
        print(f"[!] Failed to get CSRF: {e}")
        return False
    
    # Create a new session for the actual signup request (impersonate same browser)
    sess = cffi_req.Session(impersonate=IMPERSONATE, proxies={"http": proxy, "https": proxy} if proxy else None)
    sess.headers.update({
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
    
    # Generate account data
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
    
    # POST request
    try:
        resp = sess.post("https://www.instagram.com/accounts/web_create_ajax/", data=data, timeout=20)
        if resp.status_code == 429:
            print("[!] 429 Rate limit")
            return False
        if resp.status_code != 200:
            print(f"[!] HTTP {resp.status_code} – {resp.text[:200]}")
            return False
        result = resp.json()
    except Exception as e:
        print(f"[!] Request failed: {e}")
        return False
    
    if result.get('account_created', False):
        print(f"[✓] Account created: {username}")
        session_id = sess.cookies.get('sessionid', '')
        expiry = (datetime.now() + timedelta(days=30)).isoformat()
        save_account(username, password, email, session_id, expiry, "accounts.json")
        return True
    elif result.get('checkpoint_url'):
        print(f"[!] Checkpoint – need verification: {username}")
        return False
    else:
        print(f"[?] Unknown: {result}")
        return False

def main():
    print("Blac – curl_cffi version (browser impersonation)")
    while True:
        proxy_dict = rotate_proxy()
        if not proxy_dict:
            print("[!] No proxies available. Add working proxies to proxies.txt")
            time.sleep(60)
            continue
        
        user = proxy_dict.get('user', '')
        pwd = proxy_dict.get('pass', '')
        if user and pwd:
            proxy_str = f"http://{user}:{pwd}@{proxy_dict['host']}:{proxy_dict['port']}"
        else:
            proxy_str = f"http://{proxy_dict['host']}:{proxy_dict['port']}"
        
        print(f"[*] Trying proxy: {proxy_str[:50]}...")
        success = create_account(proxy_str)
        
        if success:
            delay = random.randint(120, 300)
            print(f"[✓] Success. Waiting {delay}s...")
        else:
            mark_proxy_bad(proxy_dict)
            delay = random.randint(15, 30)
            print(f"[!] Failure. Retrying with new proxy in {delay}s...")
        
        time.sleep(delay)

if __name__ == "__main__":
    main()