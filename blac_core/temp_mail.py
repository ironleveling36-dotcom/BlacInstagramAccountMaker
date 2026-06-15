import requests
import random
import string
import time

def get_temp_email() -> str:
    # Use 10minutemail's API (more reliable than 1secmail)
    try:
        resp = requests.post("https://api.10minutemail.com/v2/email", timeout=10)
        if resp.status_code == 200:
            return resp.json().get('email')
    except:
        pass
    # Fallback to 1secmail
    name = ''.join(random.choices(string.ascii_lowercase + string.digits, k=random.randint(8,12)))
    domain = random.choice(["1secmail.com", "1secmail.org", "1secmail.net"])
    return f"{name}@{domain}"

def get_inbox(email: str) -> list:
    try:
        domain = email.split('@')[1]
        if '1secmail' in domain:
            name, dom = email.split('@')
            url = f"https://www.1secmail.com/api/v1/?action=getMessages&login={name}&domain={dom}"
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200:
                return resp.json()
        elif '10minutemail' in domain:
            resp = requests.get(f"https://api.10minutemail.com/v2/email/{email}", timeout=10)
            if resp.status_code == 200:
                return [resp.json()]
    except:
        pass
    return []

def read_message(email: str, msg_id: int) -> dict:
    try:
        domain = email.split('@')[1]
        if '1secmail' in domain:
            name, dom = email.split('@')
            url = f"https://www.1secmail.com/api/v1/?action=readMessage&login={name}&domain={dom}&id={msg_id}"
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200:
                return resp.json()
        elif '10minutemail' in domain:
            # 10minutemail returns the whole message in one call
            return {'body': email.get('body', '')}
    except:
        pass
    return {}