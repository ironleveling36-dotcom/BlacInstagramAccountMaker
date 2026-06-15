#!/usr/bin/env python3
"""
Blac – Instagram Account Creator (Email verification – Fixed)
Uses hardcoded client_id, missing CSRF, and proper code field.
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
from blac_core.temp_mail import get_temp_email, get_inbox, read_message
from blac_core.session_saver import save_account

load_dotenv()

CLIENT_ID = 'X5uC6wALAAF-Lw3oSZE9kuY0mP_9'
IG_APP_ID = '936619743392459'

def generate_client_id():
    return CLIENT_ID

def get_verification_code(email: str, timeout: int = 180) -> str:
    """Wait for email and extract 6-digit code."""
    start = time.time()
    while time.time() - start < timeout:
        messages = get_inbox(email)
        for msg in messages:
            msg_id = msg.get('id')
            if not msg_id:
                continue
            body = read_message(email, msg_id).get('body', '')
            # Look for 6-digit number
            import re
            match = re.search(r'\b(\d{6})\b', body)
            if match:
                return match.group(1)
        time.sleep(5)
    raise Exception("Verification code not received")

def create_account(proxy: str = None) -> bool:
    sess = requests.Session()
    if proxy:
        sess.proxies = {'http': proxy, 'https': proxy}
    
    cookie = secrets.token_hex(8) * 2
    
    email = get_temp_email()
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
    
    # First attempt
    try:
        resp = sess.post('https://www.instagram.com/accounts/web_create_ajax/', data=data, headers=headers, timeout=15)
        if resp.status_code != 200:
            print(f"[!] Creation failed: HTTP {resp.status_code}")
            return False
        result = resp.json()
    except Exception as e:
        print(f"[!] Request error: {e}")
        return False
    
    # If account created immediately (no verification)
    if result.get('account_created', False):
        print(f"[✓] Account created (no verification): {username}")
        session_id = sess.cookies.get('sessionid', '')
        expiry = (datetime.now() + timedelta(days=30)).isoformat()
        save_account(username, password, email, session_id, expiry, "accounts.json")
        return True
    
    # Checkpoint – need verification
    if result.get('checkpoint_url') or result.get('errors'):
        print(f"[!] Verification required for: {username}")
        # Try to get code
        try:
            code = get_verification_code(email)
            print(f"[*] Extracted code: {code}")
        except Exception as e:
            print(f"[!] Failed to get code: {e}")
            return False
        
        # Determine the correct field name for the code
        # Try common field names
        code_fields = ['code', 'email_confirmation_code', 'confirmation_code', 'verification_code']
        success = False
        for field in code_fields:
            data[field] = code
            try:
                resp2 = sess.post('https://www.instagram.com/accounts/web_create_ajax/', data=data, headers=headers, timeout=15)
                if resp2.status_code != 200:
                    continue
                result2 = resp2.json()
                if result2.get('account_created', False):
                    success = True
                    break
                # If error indicates wrong field, continue
                if 'errors' in result2 and field in str(result2['errors']):
                    continue
                # If any other error, break
                if not result2.get('checkpoint_url'):
                    break
            except:
                continue
        
        if success:
            print(f"[✓] Account verified and created: {username}")
            session_id = sess.cookies.get('sessionid', '')
            expiry = (datetime.now() + timedelta(days=30)).isoformat()
            save_account(username, password, email, session_id, expiry, "accounts.json")
            return True
        else:
            print(f"[!] Invalid code or field. Last response: {result2 if 'result2' in locals() else 'none'}")
            return False
    
    print(f"[?] Unknown response: {result}")
    return False

def main():
    print("Blac – Instagram Account Creator (Email verification – Fixed)")
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