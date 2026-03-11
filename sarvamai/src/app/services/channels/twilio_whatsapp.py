# Twilio WhatsApp channel service
import httpx
from src.app.core.config import settings

def parse_twilio_request(form_data: dict):
	"""Parse incoming Twilio webhook for WhatsApp messages."""
	body = form_data.get("Body", "")
	num_media = int(form_data.get("NumMedia", 0))
	media_urls = [form_data.get(f"MediaUrl{i}") for i in range(num_media)]
	return body, media_urls

def send_whatsapp_reply(to: str, message: str):
	"""Send reply via Twilio WhatsApp API."""
	url = f"https://api.twilio.com/2010-04-01/Accounts/{settings.TWILIO_ACCOUNT_SID}/Messages.json"
	data = {
		"To": to,
		"From": settings.TWILIO_WHATSAPP_NUMBER,
		"Body": message
	}
	auth = (settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
	response = httpx.post(url, data=data, auth=auth)
	response.raise_for_status()
	return response.json()
