#!/usr/bin/env python3
"""
Blac – Pure HTTP Instagram Account Creator
Fixed: CSRF extraction from cookies, Client Hints, homepage pre‑fetch.
"""
import time
import random
import json
import re
import requests
from datetime import datetime, timedelta
from typing import Dict, Optional

from blac_core.proxy_manager import rotate_proxy, test_proxy
from blac_core.account_generator import generate_username, generate_fullname
from blac_core.temp_mail import get_temp_email, get_inbox
from blac_core.verif_code import get_instagram_code
from blac_core.session_saver import save_account

def get_shared_data(proxy: Optional[str] = None) -> Dict:
    """
    Fetch CSRF token and cookies using a realistic browser handshake.
    Returns: {'csrf': str, 'cookies': dict}
    """
    sess = requests.Session()
    if proxy:
        sess.proxies = {'http': proxy, 'https': proxy}
    
    # Critical: modern browser headers with Client Hints
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
    try:
        home = sess.get("https://www.instagram.com/", timeout=15)
        home.raise_for_status()
    except Exception as e:
        raise Exception(f"Homepage fetch failed: {e}")
    
    # Then go to signup page
    resp = sess.get("https://www.instagram.com/accounts/emailsignup/", timeout=15)
    resp.raise_for_status()
    
    # Try to get CSRF from cookie (most reliable)
    csrf = sess.cookies.get('csrftoken')
    if csrf:
        return {"csrf": csrf, "cookies": sess.cookies.get_dict()}
    
    # Fallback: extract from HTML
    html = resp.text
    # Try to find csrf in a meta tag or script
    match = re.search(r'"csrf_token":"([^"]+)"', html)
    if match:
        csrf = match.group(1)
        return {"csrf": csrf, "cookies": sess.cookies.get_dict()}
    
    # Last resort: look for __NEXT_DATA__ which may contain config
    match = re.search(r'<script[^>]*id="__NEXT_DATA__"[^>]*>([^<]+)</script>', html)
    if match:
        try:
            data = json.loads(match.group(1))
            csrf = data.get('props', {}).get('pageProps', {}).get('csrf_token')
            if csrf:
                return {"csrf": csrf, "cookies": sess.cookies.get_dict()}
        except:
            pass
    
    raise Exception("Could not obtain CSRF token. Blocked or wrong proxy.")

def generate_client_id() -> str:
    return f"wp-{''.join(random.choices('abcdef0123456789', k=10))}"

def create_account(proxy: Optional[str] = None) -> bool:
    # 1. Get CSRF and initial cookies
    try:
        shared = get_shared_data(proxy)
        csrf = shared['csrf']
        init_cookies = shared['cookies']
    except Exception as e:
        print(f"[!] Failed to get CSRF: {e}")
        return False

    # 2. Create session with proper headers
    sess = requests.Session()
    if proxy:
        sess.proxies = {'http': proxy, 'https': proxy}
    
    sess.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
        'X-CSRFToken': csrf,
        'X-Instagram-AJAX': '1',  # fallback; will be replaced if we have rollout
        'X-Requested-With': 'XMLHttpRequest',
        'Content-Type': 'application/x-www-form-urlencoded',
        'Referer': 'https://www.instagram.com/accounts/emailsignup/',
        'Origin': 'https://www.instagram.com',
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'same-origin',
    })
    
    # Set initial cookies
    for name, value in init_cookies.items():
        sess.cookies.set(name, value, domain='.instagram.com')
    
    # 3. Generate account data
    email = get_temp_email()
    fullname = generate_fullname()
    username = generate_username()
    password = "blac@123"
    ts = int(time.time())
    enc_password = f"#PWD_INSTAGRAM_BROWSER:10:{ts}:6:{password}"  # version 10 as of 2025-2026
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
        print(f"[!] Checkpoint – need verification (possibly phone): {username}")
        # Optional: handle email verification loop here
        return False
    elif 'spam' in str(result).lower():
        print(f"[!] Spam block – proxy flagged.")
        return False
    else:
        print(f"[?] Unknown response: {result}")
        return False

def main():
    print("Blac – Pure HTTP Instagram Account Creator (Fixed CSRF)")
    while True:
        proxy_dict = rotate_proxy()
        proxy_str = None
        if proxy_dict:
            user = proxy_dict.get('user', '')
            pwd = proxy_dict.get('pass', '')
            if user and pwd:
                proxy_str = f"http://{user}:{pwd}@{proxy_dict['host']}:{proxy_dict['port']}"
            else:
                proxy_str = f"http://{proxy_dict['host']}:{proxy_dict['port']}"
            print(f"[*] Using proxy: {proxy_dict['host']}:{proxy_dict['port']}")
        if create_account(proxy_str):
            delay = random.randint(120, 300)
        else:
            delay = random.randint(60, 120)
        print(f"[*] Waiting {delay}s...")
        time.sleep(delay)

if __name__ == "__main__":
    main()