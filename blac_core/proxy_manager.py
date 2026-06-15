import random
import re
import os
from typing import Dict, List, Optional

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

def rotate_proxy() -> Optional[Dict]:
    if not PROXY_LIST:
        return None
    new = random.choice(PROXY_LIST)
    while hasattr(rotate_proxy, 'last') and new == rotate_proxy.last and len(PROXY_LIST) > 1:
        new = random.choice(PROXY_LIST)
    rotate_proxy.last = new
    return new

def mark_proxy_bad(proxy: Dict):
    if proxy in PROXY_LIST:
        PROXY_LIST.remove(proxy)
    print(f"[!] Removed bad proxy: {proxy['host']}:{proxy['port']}")