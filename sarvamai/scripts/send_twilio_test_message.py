"""Send a real WhatsApp test message via Twilio.

Usage:
  python scripts/send_twilio_test_message.py --to whatsapp:+91XXXXXXXXXX
  python scripts/send_twilio_test_message.py --to whatsapp:+91XXXXXXXXXX --menu
"""
import argparse
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from app.services.channels.twilio_whatsapp import send_whatsapp_reply


HELP_MENU = (
    "*Sahayak AI* — Government Scheme Assistant\n\n"
    "*8 Indian Government Schemes Available:*\n"
    "1. PMAY-U 2.0 — Housing for poor families\n"
    "2. PMJDY — Free bank accounts\n"
    "3. PMUY (Ujjwala) — Free LPG\n"
    "4. Ayushman Bharat — Health insurance\n"
    "5. NSAP — Pensions\n"
    "6. Sukanya Samriddhi — Girl child savings\n"
    "7. APY — Guaranteed pension\n"
    "8. Stand-Up India — Loans\n\n"
    "*Ask in any language (text or voice)*\n"
    "Examples: What is PMJDY? Tell me about Ayushman Bharat. मुझे कौन सी योजना चाहिए?"
)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--to", required=True, help="Destination, e.g. whatsapp:+91XXXXXXXXXX")
    parser.add_argument("--message", default="Twilio test from Sahayak AI ✅", help="Custom text message")
    parser.add_argument("--menu", action="store_true", help="Send the default help menu text")
    args = parser.parse_args()

    body = HELP_MENU if args.menu else args.message
    response = send_whatsapp_reply(to=args.to, message=body)
    print("Twilio send OK")
    print("Message SID:", response.get("sid"))
    print("Status:", response.get("status"))
    print("To:", response.get("to"))


if __name__ == "__main__":
    main()
