#!/usr/bin/env python
"""Get Telegram bot info"""
import os
import requests
from dotenv import load_dotenv

load_dotenv()

bot_token = os.getenv('TELEGRAM_BOT_TOKEN')

if not bot_token:
    print("ERROR: TELEGRAM_BOT_TOKEN not found in .env")
    exit(1)

print("Fetching bot information...")
url = f"https://api.telegram.org/bot{bot_token}/getMe"

try:
    response = requests.get(url, timeout=10)
    data = response.json()
    
    if data.get('ok'):
        bot_info = data['result']
        print("\n✅ Bot Information:")
        print(f"   Name: {bot_info.get('first_name')}")
        print(f"   Username: @{bot_info.get('username')}")
        print(f"   ID: {bot_info.get('id')}")
        print(f"\n🔍 Search for: @{bot_info.get('username')} in Telegram")
    else:
        print(f"❌ Error: {data.get('description')}")
except Exception as e:
    print(f"❌ Error: {e}")

