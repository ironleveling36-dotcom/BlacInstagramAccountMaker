import requests
import random
import string
import time

def get_temp_email() -> str:
    # Try 10minutemail first
    try:
        resp = requests.post("https://api.10minutemail.com/v2/email", timeout=10)
        if resp.status_code == 200:
            return resp.json().get('email')
    except:
        pass
    # Fallback to guerrillamail
    try:
        resp = requests.get("https://api.guerrillamail.com/ajax.php?f=get_email_address", timeout=10)
        if resp.status_code == 200:
            return resp.json().get('email_addr')
    except:
        pass
    # Final fallback to 1secmail
    name = ''.join(random.choices(string.ascii_lowercase + string.digits, k=random.randint(8,12)))
    domain = random.choice(["1secmail.com", "1secmail.org", "1secmail.net"])
    return f"{name}@{domain}"

def get_inbox(email: str) -> list:
    domain = email.split('@')[1]
    if '10minutemail' in domain:
        try:
            resp = requests.get(f"https://api.10minutemail.com/v2/email/{email}", timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                return [{'id': 0, 'from': data.get('from', ''), 'subject': data.get('subject', ''), 'body': data.get('body', '')}]
        except:
            pass
    elif 'guerrillamail' in domain:
        try:
            session = requests.Session()
            session.get("https://www.guerrillamail.com/")
            resp = session.get("https://api.guerrillamail.com/ajax.php?f=get_email_list&offset=0", timeout=10)
            if resp.status_code == 200:
                return resp.json().get('list', [])
        except:
            pass
    else:  # 1secmail
        name, dom = email.split('@')
        try:
            resp = requests.get(f"https://www.1secmail.com/api/v1/?action=getMessages&login={name}&domain={dom}", timeout=10)
            if resp.status_code == 200:
                return resp.json()
        except:
            pass
    return []

def read_message(email: str, msg_id: int) -> dict:
    domain = email.split('@')[1]
    if '10minutemail' in domain:
        # Already fetched full message in inbox call
        return {'body': ''}  # Placeholder
    elif 'guerrillamail' in domain:
        try:
            resp = requests.get(f"https://api.guerrillamail.com/ajax.php?f=fetch_email&email_id={msg_id}", timeout=10)
            if resp.status_code == 200:
                return resp.json()
        except:
            pass
    else:
        name, dom = email.split('@')
        try:
            resp = requests.get(f"https://www.1secmail.com/api/v1/?action=readMessage&login={name}&domain={dom}&id={msg_id}", timeout=10)
            if resp.status_code == 200:
                return resp.json()
        except:
            pass
    return {}