#!/usr/bin/env python3
"""
Script to analyze all k6 metrics and show what we're collecting vs. what's available
"""

import json
import sys
from collections import defaultdict

def analyze_k6_metrics():
    """Analyze all metrics collected by k6"""
    
    print("=== k6 Metrics Analysis ===\n")
    
    # Load the full k6 summary
    try:
        with open("output/summary.json", 'r') as f:
            metrics_data = []
            for line in f:
                try:
                    data = json.loads(line.strip())
                    if data.get('type') == 'Point':
                        metrics_data.append(data)
                except json.JSONDecodeError:
                    continue
    except FileNotFoundError:
        print("❌ No k6 summary.json found. Run a load test first.")
        return
    
    # Group metrics by type
    metrics_by_name = defaultdict(list)
    for data in metrics_data:
        metric_name = data.get('metric', 'unknown')
        metrics_by_name[metric_name].append(data)
    
    print(f"📊 Total k6 metrics collected: {len(metrics_by_name)}")
    print(f"📈 Total data points: {len(metrics_data)}")
    
    # Categorize metrics
    categories = {
        "HTTP Metrics": [],
        "Performance Metrics": [],
        "System Metrics": [],
        "Custom Metrics": [],
        "Other Metrics": []
    }
    
    http_metrics = ['http_req_duration', 'http_req_blocked', 'http_req_connecting', 
                   'http_req_sending', 'http_req_waiting', 'http_req_receiving',
                   'http_req_tls_handshaking', 'http_reqs', 'http_req_failed']
    
    performance_metrics = ['iteration_duration', 'iterations', 'vus', 'vus_max']
    
    system_metrics = ['data_sent', 'data_received']
    
    for metric_name in metrics_by_name.keys():
        if metric_name in http_metrics:
            categories["HTTP Metrics"].append(metric_name)
        elif metric_name in performance_metrics:
            categories["Performance Metrics"].append(metric_name)
        elif metric_name in system_metrics:
            categories["System Metrics"].append(metric_name)
        elif metric_name.startswith('custom_') or metric_name in ['checks', 'errors', 'failed_requests', 'successful_requests']:
            categories["Custom Metrics"].append(metric_name)
        else:
            categories["Other Metrics"].append(metric_name)
    
    # Show what we're currently using
    print(f"\n🔍 CURRENTLY USED METRICS:")
    current_metrics = [
        "http_req_duration", "http_req_failed", "http_reqs"
    ]
    
    for metric in current_metrics:
        if metric in metrics_by_name:
            data_points = len(metrics_by_name[metric])
            print(f"   ✅ {metric}: {data_points} data points")
        else:
            print(f"   ❌ {metric}: Not found")
    
    # Show all available metrics by category
    print(f"\n📋 ALL AVAILABLE k6 METRICS:")
    
    for category, metrics in categories.items():
        if metrics:
            print(f"\n  🏷️  {category}:")
            for metric in sorted(metrics):
                data_points = len(metrics_by_name[metric])
                print(f"    • {metric}: {data_points} data points")
    
    # Show detailed breakdown of key metrics
    print(f"\n🔬 DETAILED METRIC BREAKDOWN:")
    
    key_metrics = [
        'http_req_duration', 'http_req_blocked', 'http_req_connecting',
        'http_req_sending', 'http_req_waiting', 'http_req_receiving',
        'http_req_tls_handshaking', 'data_sent', 'data_received'
    ]
    
    for metric in key_metrics:
        if metric in metrics_by_name:
            data_points = metrics_by_name[metric]
            if data_points:
                # Get sample data point to understand structure
                sample = data_points[0]
                tags = sample.get('data', {}).get('tags', {})
                
                print(f"\n  📊 {metric}:")
                print(f"    Data points: {len(data_points)}")
                if tags:
                    print(f"    Tags: {list(tags.keys())}")
                
                # Show some sample values
                values = [dp.get('data', {}).get('value', 0) for dp in data_points[:5]]
                print(f"    Sample values: {values[:3]}...")

