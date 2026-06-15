#!/usr/bin/env python3
"""Test all proxies from proxies.txt against Instagram signup page."""
import requests
import sys

def test_proxy(proxy_line):
    proxy_line = proxy_line.strip()
    if not proxy_line or proxy_line.startswith('#'):
        return None
    
    # Parse proxy string for requests
    if proxy_line.startswith('socks5://'):
        # SOCKS5 proxy (no auth assumed)
        proxy_url = proxy_line
    elif '://' in proxy_line:
        # http/https with optional auth
        proxy_url = proxy_line
    else:
        # host:port or host:port:user:pass
        parts = proxy_line.split(':')
        if len(parts) == 2:
            host, port = parts
            proxy_url = f"http://{host}:{port}"
        elif len(parts) == 4:
            host, port, user, pwd = parts
            proxy_url = f"http://{user}:{pwd}@{host}:{port}"
        else:
            return None
    
    proxies = {'http': proxy_url, 'https': proxy_url}
    try:
        r = requests.get('https://www.instagram.com/accounts/emailsignup/', proxies=proxies, timeout=10)
        if r.status_code == 200:
            return proxy_line
        else:
            print(f"  {proxy_line[:50]}... -> HTTP {r.status_code}")
            return None
    except Exception as e:
        print(f"  {proxy_line[:50]}... -> ERROR: {e}")
        return None

def main():
    print("Testing proxies from proxies.txt...")
    with open('proxies.txt', 'r') as f:
        lines = f.readlines()
    
    working = []
    for line in lines:
        if line.strip() and not line.startswith('#'):
            print(f"Testing {line.strip()[:50]}...")
            result = test_proxy(line)
            if result:
                working.append(result)
                print(f"  ✓ WORKING")
    
    print("\n" + "="*50)
    print(f"Working proxies ({len(working)}):")
    for p in working:
        print(p)
    print("="*50)
    print("Copy these working proxies into a new file, e.g., good_proxies.txt")
    print("Then update your proxies.txt to only include working ones.")

if __name__ == "__main__":
    main()