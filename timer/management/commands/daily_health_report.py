"""
Management command to send daily health report at 09:00.
Usage: python manage.py daily_health_report
This should be run via cron at 09:00 daily.
"""
from django.core.management.base import BaseCommand
from django.core.management import call_command


class Command(BaseCommand):
    help = 'Send daily health report (runs check_health with --daily flag)'

    def handle(self, *args, **options):
        # Call check_health with --daily flag
        call_command('check_health', '--daily')

