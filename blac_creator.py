#!/usr/bin/env python3
"""
Blac – Instagram Account Creator (Adapted from working Telegram bot)
Uses hardcoded client_id, missing CSRF, and simple enc_password.
No CSRF extraction needed – just direct POST.
"""
import time
import random
import json
import secrets
import requests
from datetime import datetime, timedelta
from user_agent import generate_user_agent
from dotenv import load_dotenv

from blac_core.proxy_manager import rotate_proxy, mark_proxy_bad
from blac_core.account_generator import generate_username, generate_fullname
from blac_core.temp_mail import get_temp_email, get_inbox
from blac_core.verif_code import get_instagram_code
from blac_core.session_saver import save_account

load_dotenv()

# Hardcoded values that work (from working bot)
CLIENT_ID = 'X5uC6wALAAF-Lw3oSZE9kuY0mP_9'
IG_APP_ID = '936619743392459'

def generate_client_id():
    # Return the same hardcoded one – it's static and works
    return CLIENT_ID

def create_account(proxy: str = None) -> bool:
    sess = requests.Session()
    if proxy:
        sess.proxies = {'http': proxy, 'https': proxy}
    
    # Generate random cookie (works without a real session)
    cookie = secrets.token_hex(8) * 2
    
    # Generate account data
    email = get_temp_email()
    fullname = generate_fullname()
    username = generate_username()
    password = "blac@123"
    # Use version 0 (like the working bot) – not timestamped
    enc_password = f"#PWD_INSTAGRAM_BROWSER:0:1589682409:{password}"
    
    # Headers – exactly as in working bot (no CSRF, no AJAX header)
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
    
    # Step 1: Attempt (same as working bot)
    data1 = {
        'enc_password': enc_password,
        'email': email,
        'username': username,
        'first_name': fullname,
        'month': '1',
        'day': '1',
        'year': '1999',
        'client_id': CLIENT_ID,
        'seamless_login_enabled': '1',
        'opt_into_one_tap': 'false'
    }
    
    try:
        resp = sess.post('https://www.instagram.com/accounts/web_create_ajax/attempt/', data=data1, headers=headers, timeout=15)
        if resp.status_code != 200:
            print(f"[!] Attempt failed: HTTP {resp.status_code}")
            return False
        # Attempt response usually contains a checkpoint or success flag
    except Exception as e:
        print(f"[!] Attempt request error: {e}")
        return False
    
    # Step 2: Actually create the account (same endpoint as working bot's final step)
    # Note: The working bot uses different endpoints for phone (send_sms) then final create.
    # For email, we directly post to the main creation endpoint with the email.
    # We'll use the same data but without phone_number, and rely on email verification later.
    data3 = {
        'enc_password': enc_password,
        'email': email,
        'username': username,
        'first_name': fullname,
        'month': '1',
        'day': '1',
        'year': '1999',
        'client_id': CLIENT_ID,
        'seamless_login_enabled': '1',
        'tos_version': 'row'
    }
    
    try:
        resp = sess.post('https://www.instagram.com/accounts/web_create_ajax/', data=data3, headers=headers, timeout=15)
        if resp.status_code != 200:
            print(f"[!] Creation failed: HTTP {resp.status_code}")
            return False
        result = resp.json()
    except Exception as e:
        print(f"[!] Creation request error: {e}")
        return False
    
    # Check response
    if result.get('account_created', False):
        print(f"[✓] Account created: {username}")
        # Get session ID from cookies (if any)
        session_id = sess.cookies.get('sessionid', '')
        expiry = (datetime.now() + timedelta(days=30)).isoformat()
        save_account(username, password, email, session_id, expiry, "accounts.json")
        return True
    elif result.get('checkpoint_url'):
        print(f"[!] Checkpoint required – need email verification: {username}")
        # Try to extract and enter the verification code (email)
        code = get_instagram_code(email, sess)
        if code:
            print(f"[*] Got code: {code}")
            # Resubmit with code (similar to phone flow)
            data3['email_confirmation_code'] = code
            resp2 = sess.post('https://www.instagram.com/accounts/web_create_ajax/', data=data3, headers=headers, timeout=15)
            if resp2.status_code == 200 and resp2.json().get('account_created', False):
                print(f"[✓] Account verified and created: {username}")
                session_id = sess.cookies.get('sessionid', '')
                save_account(username, password, email, session_id, expiry, "accounts.json")
                return True
        return False
    else:
        print(f"[?] Unknown response: {result}")
        return False

def main():
    print("Blac – Instagram Account Creator (No CSRF extraction)")
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