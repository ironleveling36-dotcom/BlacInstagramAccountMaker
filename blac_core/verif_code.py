import time
import re
from .temp_mail import get_inbox, read_message

def get_instagram_code(email: str, session=None, timeout: int = 180) -> str:
    start = time.time()
    while time.time() - start < timeout:
        messages = get_inbox(email)
        for msg in messages:
            msg_id = msg.get('id')
            if not msg_id:
                continue
            body = read_message(email, msg_id).get('body', '')
            match = re.search(r'\b(\d{6})\b', body)
            if match:
                return match.group(1)
        time.sleep(5)
    raise Exception("Verification code not received")