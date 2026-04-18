# Twilio WhatsApp channel service
import httpx
from app.core.config import settings

SUPPORTED_AUDIO_CONTENT_TYPES = {
	"audio/ogg",        # WhatsApp voice notes are commonly OGG/Opus
	"audio/opus",
	"audio/mpeg",       # .mp3
	"audio/mp3",
	"audio/wav",        # .wav
	"audio/x-wav",
	"audio/wave",
	"audio/aac",        # .aac
	"audio/mp4",        # .m4a often arrives as audio/mp4
	"audio/x-m4a",
	"audio/amr",        # .amr
	"application/ogg",  # some providers send OGG with application/*
}

def parse_twilio_request(form_data: dict):
	"""Parse incoming Twilio webhook for WhatsApp messages."""
	# Extract Body - handle both string and list (from form parsing)
	raw_body = form_data.get("Body") or ""
	if isinstance(raw_body, list):
		raw_body = raw_body[0] if raw_body else ""
	body = str(raw_body).strip()
	
	# Extract NumMedia - handle both string and list
	raw_num_media = form_data.get("NumMedia") or "0"
	if isinstance(raw_num_media, list):
		raw_num_media = raw_num_media[0] if raw_num_media else "0"
	num_media = int(raw_num_media or 0)

	media_urls = []
	media_content_types = []
	for i in range(num_media):
		url = form_data.get(f"MediaUrl{i}")
		# Handle list for URLs
		if isinstance(url, list):
			url = url[0] if url else None
		
		ctype = form_data.get(f"MediaContentType{i}") or ""
		# Handle list for content types
		if isinstance(ctype, list):
			ctype = ctype[0] if ctype else ""
		ctype = str(ctype).lower().strip()
		
		if url:
			media_urls.append(url)
			media_content_types.append(ctype)

	return body, media_urls, media_content_types

def send_whatsapp_reply(to: str, message: str):
	"""Send reply via Twilio WhatsApp API."""
	url = f"https://api.twilio.com/2010-04-01/Accounts/{settings.TWILIO_ACCOUNT_SID}/Messages.json"
	from_number = settings.TWILIO_WHATSAPP_NUMBER
	if not from_number.startswith("whatsapp:"):
		from_number = f"whatsapp:{from_number}"
	if not to.startswith("whatsapp:"):
		to = f"whatsapp:{to}"
	data = {
		"To": to,
		"From": from_number,
		"Body": message,
	}
	auth = (settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
	response = httpx.post(url, data=data, auth=auth, timeout=30.0)
	response.raise_for_status()
	return response.json()
