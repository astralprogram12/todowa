"""
Third-Party Service Integrations.

This module encapsulates functions that interact with external, third-party APIs.
By centralizing these interactions, the application can easily manage and,
if necessary, replace service providers without altering the core business logic.
"""
import requests
from config import FONNTE_TOKEN

def send_fonnte_message(target: str, message: str):
    """
    Sends a reply message to a user via the Fonnte WhatsApp API.

    Args:
        target: The recipient's phone number or identifier.
        message: The text message to be sent.
    """
    headers = {'Authorization': FONNTE_TOKEN}
    payload = {'target': target, 'message': message}
    try:
        requests.post('https://api.fonnte.com/send', headers=headers, data=payload, timeout=10)
    except requests.RequestException as e:
        print(f"Error sending Fonnte message: {e}")