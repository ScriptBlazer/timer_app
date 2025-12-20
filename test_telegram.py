# #!/usr/bin/env python
# """Test Telegram bot connection"""
# import os
# import requests
# from dotenv import load_dotenv

# load_dotenv()

# bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
# chat_id = os.getenv('TELEGRAM_ADMIN_CHAT_ID')

# print("=" * 50)
# print("Telegram Connection Test")
# print("=" * 50)
# print(f"Bot Token: {bot_token[:10] + '...' if bot_token else 'NOT SET'}")
# print(f"Chat ID: {chat_id}")
# print()

# if not bot_token or not chat_id:
#     print("❌ ERROR: Telegram credentials not found in .env file")
#     print("Make sure TELEGRAM_BOT_TOKEN and TELEGRAM_ADMIN_CHAT_ID are set")
#     exit(1)

# # Test sending a simple message
# print("Testing Telegram API connection...")
# url = f"https://api.telegram.org/bot{bot_token}/sendMessage"

# payload = {
#     "chat_id": chat_id,
#     "text": "🧪 Test message from Timer App!\n\nIf you see this, Telegram is working! ✅"
# }

# try:
#     response = requests.post(url, json=payload, timeout=10)
    
#     print(f"Status Code: {response.status_code}")
#     print(f"Response: {response.text}")
#     print()
    
#     if response.status_code == 200:
#         print("✅ SUCCESS! Telegram message sent successfully!")
#         print("Check your Telegram - you should have received the test message.")
#     else:
#         error_data = response.json()
#         print("❌ FAILED to send message")
#         print(f"Error: {error_data.get('description', 'Unknown error')}")
        
#         if "chat not found" in error_data.get('description', '').lower():
#             print("\n💡 TIP: You need to start a conversation with your bot first!")
#             print("   1. Open Telegram")
#             print("   2. Search for your bot")
#             print("   3. Click 'Start' or send /start")
#             print("   4. Then try again")
        
# except Exception as e:
#     print(f"❌ ERROR: {e}")
#     import traceback
#     traceback.print_exc()

# print("=" * 50)

