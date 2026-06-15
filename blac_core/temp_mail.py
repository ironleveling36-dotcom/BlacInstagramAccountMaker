import requests
import random
import string
import time

def get_temp_email() -> str:
    # Use temp-mail.io API (works better than guerrillamail)
    try:
        resp = requests.get("https://api.temp-mail.io/request/domains/format/json", timeout=10)
        if resp.status_code == 200:
            domains = resp.json()
            domain = random.choice(domains)
            name = ''.join(random.choices(string.ascii_lowercase + string.digits, k=random.randint(8,12)))
            email = f"{name}@{domain}"
            return email
    except:
        pass
    # Fallback to 1secmail
    name = ''.join(random.choices(string.ascii_lowercase + string.digits, k=random.randint(8,12)))
    domain = random.choice(["1secmail.com", "1secmail.org", "1secmail.net"])
    return f"{name}@{domain}"

def get_inbox(email: str) -> list:
    domain = email.split('@')[1]
    # temp-mail.io
    if 'temp-mail.io' in domain or domain in ['guerrillamail.com', 'guerrillamail.net']:
        try:
            resp = requests.get(f"https://api.temp-mail.io/request/mail/id/{email}/format/json", timeout=10)
            if resp.status_code == 200:
                return resp.json()
        except:
            pass
    # 1secmail
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
    # temp-mail.io
    if 'temp-mail.io' in domain or domain in ['guerrillamail.com', 'guerrillamail.net']:
        try:
            resp = requests.get(f"https://api.temp-mail.io/request/mail/id/{email}/format/json", timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                # Find message by id (temp-mail.io returns a list)
                for msg in data:
                    if str(msg.get('mail_id')) == str(msg_id):
                        return msg
        except:
            pass
    # 1secmail
    name, dom = email.split('@')
    try:
        resp = requests.get(f"https://www.1secmail.com/api/v1/?action=readMessage&login={name}&domain={dom}&id={msg_id}", timeout=10)
        if resp.status_code == 200:
            return resp.json()
    except:
        pass
    return {}