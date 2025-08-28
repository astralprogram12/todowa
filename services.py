import requests
from config import FONNTE_TOKEN

def send_fonnte_message(target, message):
    """Sends a reply message using the Fonnte API."""
    headers = {'Authorization': FONNTE_TOKEN}
    payload = {'target': target, 'message': message}
    try:
        requests.post('https://api.fonnte.com/send', headers=headers, data=payload, timeout=10)
    except requests.RequestException as e:
        print(f"Error sending Fonnte message: {e}")