def show_k6_capabilities():
    """Show what k6 can collect that we're not using"""
    
    print(f"\n" + "="*80)
    print("🚀 k6 CAPABILITIES WE'RE NOT FULLY UTILIZING:")
    print("="*80)
    
    capabilities = {
        "HTTP Timing Breakdown": {
            "description": "Detailed timing for each phase of HTTP requests",
            "metrics": [
                "http_req_blocked - Time spent waiting for connection",
                "http_req_connecting - Time spent establishing TCP connection", 
                "http_req_sending - Time spent sending request",
                "http_req_waiting - Time spent waiting for server response",
                "http_req_receiving - Time spent receiving response",
                "http_req_tls_handshaking - Time spent on TLS handshake"
            ],
            "value": "Identify specific bottlenecks in request lifecycle"
        },
        
        "Data Transfer Metrics": {
            "description": "Network data transfer information",
            "metrics": [
                "data_sent - Total bytes sent",
                "data_received - Total bytes received"
            ],
            "value": "Analyze bandwidth usage and payload sizes"
        },
        
        "Virtual User Metrics": {
            "description": "Information about virtual users",
            "metrics": [
                "vus - Current number of virtual users",
                "vus_max - Maximum number of virtual users"
            ],
            "value": "Monitor load distribution and scaling"
        },
        
        "Custom Metrics": {
            "description": "User-defined metrics for specific analysis",
            "metrics": [
                "Custom counters, gauges, trends, and rates",
                "Business-specific metrics",
                "Application-specific performance indicators"
            ],
            "value": "Track application-specific performance"
        },
        
        "Thresholds and Checks": {
            "description": "Performance validation and assertions",
            "metrics": [
                "checks - Pass/fail results of assertions",
                "thresholds - Performance criteria validation"
            ],
            "value": "Automated performance validation"
        },
        
        "Error Tracking": {
            "description": "Detailed error information",
            "metrics": [
                "errors - Custom error tracking",
                "failed_requests - Request failure details"
            ],
            "value": "Identify and categorize failures"
        }
    }
    
    for category, info in capabilities.items():
        print(f"\n📋 {category}:")
        print(f"   Description: {info['description']}")
        print(f"   Metrics: {', '.join(info['metrics'])}")
        print(f"   Value: {info['value']}")

def show_enhancement_opportunities():
    """Show how we could enhance our analysis with more k6 data"""
    
    print(f"\n" + "="*80)
    print("💡 ENHANCEMENT OPPORTUNITIES:")
    print("="*80)
    
    enhancements = [
        {
            "area": "Network Analysis",
            "current": "Basic response time",
            "enhanced": "Detailed timing breakdown (DNS, TCP, TLS, transfer)",
            "benefit": "Identify specific network bottlenecks"
        },
        {
            "area": "Payload Analysis", 
            "current": "Response size average",
            "enhanced": "Detailed data transfer metrics",
            "benefit": "Optimize payload sizes and compression"
        },
        {
            "area": "Load Distribution",
            "current": "Basic VU count",
            "enhanced": "VU distribution and scaling patterns",
            "benefit": "Understand load distribution and scaling"
        },
        {
            "area": "Error Analysis",
            "current": "Basic error rate",
            "enhanced": "Detailed error categorization and patterns",
            "benefit": "Identify specific failure patterns"
        },
        {
            "area": "Custom Metrics",
            "current": "Standard k6 metrics only",
            "enhanced": "Application-specific performance indicators",
            "benefit": "Track business-relevant performance"
        }
    ]
    
    for enhancement in enhancements:
        print(f"\n🎯 {enhancement['area']}:")
        print(f"   Current: {enhancement['current']}")
        print(f"   Enhanced: {enhancement['enhanced']}")
        print(f"   Benefit: {enhancement['benefit']}")

if __name__ == "__main__":
    analyze_k6_metrics()
    show_k6_capabilities()
    show_enhancement_opportunities() 