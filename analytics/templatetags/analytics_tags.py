from django import template
import json
from pathlib import Path

register = template.Library()


@register.simple_tag
def get_benchmark_results():
    """Load benchmark results from JSON file"""
    try:
        # Get the analytics app directory
        current_file = Path(__file__).resolve()
        analytics_dir = current_file.parent.parent  # analytics/
        benchmark_file = analytics_dir / 'benchmark_results.json'
        
        if benchmark_file.exists():
            with open(benchmark_file, 'r') as f:
                return json.load(f)
    except Exception:
        pass
    return None
