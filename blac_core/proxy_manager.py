import random
import re
import os
import requests
import urllib.parse
from typing import Optional, Dict, List

PROXY_FILE = "proxies.txt"

def parse_proxy_line(line: str) -> Optional[Dict]:
    line = line.strip()
    if not line or line.startswith('#'):
        return None
    # socks5://user:pass@host:port
    match = re.match(r'(?P<proto>socks5|socks4|http|https)://(?:(?P<user>[^:]+):(?P<pass>[^@]+)@)?(?P<host>[^:]+):(?P<port>\d+)', line)
    if match:
        return {
            "type": match.group('proto'),
            "host": match.group('host'),
            "port": int(match.group('port')),
            "user": match.group('user') or '',
            "pass": match.group('pass') or ''
        }
    parts = line.split(':')
    if len(parts) == 4:
        host, port, user, pwd = parts
        return {"type": "http", "host": host, "port": int(port), "user": user, "pass": pwd}
    if len(parts) == 2:
        host, port = parts
        return {"type": "http", "host": host, "port": int(port), "user": "", "pass": ""}
    return None

def load_proxies_from_file(filepath: str = PROXY_FILE) -> List[Dict]:
    proxies = []
    if not os.path.exists(filepath):
        return proxies
    with open(filepath, 'r') as f:
        for line in f:
            p = parse_proxy_line(line)
            if p:
                proxies.append(p)
    return proxies

PROXY_LIST = load_proxies_from_file()

def get_proxy() -> Optional[Dict]:
    return random.choice(PROXY_LIST) if PROXY_LIST else None

def rotate_proxy() -> Optional[Dict]:
    if len(PROXY_LIST) <= 1:
        return get_proxy()
    new = get_proxy()
    while new == getattr(rotate_proxy, '_last', None):
        new = get_proxy()
    rotate_proxy._last = new
    return new

def test_proxy(proxy: Dict, timeout: int = 10) -> bool:
    if not proxy:
        return True
    host = proxy['host']
    port = proxy['port']
    user = proxy.get('user', '')
    pwd = proxy.get('pass', '')
    if user and pwd:
        proxy_url = f"http://{user}:{pwd}@{host}:{port}"
    else:
        proxy_url = f"http://{host}:{port}"
    try:
        r = requests.get("https://api.ipify.org?format=json", proxies={"http": proxy_url, "https": proxy_url}, timeout=timeout)
        return r.status_code == 200
    except:
        return False

def get_proxy_stats() -> Dict:
    return {
        "total": len(PROXY_LIST),
        "http": sum(1 for p in PROXY_LIST if p['type'] == 'http'),
        "socks": sum(1 for p in PROXY_LIST if p['type'].startswith('socks')),
        "auth": sum(1 for p in PROXY_LIST if p['user'])
    }

def mark_proxy_bad(proxy: Dict):
    """Remove a proxy from the global list so it won't be reused."""
    if proxy in PROXY_LIST:
        PROXY_LIST.remove(proxy)
    print(f"[!] Removed bad proxy: {proxy['host']}:{proxy['port']}")