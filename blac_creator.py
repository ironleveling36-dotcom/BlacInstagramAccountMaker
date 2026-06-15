#!/usr/bin/env python3
"""
Blac – Last Test with Your Gmail (Manual Code Entry)
"""
import time
import random
import secrets
import requests
from user_agent import generate_user_agent

CLIENT_ID = 'X5uC6wALAAF-Lw3oSZE9kuY0mP_9'
IG_APP_ID = '936619743392459'

def create_account(proxy: str = None):
    print(f"[*] Using proxy: {proxy[:50] if proxy else 'None'}")
    
    sess = requests.Session()
    if proxy:
        sess.proxies = {'http': proxy, 'https': proxy}
    
    cookie = secrets.token_hex(8) * 2
    email = "blacff07@gmail.com"   # <-- YOUR GMAIL
    fullname = "Test User"
    username = "tester_" + ''.join(random.choices('abcdefghijklmnopqrstuvwxyz', k=6))
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
    resp = sess.post('https://www.instagram.com/accounts/web_create_ajax/', data=data, headers=headers, timeout=15)
    if resp.status_code != 200:
        print(f"[!] HTTP {resp.status_code}")
        return False
    result = resp.json()
    
    if result.get('account_created', False):
        print(f"[✓] Account created (no verification): {username}")
        return True
    
    if result.get('checkpoint_url') or result.get('errors'):
        print(f"[!] Verification required for: {username}")
        print(f"[*] Check your Gmail: {email} (including Spam folder)")
        code = input("Enter the 6-digit code (or press Enter to abort): ").strip()
        if len(code) == 6:
            data['code'] = code
            resp2 = sess.post('https://www.instagram.com/accounts/web_create_ajax/', data=data, headers=headers, timeout=15)
            if resp2.status_code == 200:
                result2 = resp2.json()
                if result2.get('account_created', False):
                    print(f"[✓] Account verified and created: {username}")
                    return True
                else:
                    print(f"[!] Verification failed: {result2}")
            else:
                print(f"[!] Code submission HTTP {resp2.status_code}")
        else:
            print("[!] No code entered.")
        return False
    
    print(f"[?] Unknown response: {result}")
    return False

if __name__ == "__main__":
    # Try with one of your proxies (or set to None)
    proxy = "http://g2rTXpNfPdcw2fzGtWKp62yH:nizar1elad2@hu-bud.pvdata.host:8080"
    create_account(proxy)