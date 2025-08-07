#!/usr/bin/env python3
"""
Simple script to parse k6 JSON results and display key metrics
"""

import json
import sys
from collections import defaultdict

def parse_k6_results(file_path):
    """Parse k6 JSON results file"""
    metrics = defaultdict(list)
    
    with open(file_path, 'r') as f:
        for line in f:
            try:
                data = json.loads(line.strip())
                if data.get('type') == 'Point':
                    metric_name = data.get('metric')
                    value = data.get('data', {}).get('value')
                    if metric_name and value is not None:
                        metrics[metric_name].append(value)
            except json.JSONDecodeError:
                continue
    
    return metrics

def calculate_stats(values):
    """Calculate basic statistics"""
    if not values:
        return {}
    
    values = [v for v in values if isinstance(v, (int, float))]
    if not values:
        return {}
    
    return {
        'count': len(values),
        'min': min(values),
        'max': max(values),
        'avg': sum(values) / len(values)
    }

def main():
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
    else:
        file_path = 'output/summary.json'
    
    print("=== POP Website Load Test Results ===\n")
    
    try:
        metrics = parse_k6_results(file_path)
        
        # Display key metrics
        if 'http_req_duration' in metrics:
            stats = calculate_stats(metrics['http_req_duration'])
            print(f"Response Time (ms):")
            print(f"  Average: {stats.get('avg', 0):.2f}")
            print(f"  Min: {stats.get('min', 0):.2f}")
            print(f"  Max: {stats.get('max', 0):.2f}")
            print(f"  Total Requests: {stats.get('count', 0)}")
            print()
        
        if 'http_reqs' in metrics:
            total_requests = len(metrics['http_reqs'])
            print(f"Total HTTP Requests: {total_requests}")
            print()
        
        if 'http_req_failed' in metrics:
            failed_requests = len([v for v in metrics['http_req_failed'] if v > 0])
            print(f"Failed Requests: {failed_requests}")
            if total_requests > 0:
                failure_rate = (failed_requests / total_requests) * 100
                print(f"Failure Rate: {failure_rate:.2f}%")
            print()
        
        # Show all available metrics
        print("Available Metrics:")
        for metric in sorted(metrics.keys()):
            count = len(metrics[metric])
            print(f"  {metric}: {count} data points")
        
    except FileNotFoundError:
        print(f"Error: File {file_path} not found")
    except Exception as e:
        print(f"Error parsing results: {e}")

if __name__ == "__main__":
    main() 