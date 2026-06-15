#!/usr/bin/env python3
"""
Blac – Pure HTTP Instagram Account Creator
- Handles 429 by rotating proxies
- All requests go through proxy
- Realistic headers and delays
"""
import time
import random
import json
import re
import requests
from datetime import datetime, timedelta

PROXY_FILE = "proxies.txt"
WORKING_PROXIES = []   # will be loaded
BAD_PROXIES = set()

def load_proxies():
    global WORKING_PROXIES
    try:
        with open(PROXY_FILE, 'r') as f:
            lines = [line.strip() for line in f if line.strip() and not line.startswith('#')]
        WORKING_PROXIES = lines
        print(f"[*] Loaded {len(WORKING_PROXIES)} proxies")
    except FileNotFoundError:
        print("[!] proxies.txt not found")

def get_proxy():
    available = [p for p in WORKING_PROXIES if p not in BAD_PROXIES]
    if not available:
        return None
    return random.choice(available)

def mark_proxy_bad(proxy):
    BAD_PROXIES.add(proxy)
    print(f"[!] Marked bad: {proxy[:60]}...")

def random_delay(min_sec=0.5, max_sec=2):
    time.sleep(random.uniform(min_sec, max_sec))

def get_shared_data(proxy):
    """Fetch CSRF token using a realistic session through the proxy."""
    sess = requests.Session()
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
    
    # Step 1: Homepage
    print("[DEBUG] Fetching homepage...")
    resp = sess.get("https://www.instagram.com/", timeout=15)
    if resp.status_code != 200:
        raise Exception(f"Homepage returned {resp.status_code}")
    random_delay(1.5, 3)
    
    # Step 2: Signup page
    print("[DEBUG] Fetching signup page...")
    resp = sess.get("https://www.instagram.com/accounts/emailsignup/", timeout=15)
    if resp.status_code != 200:
        raise Exception(f"Signup page returned {resp.status_code}")
    
    # Extract CSRF from cookies
    csrf = sess.cookies.get('csrftoken')
    if csrf:
        print(f"[DEBUG] CSRF from cookie: {csrf[:10]}...")
        return csrf, sess.cookies.get_dict()
    
    # Fallback: search HTML
    html = resp.text
    match = re.search(r'"csrf_token":"([^"]+)"', html)
    if match:
        csrf = match.group(1)
        print(f"[DEBUG] CSRF from HTML: {csrf[:10]}...")
        return csrf, sess.cookies.get_dict()
    
    raise Exception("CSRF not found")

def generate_username():
    first = random.choice(["Rajesh","Priya","Amit","Neha","Vikram","Sneha","Rahul","Anjali"])
    last = random.choice(["Sharma","Verma","Gupta","Kumar","Singh","Patel","Reddy","Yadav"])
    base = first.lower() + last.lower()
    suffix = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=random.randint(2,4)))
    sep = random.choice(['.', '_', ''])
    username = (base + sep + suffix)[:30]
    return username

def generate_fullname():
    first = random.choice(["Rajesh","Priya","Amit","Neha","Vikram","Sneha","Rahul","Anjali"])
    last = random.choice(["Sharma","Verma","Gupta","Kumar","Singh","Patel","Reddy","Yadav"])
    return f"{first} {last}"

def get_temp_email():
    import string
    name = ''.join(random.choices(string.ascii_lowercase + string.digits, k=random.randint(8,12)))
    domain = random.choice(["1secmail.com", "1secmail.org", "1secmail.net"])
    return f"{name}@{domain}"

def get_instagram_code(email, timeout=180):
    name, domain = email.split('@')
    start = time.time()
    while time.time() - start < timeout:
        try:
            url = f"https://www.1secmail.com/api/v1/?action=getMessages&login={name}&domain={domain}"
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200 and resp.json():
                msg_id = resp.json()[0]['id']
                msg_url = f"https://www.1secmail.com/api/v1/?action=readMessage&login={name}&domain={domain}&id={msg_id}"
                msg = requests.get(msg_url).json()
                body = msg.get('body', '')
                code = re.search(r'\b(\d{6})\b', body)
                if code:
                    return code.group(1)
        except:
            pass
        time.sleep(5)
    raise Exception("Verification code not received")

def save_account(username, password, email, session_id, expiry, filename="accounts.json"):
    try:
        with open(filename, 'r') as f:
            accounts = json.load(f)
    except:
        accounts = []
    accounts.append({
        "username": username,
        "password": password,
        "email": email,
        "session_id": session_id,
        "session_expiry": expiry,
        "created_at": datetime.now().isoformat()
    })
    with open(filename, 'w') as f:
        json.dump(accounts, f, indent=2)
    print(f"[✓] Saved to {filename}")

def create_account(proxy):
    # Get CSRF and initial cookies
    try:
        csrf, cookies = get_shared_data(proxy)
    except Exception as e:
        print(f"[!] CSRF extraction failed: {e}")
        return False
    
    # Create session for the POST request
    sess = requests.Session()
    sess.proxies = {'http': proxy, 'https': proxy}
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
    for name, value in cookies.items():
        sess.cookies.set(name, value, domain='.instagram.com')
    
    # Generate account data
    email = get_temp_email()
    fullname = generate_fullname()
    username = generate_username()
    password = "blac@123"
    ts = int(time.time())
    enc_password = f"#PWD_INSTAGRAM_BROWSER:10:{ts}:6:{password}"
    client_id = f"wp-{''.join(random.choices('abcdef0123456789', k=10))}"
    
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
    
    # Submit
    try:
        resp = sess.post("https://www.instagram.com/accounts/web_create_ajax/", data=data, timeout=15)
        if resp.status_code == 429:
            print("[!] 429 Rate limit")
            return False
        if resp.status_code != 200:
            print(f"[!] HTTP {resp.status_code}: {resp.text[:200]}")
            return False
        result = resp.json()
    except Exception as e:
        print(f"[!] POST error: {e}")
        return False
    
    if result.get('account_created'):
        print(f"[✓] Account created: {username}")
        session_id = sess.cookies.get('sessionid', '')
        expiry = (datetime.now() + timedelta(days=30)).isoformat()
        save_account(username, password, email, session_id, expiry)
        return True
    elif result.get('checkpoint_url'):
        print(f"[!] Checkpoint required: {username}")
        return False
    else:
        print(f"[?] Response: {result}")
        return False

def main():
    load_proxies()
    if not WORKING_PROXIES:
        print("[!] No proxies. Exiting.")
        return
    print("Blac – Pure HTTP (429 resilient)")
    while True:
        proxy = get_proxy()
        if not proxy:
            print("[!] No proxies left. Add more to proxies.txt")
            time.sleep(60)
            continue
        print(f"[*] Trying proxy: {proxy[:80]}...")
        success = create_account(proxy)
        if success:
            delay = random.randint(120, 300)
            print(f"[✓] Success. Waiting {delay}s before next...")
        else:
            mark_proxy_bad(proxy)
            delay = random.randint(5, 15)
            print(f"[!] Failure. Retrying with new proxy in {delay}s...")
        time.sleep(delay)

if __name__ == "__main__":
    main()