"""
Management command to check app health via URL and send Telegram notifications.
Usage: 
    python manage.py check_health              # Manual run - always sends Telegram
    python manage.py check_health --daily      # Daily report at 09:00
"""
from django.core.management.base import BaseCommand
from django.conf import settings
from django.utils import timezone
import os
import json
import requests

from timer.telegram_utils import send_telegram_notification


class Command(BaseCommand):
    help = 'Check app health via URL and send Telegram notifications'

    def add_arguments(self, parser):
        parser.add_argument(
            '--daily',
            action='store_true',
            help='Send daily health report (for 09:00 cron job)'
        )
        parser.add_argument(
            '--health-url',
            type=str,
            default=None,
            help='Health check URL (default: from HEALTH_CHECK_URL env or https://timer.samberko.co.uk/health/)'
        )

    def handle(self, *args, **options):
        # Get health check URL
        health_url = options.get('health_url') or os.getenv('HEALTH_CHECK_URL', 'https://timer.samberko.co.uk/health/')
        is_daily = options.get('daily', False)
        
        # Call health endpoint
        try:
            response = requests.get(health_url, timeout=10)
            response.raise_for_status()
            data = response.json()
            status = data.get('status', 'error')
            timestamp = data.get('timestamp', timezone.now().isoformat())
            errors = data.get('errors', [])
        except requests.exceptions.RequestException as e:
            status = 'error'
            timestamp = timezone.now().isoformat()
            errors = [f"Failed to reach health endpoint: {str(e)}"]
            self.stdout.write(self.style.ERROR(f'Error calling health endpoint: {e}'))
        except json.JSONDecodeError as e:
            status = 'error'
            timestamp = timezone.now().isoformat()
            errors = [f"Invalid JSON response: {str(e)}"]
            self.stdout.write(self.style.ERROR(f'Invalid JSON response: {e}'))
        
        # Format timestamp for display
        try:
            from datetime import datetime
            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            formatted_time = dt.strftime('%Y-%m-%d %H:%M:%S')
        except:
            formatted_time = timestamp
        
        # Build Telegram message
        if status == "ok":
            status_emoji = "✅"
            status_text = "OK"
            message = (
                f"{status_emoji} *Health Check: {status_text}*\n\n"
                f"Timer App is responding correctly.\n\n"
                f"*Status:* {status_text}\n"
                f"*Timestamp:* {formatted_time}"
            )
        else:
            status_emoji = "❌"
            status_text = "FAIL"
            error_details = "\n".join([f"• {error}" for error in errors]) if errors else "Unknown error"
            message = (
                f"{status_emoji} *Health Check: {status_text}*\n\n"
                f"Timer App is not responding correctly.\n\n"
                f"*Status:* {status_text}\n"
                f"*Timestamp:* {formatted_time}\n\n"
                f"*Errors:*\n{error_details}"
            )
        
        # Send Telegram notification
        # Always send Telegram notification (both manual runs and daily reports)
        success = send_telegram_notification(message)
        if success:
            if is_daily:
                self.stdout.write(self.style.SUCCESS(f'Daily health report sent: {status}'))
            else:
                self.stdout.write(self.style.SUCCESS(f'Health check completed: {status}. Telegram notification sent.'))
        else:
            if is_daily:
                self.stdout.write(self.style.ERROR(f'Daily health report failed to send: {status}'))
            else:
                self.stdout.write(self.style.ERROR(f'Health check completed: {status}, but failed to send Telegram notification.'))

