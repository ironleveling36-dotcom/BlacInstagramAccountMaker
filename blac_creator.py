#!/usr/bin/env python3
"""
Blac – Instagram Account Creator (Email verification)
Uses temp-mail.io API for reliable temporary email.
"""
import time
import random
import json
import secrets
import requests
import re
from datetime import datetime, timedelta
from user_agent import generate_user_agent
from dotenv import load_dotenv

from blac_core.proxy_manager import rotate_proxy, mark_proxy_bad
from blac_core.account_generator import generate_username, generate_fullname
from blac_core.session_saver import save_account

load_dotenv()

CLIENT_ID = 'X5uC6wALAAF-Lw3oSZE9kuY0mP_9'
IG_APP_ID = '936619743392459'

def create_temp_email():
    """Create a temporary email using temp-mail.io API."""
    session = requests.Session()
    resp = session.get("https://api.temp-mail.io/request/domains/format/json")
    if resp.status_code != 200:
        raise Exception("Failed to get domains")
    domains = resp.json()
    domain = random.choice(domains)
    name = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=10))
    email = f"{name}@{domain}"
    return email, session

def wait_for_instagram_code(email, session, timeout=180):
    """Poll temp-mail.io inbox for Instagram code."""
    start = time.time()
    while time.time() - start < timeout:
        resp = session.get(f"https://api.temp-mail.io/request/mail/id/{email}/format/json")
        if resp.status_code == 200:
            messages = resp.json()
            for msg in messages:
                subject = msg.get('mail_subject', '')
                if 'instagram' in subject.lower():
                    body = msg.get('mail_text_only', '') or msg.get('mail_html', '')
                    match = re.search(r'\b(\d{6})\b', body)
                    if match:
                        return match.group(1)
        time.sleep(5)
    raise Exception("Code not received")

def create_account(proxy: str = None) -> bool:
    sess = requests.Session()
    if proxy:
        sess.proxies = {'http': proxy, 'https': proxy}
    
    cookie = secrets.token_hex(8) * 2
    
    try:
        email, mail_session = create_temp_email()
        print(f"[*] Temp email: {email}")
    except Exception as e:
        print(f"[!] Failed to create temp email: {e}")
        return False
    
    fullname = generate_fullname()
    username = generate_username()
    password = "blac@123"
    enc_password = f"#PWD_INSTAGRAM_BROWSER:0:1589682409:{password}"
    
    headers = {
        'Host': 'www.instagram.com',
        'KeepAlive': 'True',
        'User-Agent': generate_user_agent(),
        'Cookie': cookie,
        'Accept': '*/*',
        'Content-Type': 'application/x-www-form-urlencoded',
        'X-Requested-With': 'XMLHttpRequest',
        'X-IG-App-ID': IG_APP_ID,
        'X-Instagram-AJAX': 'missing',
        'X-CSRFToken': 'missing',
        'Accept-Language': 'en-US,en;q=0.9',
    }
    
    data = {
        'enc_password': enc_password,
        'email': email,
        'username': username,
        'first_name': fullname,
        'month': '1',
        'day': '1',
        'year': '1999',
        'client_id': CLIENT_ID,
        'seamless_login_enabled': '1',
        'opt_into_one_tap': 'false',
        'tos_version': 'row'
    }
    
    # First POST
    try:
        resp = sess.post('https://www.instagram.com/accounts/web_create_ajax/', data=data, headers=headers, timeout=15)
        if resp.status_code != 200:
            print(f"[!] HTTP {resp.status_code}")
            return False
        result = resp.json()
    except Exception as e:
        print(f"[!] Request error: {e}")
        return False
    
    if result.get('account_created', False):
        print(f"[✓] Account created (no verification): {username}")
        session_id = sess.cookies.get('sessionid', '')
        expiry = (datetime.now() + timedelta(days=30)).isoformat()
        save_account(username, password, email, session_id, expiry, "accounts.json")
        return True
    
    if result.get('checkpoint_url') or result.get('errors'):
        print(f"[!] Verification required for: {username}")
        try:
            code = wait_for_instagram_code(email, mail_session)
            print(f"[*] Got code: {code}")
        except Exception as e:
            print(f"[!] Code extraction failed: {e}")
            return False
        
        data['code'] = code
        try:
            resp2 = sess.post('https://www.instagram.com/accounts/web_create_ajax/', data=data, headers=headers, timeout=15)
            if resp2.status_code != 200:
                print(f"[!] Code submission HTTP {resp2.status_code}")
                return False
            result2 = resp2.json()
        except Exception as e:
            print(f"[!] Code submit error: {e}")
            return False
        
        if result2.get('account_created', False):
            print(f"[✓] Account verified and created: {username}")
            session_id = sess.cookies.get('sessionid', '')
            expiry = (datetime.now() + timedelta(days=30)).isoformat()
            save_account(username, password, email, session_id, expiry, "accounts.json")
            return True
        else:
            print(f"[!] Invalid code or other error: {result2}")
            return False
    
    print(f"[?] Unknown response: {result}")
    return False

def main():
    print("Blac – Instagram Account Creator (temp-mail.io)")
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