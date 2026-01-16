"""
Management command to test analytics view performance
Run: python manage.py test_analytics_performance
"""
from django.core.management.base import BaseCommand
from django.test import RequestFactory
from django.contrib.auth.models import User
from analytics.views import statistics
from django.db import connection, reset_queries
from django.conf import settings
import time
import json
import os
from pathlib import Path
from django.utils import timezone


class Command(BaseCommand):
    help = 'Test analytics view performance'

    def add_arguments(self, parser):
        parser.add_argument(
            '--username',
            type=str,
            help='Username to test with (default: first user)',
        )
        parser.add_argument(
            '--json',
            type=str,
            help='Save results to JSON file (for HTML consumption)',
        )

    def handle(self, *args, **options):
        # Get user
        if options['username']:
            try:
                user = User.objects.get(username=options['username'])
            except User.DoesNotExist:
                self.stdout.write(self.style.ERROR(f"User '{options['username']}' not found"))
                return
        else:
            user = User.objects.first()
            if not user:
                self.stdout.write(self.style.ERROR("No users found. Please create a user first."))
                return

        # Create a mock request
        factory = RequestFactory()
        request = factory.get('/analytics/')
        request.user = user

        # Enable query logging
        was_debug = settings.DEBUG
        settings.DEBUG = True
        reset_queries()

        # Time the view
        start_time = time.time()
        result_data = {
            'success': False,
            'error': None,
            'timestamp': timezone.now().isoformat(),
            'user': user.username,
        }
        
        try:
            response = statistics(request)
            calculation_time = time.time() - start_time
            
            # Get query info
            queries = connection.queries
            query_count = len(queries)
            total_query_time = sum(float(q.get('time', 0)) for q in queries)
            avg_query_time = (total_query_time / query_count * 1000) if query_count > 0 else 0
            
            # Show query breakdown
            query_types = {}
            query_details = []
            for q in queries:
                sql = q.get('sql', '').upper().strip()
                query_time = float(q.get('time', 0))
                if sql.startswith('SELECT'):
                    query_types['SELECT'] = query_types.get('SELECT', 0) + 1
                elif sql.startswith('INSERT'):
                    query_types['INSERT'] = query_types.get('INSERT', 0) + 1
                elif sql.startswith('UPDATE'):
                    query_types['UPDATE'] = query_types.get('UPDATE', 0) + 1
                elif sql.startswith('DELETE'):
                    query_types['DELETE'] = query_types.get('DELETE', 0) + 1
                else:
                    query_types['OTHER'] = query_types.get('OTHER', 0) + 1
                
                # Store query details (limit to first 50 for JSON size)
                if len(query_details) < 50:
                    query_details.append({
                        'sql': q.get('sql', '')[:200] + ('...' if len(q.get('sql', '')) > 200 else ''),
                        'time': round(query_time, 4),
                        'type': sql.split()[0] if sql else 'OTHER'
                    })
            
            # Get context data
            context_data = {}
            if hasattr(response, 'context_data'):
                context = response.context_data
                context_data = {
                    'total_sessions': context.get('total_sessions', 0),
                    'total_time_seconds': context.get('total_time_seconds', 0),
                    'total_time_hours': round(context.get('total_time_seconds', 0) / 3600, 2),
                    'total_cost': float(context.get('total_cost', 0)),
                    'this_week_hours': round(context.get('this_week_hours', 0), 2),
                    'this_week_cost': float(context.get('this_week_cost', 0)),
                }
            
            # Check if targets met
            target_queries = 20
            target_time_ms = 100
            passed = query_count < target_queries and calculation_time < 0.1
            
            # Build result data
            result_data.update({
                'success': True,
                'performance': {
                    'total_queries': query_count,
                    'total_query_time_seconds': round(total_query_time, 4),
                    'total_query_time_ms': round(total_query_time * 1000, 2),
                    'average_query_time_ms': round(avg_query_time, 2),
                    'calculation_time_seconds': round(calculation_time, 4),
                    'calculation_time_ms': round(calculation_time * 1000, 2),
                },
                'targets': {
                    'query_count': target_queries,
                    'calculation_time_ms': target_time_ms,
                    'passed': passed,
                },
                'query_breakdown': query_types,
                'query_details': query_details,
                'context_data': context_data,
            })
            
            # Console output
            self.stdout.write("\n" + "="*60)
            self.stdout.write(self.style.SUCCESS("ANALYTICS PERFORMANCE TEST RESULTS"))
            self.stdout.write("="*60)
            self.stdout.write(self.style.SUCCESS("✅ View executed successfully"))
            self.stdout.write(f"\n📊 Performance Metrics:")
            self.stdout.write(f"   • Total Queries: {query_count}")
            self.stdout.write(f"   • Total Query Time: {total_query_time:.4f}s")
            if query_count > 0:
                self.stdout.write(f"   • Average Query Time: {avg_query_time:.2f}ms")
            self.stdout.write(f"   • Calculation Time: {calculation_time:.4f}s ({calculation_time*1000:.2f}ms)")
            self.stdout.write(f"\n🎯 Targets:")
            self.stdout.write(f"   • Target Queries: <{target_queries}")
            self.stdout.write(f"   • Target Time: <{target_time_ms}ms")
            
            if passed:
                self.stdout.write(self.style.SUCCESS(f"\n✅ PASSED - All targets met!"))
            else:
                self.stdout.write(self.style.WARNING(f"\n❌ NEEDS IMPROVEMENT"))
                if query_count >= target_queries:
                    self.stdout.write(self.style.WARNING(f"   ⚠️  Query count ({query_count}) exceeds target ({target_queries})"))
                if calculation_time >= 0.1:
                    self.stdout.write(self.style.WARNING(f"   ⚠️  Calculation time ({calculation_time*1000:.2f}ms) exceeds target ({target_time_ms}ms)"))
            self.stdout.write("="*60)
            
            self.stdout.write(f"\n📈 Query Breakdown:")
            for qtype, count in sorted(query_types.items()):
                self.stdout.write(f"   • {qtype}: {count}")
            
            if context_data:
                self.stdout.write(f"\n📦 Context Data:")
                self.stdout.write(f"   • Total Sessions: {context_data.get('total_sessions', 'N/A')}")
                self.stdout.write(f"   • Total Time: {context_data.get('total_time_hours', 0)} hours")
                self.stdout.write(f"   • Total Cost: ${context_data.get('total_cost', 0):.2f}")
            
            # Save to JSON if requested
            if options.get('json'):
                json_path = Path(options['json'])
                json_path.parent.mkdir(parents=True, exist_ok=True)
                with open(json_path, 'w') as f:
                    json.dump(result_data, f, indent=2)
                self.stdout.write(self.style.SUCCESS(f"\n💾 Results saved to: {json_path}"))
            
        except Exception as e:
            error_msg = str(e)
            result_data.update({
                'success': False,
                'error': error_msg,
            })
            self.stdout.write(self.style.ERROR(f"\n❌ Error: {e}"))
            import traceback
            self.stdout.write(traceback.format_exc())
        finally:
            settings.DEBUG = was_debug
        
        # Return result data for use in views
        return result_data
