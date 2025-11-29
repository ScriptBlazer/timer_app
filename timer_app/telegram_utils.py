"""Telegram notification utilities"""
import requests
import os
from django.conf import settings
from dotenv import load_dotenv


def send_telegram_approval_request(pending_registration, request):
    """Send Telegram message with approval buttons
    Returns: (success: bool, error_message: str or None)
    """
    # Ensure .env is loaded
    load_dotenv()
    
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    chat_id = os.getenv('TELEGRAM_ADMIN_CHAT_ID')
    
    if not bot_token or not chat_id:
        error_msg = "Telegram credentials not configured. Please check your .env file."
        print(f"⚠️ Warning: {error_msg}")
        print(f"Bot token exists: {bool(bot_token)}")
        print(f"Chat ID exists: {bool(chat_id)}")
        if bot_token:
            print(f"Bot token: {bot_token[:10]}...")
        print(f"Chat ID: {chat_id}")
        return False, error_msg
    
    # Build approval URLs
    base_url = request.build_absolute_uri('/').rstrip('/')
    approve_url = f"{base_url}/registration/approve/{pending_registration.approval_token}/"
    deny_url = f"{base_url}/registration/deny/{pending_registration.approval_token}/"
    
    # Message text
    message = (
        f"🔔 *New Registration Request*\n\n"
        f"*Username:* {pending_registration.username}\n"
        f"*Email:* {pending_registration.email}\n"
        f"*Requested:* {pending_registration.created_at.strftime('%Y-%m-%d %H:%M')}\n\n"
        f"Please approve or deny this registration:"
    )
    
    # Inline keyboard with approve/deny buttons
    keyboard = {
        "inline_keyboard": [
            [
                {"text": "✅ Approve", "url": approve_url},
                {"text": "❌ Deny", "url": deny_url}
            ]
        ]
    }
    
    # Send message
    try:
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "Markdown",
            "reply_markup": keyboard
        }
        
        print(f"📤 Sending Telegram message to chat {chat_id}...")
        response = requests.post(url, json=payload, timeout=10)
        
        if response.status_code != 200:
            print(f"❌ Telegram API error: Status {response.status_code}")
            print(f"Response: {response.text}")
            error_msg = "Failed to send Telegram notification."
            try:
                error_data = response.json()
                error_desc = error_data.get('description', '')
                print(f"Error details: {error_data}")
                
                # Check for specific errors
                if "chat not found" in error_desc.lower():
                    error_msg = (
                        "⚠️ Bot conversation not started! Please:\n"
                        "1. Open Telegram and search for: @berko_timer_app_bot\n"
                        "2. Click 'Start' or send /start to the bot\n"
                        "3. Then try resending the notification again"
                    )
                    print("\n⚠️ IMPORTANT: You need to start a conversation with your bot first!")
                    print("   1. Open Telegram")
                    print("   2. Search for: @berko_timer_app_bot")
                    print("   3. Click 'Start' or send /start")
                    print("   4. Then try resending the notification")
            except:
                pass
            return False, error_msg
        
        print(f"✅ Telegram message sent successfully!")
        return True, None
    except Exception as e:
        error_msg = f"Error sending Telegram message: {str(e)}"
        print(f"❌ {error_msg}")
        import traceback
        traceback.print_exc()
        return False, error_msg


def send_telegram_notification(message):
    """Send simple Telegram notification"""
    load_dotenv()  # Ensure .env is loaded
    
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    chat_id = os.getenv('TELEGRAM_ADMIN_CHAT_ID')
    
    if not bot_token or not chat_id:
        return False
    
    try:
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "Markdown"
        }
        
        response = requests.post(url, json=payload, timeout=10)
        
        if response.status_code != 200:
            print(f"Telegram API error: Status {response.status_code}")
            print(f"Response: {response.text}")
            return False
        
        return True
    except Exception as e:
        print(f"Error sending Telegram message: {e}")
        return False
