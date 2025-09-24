#!/usr/bin/env python3
"""
Generate HTML Report from k6 Summary Files
Creates a comprehensive HTML report from protocol and browser test results
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

def load_k6_summary(file_path):
    """Load k6 summary file - handles both JSONL and aggregated JSON formats"""
    try:
        # First, try to load as a single JSON object (aggregated format)
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
                # Check if this is the aggregated k6 summary format
                if isinstance(data, dict) and 'state' in data and 'metrics' in data:
                    print(f"Loaded aggregated k6 summary format from {file_path}")
                    return data
                else:
                    print(f"Loaded single JSON object from {file_path}")
                    return data
        except json.JSONDecodeError:
            pass
        
        # If that fails, try to load as JSONL (line-by-line JSON)
        try:
            data = []
            with open(file_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        data.append(json.loads(line))
            if data:
                print(f"Loaded JSONL format from {file_path} ({len(data)} lines)")
                return data
        except Exception:
            pass
        
        print(f"Error: Could not parse {file_path} as either JSON or JSONL")
        return None
        
    except Exception as e:
        print(f"Error loading {file_path}: {e}")
        return None

def extract_metrics(summary_data):
    """Extract comprehensive metrics from k6 summary data - handles both JSONL and aggregated formats"""
    metrics = {}
    
    if not summary_data:
        return metrics
    
    # Check if this is Playwright data format
    if isinstance(summary_data, dict) and 'playwright_summary' in summary_data:
        print(f"Processing Playwright summary format...")
        return extract_metrics_from_playwright(summary_data)
    
    # Check if this is aggregated k6 summary format
    if isinstance(summary_data, dict) and 'state' in summary_data and 'metrics' in summary_data:
        print(f"Processing aggregated k6 summary format...")
        return extract_metrics_from_aggregated(summary_data)
    
    # Handle JSONL format (original implementation)
    print(f"Processing {len(summary_data)} data points from JSONL...")
    
    # Group data points by metric type
    metric_groups = {}
    for item in summary_data:
        if item.get('type') == 'Point' and 'data' in item:
            metric_name = item.get('metric')
            if metric_name not in metric_groups:
                metric_groups[metric_name] = []
            metric_groups[metric_name].append(item['data'])
    
    print(f"Found metric groups: {list(metric_groups.keys())}")
    
    # 1. HTTP Request Counts and Throughput
    if 'http_reqs' in metric_groups:
        metrics['total_requests'] = len(metric_groups['http_reqs'])
        print(f"Total HTTP requests: {metrics['total_requests']}")
        
        # Calculate requests per second (approximate)
        if len(metric_groups['http_reqs']) > 1:
            first_time = metric_groups['http_reqs'][0].get('time', '')
            last_time = metric_groups['http_reqs'][-1].get('time', '')
            if first_time and last_time:
                try:
                    from datetime import datetime
                    start_dt = datetime.fromisoformat(first_time.replace('Z', '+00:00'))
                    end_dt = datetime.fromisoformat(last_time.replace('Z', '+00:00'))
                    duration = (end_dt - start_dt).total_seconds()
                    if duration > 0:
                        metrics['requests_per_second'] = len(metric_groups['http_reqs']) / duration
                        metrics['test_duration_seconds'] = duration
                except:
                    metrics['requests_per_second'] = 0.0
                    metrics['test_duration_seconds'] = 0
            else:
                metrics['requests_per_second'] = 0.0
                metrics['test_duration_seconds'] = 0
        else:
            metrics['requests_per_second'] = 0.0
            metrics['test_duration_seconds'] = 0
    
    # 2. HTTP Request Duration Analysis
    if 'http_req_duration' in metric_groups:
        durations = [point.get('value', 0) for point in metric_groups['http_req_duration']]
        if durations:
            durations.sort()
            metrics['avg_response_time'] = sum(durations) / len(durations)
            metrics['min_response_time'] = durations[0]
            metrics['max_response_time'] = durations[-1]
            
            # Calculate percentiles
            p50_index = int(len(durations) * 0.50)
            p75_index = int(len(durations) * 0.75)
            p90_index = int(len(durations) * 0.90)
            p95_index = int(len(durations) * 0.95)
            p99_index = int(len(durations) * 0.99)
            
            if p50_index < len(durations):
                metrics['p50_response_time'] = durations[p50_index]
            if p75_index < len(durations):
                metrics['p75_response_time'] = durations[p75_index]
            if p90_index < len(durations):
                metrics['p90_response_time'] = durations[p90_index]
            if p95_index < len(durations):
                metrics['p95_response_time'] = durations[p95_index]
            if p99_index < len(durations):
                metrics['p99_response_time'] = durations[p99_index]
        
        print(f"Response time metrics: {metrics.get('avg_response_time', 0):.0f}ms avg, {metrics.get('p95_response_time', 0):.0f}ms p95")
    
    # 3. Failure Rate Analysis
    if 'http_req_failed' in metric_groups:
        # Only count requests where value is not 0 (actual failures)
        failed_requests = len([point for point in metric_groups['http_req_failed'] if point.get('value', 0) > 0])
        total_requests = metrics.get('total_requests', 0)
        if total_requests > 0:
            metrics['error_rate'] = (failed_requests / total_requests) * 100
            metrics['failed_requests_count'] = failed_requests
            metrics['successful_requests_count'] = total_requests - failed_requests
        else:
            metrics['error_rate'] = 0.0
            metrics['failed_requests_count'] = 0
            metrics['successful_requests_count'] = 0
    
    # 4. Connection Breakdown Analysis
    connection_metrics = {}
    for metric in ['http_req_blocked', 'http_req_connecting', 'http_req_tls_handshaking', 'http_req_sending', 'http_req_waiting', 'http_req_receiving']:
        if metric in metric_groups:
            values = [point.get('value', 0) for point in metric_groups[metric]]
            if values:
                connection_metrics[metric] = {
                    'avg': sum(values) / len(values),
                    'min': min(values),
                    'max': max(values),
                    'p95': values[int(len(values) * 0.95)] if len(values) > 0 else 0
                }
    
    metrics['connection_breakdown'] = connection_metrics
    
    # 5. Data Transfer Analysis
    if 'data_received' in metric_groups:
        # Get the last data_received value (cumulative)
        if metric_groups['data_received']:
            metrics['data_received'] = metric_groups['data_received'][-1].get('value', 0)
            metrics['data_received_mb'] = metrics['data_received'] / 1024 / 1024
    
    if 'data_sent' in metric_groups:
        # Get the last data_sent value (cumulative)
        if metric_groups['data_sent']:
            metrics['data_sent'] = metric_groups['data_sent'][-1].get('value', 0)
            metrics['data_sent_mb'] = metrics['data_sent'] / 1024 / 1024
    
    # 6. Status Code Distribution
    status_codes = {}
    if 'http_reqs' in metric_groups:
        for req in metric_groups['http_reqs']:
            status = req.get('tags', {}).get('status', 'unknown')
            if status in status_codes:
                status_codes[status] += 1
            else:
                status_codes[status] = 1
    
    metrics['status_code_distribution'] = status_codes
    
    # 7. Virtual Users Analysis
    if 'vus' in metric_groups:
        # Get the last VU count
        if metric_groups['vus']:
            metrics['avg_vus'] = metric_groups['vus'][-1].get('value', 0)
    
    if 'vus_max' in metric_groups:
        # Get the max VU count
        if metric_groups['vus_max']:
            metrics['max_vus'] = metric_groups['vus_max'][-1].get('value', 0)
    
    # 8. Iteration Analysis
    if 'iterations' in metric_groups:
        # Get the last iterations value (cumulative)
        if metric_groups['iterations']:
            metrics['total_iterations'] = metric_groups['iterations'][-1].get('value', 0)
    
    if 'iteration_duration' in metric_groups:
        durations = [point.get('value', 0) for point in metric_groups['iteration_duration']]
        if durations:
            metrics['avg_iteration_duration'] = sum(durations) / len(durations)
            metrics['min_iteration_duration'] = min(durations)
            metrics['max_iteration_duration'] = max(durations)
    
    # 9. Performance Insights
    insights = []
    
    # Check for high latency
    if metrics.get('p95_response_time', 0) > 1000:
        insights.append({
            'type': 'high_latency',
            'severity': 'high',
            'message': f'P95 response time is {metrics.get("p95_response_time", 0):.0f}ms (>1000ms threshold)',
            'recommendation': 'Investigate server performance, database queries, or network issues'
        })
    
    # Check for high error rate
    if metrics.get('error_rate', 0) > 5:
        insights.append({
            'type': 'high_error_rate',
            'severity': 'high',
            'message': f'Error rate is {metrics.get("error_rate", 0):.1f}% (>5% threshold)',
            'recommendation': 'Investigate server errors, network issues, or application bugs'
        })
    
    # Check for connection issues
    if 'connection_breakdown' in metrics:
        conn = metrics['connection_breakdown']
        if 'http_req_connecting' in conn and conn['http_req_connecting']['avg'] > 100:
            insights.append({
                'type': 'connection_issues',
                'severity': 'medium',
                'message': f'Average connection time is {conn["http_req_connecting"]["avg"]:.0f}ms',
                'recommendation': 'Consider connection pooling, DNS optimization, or CDN'
            })
        
        if 'http_req_tls_handshaking' in conn and conn['http_req_tls_handshaking']['avg'] > 50:
            insights.append({
                'type': 'tls_issues',
                'severity': 'medium',
                'message': f'Average TLS handshake time is {conn["http_req_tls_handshaking"]["avg"]:.0f}ms',
                'recommendation': 'Enable TLS session resumption, optimize certificate chain'
            })
    
    # Check for large payloads
    if metrics.get('data_received_mb', 0) > 10:
        insights.append({
            'type': 'large_payloads',
            'severity': 'medium',
            'message': f'Total data received is {metrics.get("data_received_mb", 0):.1f}MB',
            'recommendation': 'Consider compression, pagination, or API optimization'
        })
    
    metrics['performance_insights'] = insights
    
    # 10. Performance Score
    score = 100
    deductions = 0
    
    # Deduct for high error rate
    if metrics.get('error_rate', 0) > 0:
        deductions += min(metrics.get('error_rate', 0) * 2, 40)  # Max 40 points for errors
    
    # Deduct for high latency
    if metrics.get('p95_response_time', 0) > 1000:
        latency_penalty = min((metrics.get('p95_response_time', 0) - 1000) / 100, 30)  # Max 30 points for latency
        deductions += latency_penalty
    
    # Deduct for connection issues
    if 'connection_breakdown' in metrics:
        conn = metrics['connection_breakdown']
        if 'http_req_connecting' in conn and conn['http_req_connecting']['avg'] > 100:
            deductions += 10
        if 'http_req_tls_handshaking' in conn and conn['http_req_tls_handshaking']['avg'] > 50:
            deductions += 10
    
    metrics['performance_score'] = max(0, score - deductions)
    
    print(f"Final metrics: {metrics}")
    return metrics

def extract_metrics_from_aggregated(summary_data):
    """Extract metrics from aggregated k6 summary format"""
    metrics = {}
    
    if not summary_data or not isinstance(summary_data, dict):
        return metrics
    
    state = summary_data.get('state', {})
    k6_metrics = summary_data.get('metrics', {})
    
    print(f"Processing aggregated k6 summary with {len(k6_metrics)} metric types...")
    
    # Extract basic state information
    metrics['test_duration'] = state.get('testRunDuration', '0ms')
    metrics['virtual_users'] = state.get('vus', 0)
    metrics['max_virtual_users'] = state.get('vusMax', 0)
    metrics['iterations'] = state.get('iterationCount', 0)
    
    # Extract HTTP metrics
    if 'http_reqs' in k6_metrics:
        http_reqs = k6_metrics['http_reqs']
        metrics['total_requests'] = http_reqs.get('count', 0)
        metrics['requests_per_second'] = http_reqs.get('rate', 0.0)
        
        # Calculate duration from testRunDuration
        duration_str = state.get('testRunDuration', '0ms')
        try:
            if 'm' in duration_str:
                minutes = int(duration_str.split('m')[0])
                seconds = int(duration_str.split('m')[1].replace('s', '')) if 's' in duration_str.split('m')[1] else 0
                metrics['test_duration_seconds'] = minutes * 60 + seconds
            elif 's' in duration_str:
                seconds = int(duration_str.replace('s', ''))
                metrics['test_duration_seconds'] = seconds
            else:
                metrics['test_duration_seconds'] = 0
        except:
            metrics['test_duration_seconds'] = 0
    
    # Extract response time metrics
    if 'http_req_duration' in k6_metrics:
        duration_metric = k6_metrics['http_req_duration']
        metrics['avg_response_time'] = duration_metric.get('avg', 0)
        metrics['min_response_time'] = duration_metric.get('min', 0)
        metrics['max_response_time'] = duration_metric.get('max', 0)
        metrics['p50_response_time'] = duration_metric.get('p(50)', 0)
        metrics['p75_response_time'] = duration_metric.get('p(75)', 0)
        metrics['p90_response_time'] = duration_metric.get('p(90)', 0)
        metrics['p95_response_time'] = duration_metric.get('p(95)', 0)
        metrics['p99_response_time'] = duration_metric.get('p(99)', 0)
        
        print(f"Response time metrics: {metrics.get('avg_response_time', 0):.0f}ms avg, {metrics.get('p95_response_time', 0):.0f}ms p95")
    
    # Extract failure rate
    if 'http_req_failed' in k6_metrics:
        failed_metric = k6_metrics['http_req_failed']
        # Use the sum (actual failed requests) instead of count
        failed_count = failed_metric.get('sum', 0)
        total_requests = metrics.get('total_requests', 0)
        
        if total_requests > 0:
            metrics['error_rate'] = (failed_count / total_requests) * 100
            metrics['failed_requests_count'] = failed_count
        else:
            metrics['error_rate'] = 0.0
            metrics['failed_requests_count'] = 0
    
    # Extract data transfer metrics
    if 'data_received' in k6_metrics:
        data_received = k6_metrics['data_received']
        metrics['data_received_bytes'] = data_received.get('sum', 0)
        metrics['data_received_rate'] = data_received.get('rate', 0.0)
    
    if 'data_sent' in k6_metrics:
        data_sent = k6_metrics['data_sent']
        metrics['data_sent_bytes'] = data_sent.get('sum', 0)
        metrics['data_sent_rate'] = data_sent.get('rate', 0.0)
    
    # Extract connection breakdown metrics for HTTP Request Breakdown chart
    connection_breakdown = {}
    if 'http_req_blocked' in k6_metrics:
        connection_breakdown['http_req_blocked'] = k6_metrics['http_req_blocked']
    if 'http_req_connecting' in k6_metrics:
        connection_breakdown['http_req_connecting'] = k6_metrics['http_req_connecting']
    if 'http_req_tls_handshaking' in k6_metrics:
        connection_breakdown['http_req_tls_handshaking'] = k6_metrics['http_req_tls_handshaking']
    if 'http_req_sending' in k6_metrics:
        connection_breakdown['http_req_sending'] = k6_metrics['http_req_sending']
    if 'http_req_waiting' in k6_metrics:
        connection_breakdown['http_req_waiting'] = k6_metrics['http_req_waiting']
    if 'http_req_receiving' in k6_metrics:
        connection_breakdown['http_req_receiving'] = k6_metrics['http_req_receiving']
    
    metrics['connection_breakdown'] = connection_breakdown
    
    # Extract iteration metrics
    if 'iterations' in k6_metrics:
        iterations = k6_metrics['iterations']
        metrics['iterations_count'] = iterations.get('count', 0)
        metrics['iterations_per_second'] = iterations.get('rate', 0.0)
    
    # Calculate comprehensive performance score for protocol tests
    score = 100.0
    deductions = 0
    deduction_reasons = []
    
    # 1. Error Rate Analysis (Critical)
    error_rate = metrics.get('error_rate', 0)
    if error_rate > 5:
        deductions += 30
        deduction_reasons.append(f"High error rate: {error_rate:.1f}%")
    elif error_rate > 1:
        deductions += 15
        deduction_reasons.append(f"Moderate error rate: {error_rate:.1f}%")
    elif error_rate > 0.5:
        deductions += 5
        deduction_reasons.append(f"Low error rate: {error_rate:.1f}%")
    
    # 2. Response Time Analysis (Critical)
    avg_response = metrics.get('avg_response_time', 0)
    p95_response = metrics.get('p95_response_time', 0)
    p99_response = metrics.get('p99_response_time', 0)
    
    if avg_response > 5000:  # > 5s
        deductions += 25
        deduction_reasons.append(f"Very slow avg response: {avg_response:.0f}ms")
    elif avg_response > 2000:  # > 2s
        deductions += 15
        deduction_reasons.append(f"Slow avg response: {avg_response:.0f}ms")
    elif avg_response > 1000:  # > 1s
        deductions += 10
        deduction_reasons.append(f"Moderate avg response: {avg_response:.0f}ms")
    elif avg_response > 500:   # > 500ms
        deductions += 5
        deduction_reasons.append(f"Above optimal avg response: {avg_response:.0f}ms")
    
    # P95 response time analysis
    if p95_response > 2000:  # > 2s
        deductions += 15
        deduction_reasons.append(f"High P95 response: {p95_response:.0f}ms")
    elif p95_response > 1000:  # > 1s
        deductions += 10
        deduction_reasons.append(f"Moderate P95 response: {p95_response:.0f}ms")
    elif p95_response > 500:   # > 500ms
        deductions += 5
        deduction_reasons.append(f"Above optimal P95 response: {p95_response:.0f}ms")
    
    # 3. Throughput Analysis
    rps = metrics.get('requests_per_second', 0)
    if rps < 10:
        deductions += 15
        deduction_reasons.append(f"Very low throughput: {rps:.1f} req/s")
    elif rps < 50:
        deductions += 10
        deduction_reasons.append(f"Low throughput: {rps:.1f} req/s")
    elif rps < 100:
        deductions += 5
        deduction_reasons.append(f"Below optimal throughput: {rps:.1f} req/s")
    
    # 4. Connection Performance Analysis
    if 'connection_breakdown' in metrics:
        conn = metrics['connection_breakdown']
        
        # DNS/Connection issues
        if 'http_req_connecting' in conn:
            connecting_avg = conn['http_req_connecting']['avg']
            if connecting_avg > 100:
                deductions += 10
                deduction_reasons.append(f"Slow DNS/connection: {connecting_avg:.1f}ms")
            elif connecting_avg > 50:
                deductions += 5
                deduction_reasons.append(f"Moderate DNS/connection: {connecting_avg:.1f}ms")
        
        # TLS handshake issues
        if 'http_req_tls_handshaking' in conn:
            tls_avg = conn['http_req_tls_handshaking']['avg']
            if tls_avg > 100:
                deductions += 10
                deduction_reasons.append(f"Slow TLS handshake: {tls_avg:.1f}ms")
            elif tls_avg > 50:
                deductions += 5
                deduction_reasons.append(f"Moderate TLS handshake: {tls_avg:.1f}ms")
        
        # Server processing time
        if 'http_req_waiting' in conn:
            waiting_avg = conn['http_req_waiting']['avg']
            if waiting_avg > 1000:  # > 1s
                deductions += 15
                deduction_reasons.append(f"Slow server processing: {waiting_avg:.1f}ms")
            elif waiting_avg > 500:  # > 500ms
                deductions += 10
                deduction_reasons.append(f"Moderate server processing: {waiting_avg:.1f}ms")
            elif waiting_avg > 200:  # > 200ms
                deductions += 5
                deduction_reasons.append(f"Above optimal server processing: {waiting_avg:.1f}ms")
    
    # 5. Data Transfer Efficiency
    data_received_mb = metrics.get('data_received_bytes', 0) / 1024 / 1024
    data_sent_mb = metrics.get('data_sent_bytes', 0) / 1024 / 1024
    total_requests = metrics.get('total_requests', 0)
    
    if total_requests > 0:
        avg_response_size_kb = (data_received_mb * 1024) / total_requests
        if avg_response_size_kb > 1000:  # > 1MB per response
            deductions += 10
            deduction_reasons.append(f"Large response size: {avg_response_size_kb:.1f}KB avg")
        elif avg_response_size_kb > 500:  # > 500KB per response
            deductions += 5
            deduction_reasons.append(f"Above optimal response size: {avg_response_size_kb:.1f}KB avg")
    
    # 6. Load Distribution Analysis
    max_vus = metrics.get('max_virtual_users', 0)
    virtual_users = metrics.get('virtual_users', 0)
    if max_vus > virtual_users * 1.5:  # Significant VU variation
        deductions += 5
        deduction_reasons.append(f"High VU variation: {virtual_users} -> {max_vus}")
    
    metrics['performance_score'] = max(0, score - deductions)
    metrics['performance_deductions'] = deduction_reasons
    
    print(f"Protocol performance score: {metrics['performance_score']:.0f} (deductions: {deductions})")
    if deduction_reasons:
        print(f"Deduction reasons: {', '.join(deduction_reasons)}")
    
    return metrics

def extract_metrics_from_playwright(summary_data):
    """Extract metrics from Playwright summary format"""
    metrics = {}
    
    if not summary_data or not isinstance(summary_data, dict):
        return metrics
    
    playwright_summary = summary_data.get('playwright_summary', {})
    
    print(f"Processing Playwright summary with {len(playwright_summary)} metrics...")
    
    # Extract basic test information
    metrics['test_duration_seconds'] = playwright_summary.get('test_duration', 0)
    metrics['total_vus'] = playwright_summary.get('total_vus', 0)
    metrics['max_vus'] = playwright_summary.get('total_vus', 0)  # Same as total for Playwright
    metrics['total_iterations'] = playwright_summary.get('total_iterations', 0)
    metrics['successful_iterations'] = playwright_summary.get('successful_iterations', 0)
    metrics['error_rate'] = playwright_summary.get('error_rate', 0.0)
    
    # Map Playwright metrics to k6-like metrics for report compatibility
    metrics['total_requests'] = playwright_summary.get('total_iterations', 0)  # Each iteration = 1 request
    metrics['requests_per_second'] = playwright_summary.get('total_iterations', 0) / max(playwright_summary.get('test_duration', 1), 1)
    
    # Browser-specific performance metrics
    metrics['avg_response_time'] = playwright_summary.get('avg_total_time', 0) * 1000  # Convert to ms
    metrics['min_response_time'] = playwright_summary.get('min_total_time', 0) * 1000
    metrics['max_response_time'] = playwright_summary.get('max_total_time', 0) * 1000
    
    # Core Web Vitals
    metrics['avg_first_contentful_paint'] = playwright_summary.get('avg_first_contentful_paint', 0)
    metrics['min_first_contentful_paint'] = playwright_summary.get('min_first_contentful_paint', 0)
    metrics['max_first_contentful_paint'] = playwright_summary.get('max_first_contentful_paint', 0)
    metrics['p95_first_contentful_paint'] = playwright_summary.get('p95_first_contentful_paint', 0)
    
    metrics['avg_dom_content_loaded'] = playwright_summary.get('avg_dom_content_loaded', 0)
    metrics['min_dom_content_loaded'] = playwright_summary.get('min_dom_content_loaded', 0)
    metrics['max_dom_content_loaded'] = playwright_summary.get('max_dom_content_loaded', 0)
    metrics['p95_dom_content_loaded'] = playwright_summary.get('p95_dom_content_loaded', 0)
    
    metrics['avg_load_complete'] = playwright_summary.get('avg_load_complete', 0)
    metrics['min_load_complete'] = playwright_summary.get('min_load_complete', 0)
    metrics['max_load_complete'] = playwright_summary.get('max_load_complete', 0)
    metrics['p95_load_complete'] = playwright_summary.get('p95_load_complete', 0)
    
    # Advanced Core Web Vitals (handle null values)
    lcp_avg = playwright_summary.get('avg_largest_contentful_paint', 0)
    metrics['avg_largest_contentful_paint'] = lcp_avg if lcp_avg is not None else 0
    metrics['min_largest_contentful_paint'] = playwright_summary.get('min_largest_contentful_paint', 0) or 0
    metrics['max_largest_contentful_paint'] = playwright_summary.get('max_largest_contentful_paint', 0) or 0
    metrics['p95_largest_contentful_paint'] = playwright_summary.get('p95_largest_contentful_paint', 0) or 0
    
    metrics['avg_cumulative_layout_shift'] = playwright_summary.get('avg_cumulative_layout_shift', 0) or 0
    metrics['min_cumulative_layout_shift'] = playwright_summary.get('min_cumulative_layout_shift', 0) or 0
    metrics['max_cumulative_layout_shift'] = playwright_summary.get('max_cumulative_layout_shift', 0) or 0
    
    fid_avg = playwright_summary.get('avg_first_input_delay', 0)
    metrics['avg_first_input_delay'] = fid_avg if fid_avg is not None else 0
    metrics['min_first_input_delay'] = playwright_summary.get('min_first_input_delay', 0) or 0
    metrics['max_first_input_delay'] = playwright_summary.get('max_first_input_delay', 0) or 0
    
    # Network Performance
    metrics['avg_time_to_first_byte'] = playwright_summary.get('avg_time_to_first_byte', 0)
    metrics['avg_dns_lookup'] = playwright_summary.get('avg_dns_lookup', 0)
    metrics['avg_tcp_connection'] = playwright_summary.get('avg_tcp_connection', 0)
    metrics['avg_ssl_handshake'] = playwright_summary.get('avg_ssl_handshake', 0)
    
    # Memory Usage (handle null values)
    metrics['avg_js_heap_used'] = playwright_summary.get('avg_js_heap_used', 0) or 0
    metrics['avg_js_heap_total'] = playwright_summary.get('avg_js_heap_total', 0) or 0
    metrics['avg_js_heap_limit'] = playwright_summary.get('avg_js_heap_limit', 0) or 0
    
    # Performance Metrics (handle null values)
    metrics['avg_total_blocking_time'] = playwright_summary.get('avg_total_blocking_time', 0) or 0
    metrics['avg_long_tasks_count'] = playwright_summary.get('avg_long_tasks_count', 0) or 0
    metrics['avg_layout_duration'] = playwright_summary.get('avg_layout_duration', 0) or 0
    metrics['avg_recalc_style_duration'] = playwright_summary.get('avg_recalc_style_duration', 0) or 0
    metrics['avg_script_duration'] = playwright_summary.get('avg_script_duration', 0) or 0
    metrics['avg_paint_duration'] = playwright_summary.get('avg_paint_duration', 0) or 0
    
    # Resource metrics
    metrics['avg_resource_count'] = playwright_summary.get('avg_resource_count', 0)
    metrics['min_resource_count'] = playwright_summary.get('min_resource_count', 0)
    metrics['max_resource_count'] = playwright_summary.get('max_resource_count', 0)
    
    metrics['avg_total_resource_size'] = playwright_summary.get('avg_total_resource_size', 0)
    metrics['min_total_resource_size'] = playwright_summary.get('min_total_resource_size', 0)
    metrics['max_total_resource_size'] = playwright_summary.get('max_total_resource_size', 0)
    
    # Calculate comprehensive browser performance score using ALL metrics
    score = 100.0
    deductions = 0
    deduction_reasons = []
    
    # 1. Core Web Vitals Analysis (Critical)
    lcp_score = playwright_summary.get('lcp_score', 0)
    fid_score = playwright_summary.get('fid_score', 0)
    cls_score = playwright_summary.get('cls_score', 0)
    
    if lcp_score < 75:
        deductions += 15
        deduction_reasons.append(f"Poor LCP score: {lcp_score}/100")
    elif lcp_score < 90:
        deductions += 5
        deduction_reasons.append(f"Below optimal LCP score: {lcp_score}/100")
    
    if fid_score < 75:
        deductions += 15
        deduction_reasons.append(f"Poor FID score: {fid_score}/100")
    elif fid_score < 90:
        deductions += 5
        deduction_reasons.append(f"Below optimal FID score: {fid_score}/100")
    
    if cls_score < 75:
        deductions += 15
        deduction_reasons.append(f"Poor CLS score: {cls_score}/100")
    elif cls_score < 90:
        deductions += 5
        deduction_reasons.append(f"Below optimal CLS score: {cls_score}/100")
    
    # 2. Page Load Performance Analysis (Critical)
    avg_response_time = metrics.get('avg_response_time', 0)
    if avg_response_time > 5000:  # > 5s
        deductions += 25
        deduction_reasons.append(f"Very slow page load: {avg_response_time:.0f}ms")
    elif avg_response_time > 3000:  # > 3s
        deductions += 20
        deduction_reasons.append(f"Slow page load: {avg_response_time:.0f}ms")
    elif avg_response_time > 2000:  # > 2s
        deductions += 15
        deduction_reasons.append(f"Above optimal page load: {avg_response_time:.0f}ms")
    elif avg_response_time > 1500:  # > 1.5s
        deductions += 10
        deduction_reasons.append(f"Moderate page load: {avg_response_time:.0f}ms")
    elif avg_response_time > 1000:  # > 1s
        deductions += 5
        deduction_reasons.append(f"Below optimal page load: {avg_response_time:.0f}ms")
    
    # 3. First Contentful Paint Analysis
    fcp = metrics.get('avg_first_contentful_paint', 0)
    if fcp > 3000:  # > 3s
        deductions += 15
        deduction_reasons.append(f"Very slow FCP: {fcp:.0f}ms")
    elif fcp > 1800:  # > 1.8s (Google's threshold)
        deductions += 10
        deduction_reasons.append(f"Slow FCP: {fcp:.0f}ms")
    elif fcp > 1200:  # > 1.2s
        deductions += 5
        deduction_reasons.append(f"Above optimal FCP: {fcp:.0f}ms")
    
    # 4. DOM Content Loaded Analysis
    dom_loaded = metrics.get('avg_dom_content_loaded', 0)
    if dom_loaded > 3000:  # > 3s
        deductions += 10
        deduction_reasons.append(f"Slow DOM loaded: {dom_loaded:.0f}ms")
    elif dom_loaded > 2000:  # > 2s
        deductions += 5
        deduction_reasons.append(f"Above optimal DOM loaded: {dom_loaded:.0f}ms")
    
    # 5. Network Performance Analysis
    ttfb = metrics.get('avg_time_to_first_byte', 0)
    if ttfb > 1000:  # > 1s
        deductions += 15
        deduction_reasons.append(f"Slow TTFB: {ttfb:.0f}ms")
    elif ttfb > 600:  # > 600ms
        deductions += 10
        deduction_reasons.append(f"Above optimal TTFB: {ttfb:.0f}ms")
    elif ttfb > 200:  # > 200ms
        deductions += 5
        deduction_reasons.append(f"Below optimal TTFB: {ttfb:.0f}ms")
    
    # DNS lookup analysis
    dns_lookup = metrics.get('avg_dns_lookup', 0)
    if dns_lookup > 100:  # > 100ms
        deductions += 5
        deduction_reasons.append(f"Slow DNS lookup: {dns_lookup:.1f}ms")
    
    # TCP connection analysis
    tcp_connection = metrics.get('avg_tcp_connection', 0)
    if tcp_connection > 200:  # > 200ms
        deductions += 5
        deduction_reasons.append(f"Slow TCP connection: {tcp_connection:.1f}ms")
    
    # SSL handshake analysis
    ssl_handshake = metrics.get('avg_ssl_handshake', 0)
    if ssl_handshake > 300:  # > 300ms
        deductions += 5
        deduction_reasons.append(f"Slow SSL handshake: {ssl_handshake:.1f}ms")
    
    # 6. Memory Usage Analysis
    js_heap_used = metrics.get('avg_js_heap_used', 0)
    js_heap_total = metrics.get('avg_js_heap_total', 0)
    js_heap_limit = metrics.get('avg_js_heap_limit', 0)
    
    if js_heap_used > 100000000:  # > 100MB
        deductions += 15
        deduction_reasons.append(f"High JS heap usage: {js_heap_used/1024/1024:.1f}MB")
    elif js_heap_used > 50000000:  # > 50MB
        deductions += 10
        deduction_reasons.append(f"Above optimal JS heap usage: {js_heap_used/1024/1024:.1f}MB")
    elif js_heap_used > 25000000:  # > 25MB
        deductions += 5
        deduction_reasons.append(f"Below optimal JS heap usage: {js_heap_used/1024/1024:.1f}MB")
    
    # Memory efficiency (used vs total)
    if js_heap_total > 0:
        memory_efficiency = (js_heap_used / js_heap_total) * 100
        if memory_efficiency > 90:  # > 90% memory usage
            deductions += 10
            deduction_reasons.append(f"High memory usage: {memory_efficiency:.1f}%")
        elif memory_efficiency > 75:  # > 75% memory usage
            deductions += 5
            deduction_reasons.append(f"Above optimal memory usage: {memory_efficiency:.1f}%")
    
    # 7. Resource Loading Analysis
    resource_count = metrics.get('avg_resource_count', 0)
    if resource_count > 100:  # > 100 resources
        deductions += 10
        deduction_reasons.append(f"High resource count: {resource_count:.0f}")
    elif resource_count > 50:  # > 50 resources
        deductions += 5
        deduction_reasons.append(f"Above optimal resource count: {resource_count:.0f}")
    
    total_resource_size = metrics.get('avg_total_resource_size', 0)
    if total_resource_size > 5000000:  # > 5MB
        deductions += 10
        deduction_reasons.append(f"Large resource size: {total_resource_size/1024/1024:.1f}MB")
    elif total_resource_size > 2000000:  # > 2MB
        deductions += 5
        deduction_reasons.append(f"Above optimal resource size: {total_resource_size/1024/1024:.1f}MB")
    
    # 8. Rendering Performance Analysis
    total_blocking_time = metrics.get('avg_total_blocking_time', 0)
    if total_blocking_time > 300:  # > 300ms
        deductions += 15
        deduction_reasons.append(f"High blocking time: {total_blocking_time:.0f}ms")
    elif total_blocking_time > 200:  # > 200ms
        deductions += 10
        deduction_reasons.append(f"Above optimal blocking time: {total_blocking_time:.0f}ms")
    elif total_blocking_time > 100:  # > 100ms
        deductions += 5
        deduction_reasons.append(f"Below optimal blocking time: {total_blocking_time:.0f}ms")
    
    long_tasks_count = metrics.get('avg_long_tasks_count', 0)
    if long_tasks_count > 10:  # > 10 long tasks
        deductions += 10
        deduction_reasons.append(f"High long tasks count: {long_tasks_count:.0f}")
    elif long_tasks_count > 5:  # > 5 long tasks
        deductions += 5
        deduction_reasons.append(f"Above optimal long tasks: {long_tasks_count:.0f}")
    
    # 9. Throughput Analysis
    requests_per_second = metrics.get('requests_per_second', 0)
    if requests_per_second < 1:  # < 1 req/s
        deductions += 10
        deduction_reasons.append(f"Very low browser throughput: {requests_per_second:.1f} req/s")
    elif requests_per_second < 2:  # < 2 req/s
        deductions += 5
        deduction_reasons.append(f"Low browser throughput: {requests_per_second:.1f} req/s")
    
    # Store individual Core Web Vitals scores
    metrics['lcp_score'] = lcp_score
    metrics['fid_score'] = fid_score
    metrics['cls_score'] = cls_score
    
    # Calculate final performance score
    metrics['performance_score'] = max(0, score - deductions)
    metrics['performance_deductions'] = deduction_reasons
    
    print(f"Browser performance score: {metrics['performance_score']:.0f} (deductions: {deductions})")
    if deduction_reasons:
        print(f"Deduction reasons: {', '.join(deduction_reasons)}")
    
    # Data transfer (estimate based on resource size)
    total_data = metrics['avg_total_resource_size'] * metrics['total_iterations']
    metrics['data_received_bytes'] = total_data
    metrics['data_received'] = total_data / 1024 / 1024  # Convert to MB
    
    print(f"Playwright metrics: {metrics.get('total_iterations', 0)} iterations, {metrics.get('avg_response_time', 0):.0f}ms avg response, {metrics.get('performance_score', 0):.0f} performance score")
    
    return metrics

def generate_recommendations_html(recommendations):
    """Generate HTML for recommendations"""
    if not recommendations:
        return '<p>No specific recommendations available.</p>'
    
    html_parts = []
    for rec in recommendations:
        priority_color = '#e74c3c' if rec.get('priority') == 'high' else '#f39c12' if rec.get('priority') == 'medium' else '#27ae60'
        
        actions_html = ''
        for action in rec.get('actions', []):
            actions_html += f'<li>{action}</li>'
        
        html_parts.append(f'''
        <div style="margin-bottom: 15px; padding: 10px; background: white; border-radius: 5px; border-left: 4px solid {priority_color};">
            <h4 style="margin: 0 0 5px 0; color: #2c3e50;">{rec.get('title', 'Recommendation')}</h4>
            <p style="margin: 0 0 10px 0; color: #7f8c8d;">{rec.get('description', '')}</p>
            <ul style="margin: 0; padding-left: 20px;">
                {actions_html}
            </ul>
        </div>
        ''')
    
    return '\n'.join(html_parts)

def generate_insights_html(insights):
    """Generate HTML for performance insights"""
    if not insights:
        return '<p>No specific performance insights available.</p>'
    
    html_parts = []
    for insight in insights:
        severity_color = '#e74c3c' if insight.get('severity') == 'high' else '#f39c12' if insight.get('severity') == 'medium' else '#27ae60'
        
        html_parts.append(f'''
        <div style="margin-bottom: 15px; padding: 10px; background: white; border-radius: 5px; border-left: 4px solid {severity_color};">
            <h4 style="margin: 0 0 5px 0; color: #2c3e50;">{insight.get('issue', 'Performance Issue')}</h4>
            <p style="margin: 0; color: #7f8c8d;">{insight.get('recommendation', '')}</p>
        </div>
        ''')
    
    return '\n'.join(html_parts)

def generate_resource_types_html(resource_counts):
    """Generate HTML for resource types breakdown"""
    if not resource_counts:
        return '<p>No resource type data available.</p>'
    
    html = ''
    for resource_type, count in resource_counts.items():
        html += f'''
        <div class="stat">
            <div class="label">{resource_type.title()}</div>
            <div class="value">{count:,}</div>
        </div>
        '''
    return html

def generate_resource_performance_issues_html(resource_analysis):
    """Generate HTML for resource performance issues"""
    if not resource_analysis or not resource_analysis.get('performance_issues'):
        return ''
    
    issues = resource_analysis['performance_issues']
    html = f'''
    <h3>Resource Performance Issues</h3>
    <div class="issues-list">
    '''
    
    for issue in issues:
        severity_class = f"severity-{issue['severity']}"
        severity_icon = "🔴" if issue['severity'] == 'critical' else "🟡" if issue['severity'] == 'high' else "🟠" if issue['severity'] == 'medium' else "🟢"
        
        html += f'''
        <div class="issue-item {severity_class}">
            <div class="issue-header">
                <span class="severity-icon">{severity_icon}</span>
                <span class="severity-badge">{issue['severity'].upper()}</span>
                <span class="issue-type">{issue['type'].replace('_', ' ').title()}</span>
            </div>
            <div class="issue-description">{issue['description']}</div>
            <div class="issue-impact"><strong>Impact:</strong> {issue['impact']}</div>
        </div>
        '''
    
    html += '''
    </div>
    '''
    
    return html

def generate_resource_recommendations_html(resource_analysis):
    """Generate HTML for resource optimization recommendations"""
    if not resource_analysis or not resource_analysis.get('recommendations'):
        return ''
    
    recommendations = resource_analysis['recommendations']
    html = f'''
    <h3>Resource Optimization Recommendations</h3>
    <div class="recommendations-list">
    '''
    
    for rec in recommendations:
        priority_class = f"priority-{rec['priority'].lower()}"
        priority_icon = "🔴" if rec['priority'] == 'Critical' else "🟡" if rec['priority'] == 'High' else "🟠" if rec['priority'] == 'Medium' else "🟢"
        
        html += f'''
        <div class="recommendation-item {priority_class}">
            <div class="recommendation-header">
                <span class="priority-icon">{priority_icon}</span>
                <span class="priority-badge">{rec['priority']}</span>
                <span class="recommendation-category">{rec['category']}</span>
            </div>
            <div class="recommendation-action"><strong>Action:</strong> {rec['action']}</div>
            <div class="recommendation-details">{rec['details']}</div>
        </div>
        '''
    
    html += '''
    </div>
    '''
    
    return html

def generate_performance_culprits_html(performance_culprits):
    """Generate HTML for performance culprits analysis"""
    if not performance_culprits:
        return ''
    
    html = '''
    <div class="card">
        <h2>🐌 Performance Culprits</h2>
        <p>Resources and requests that are impacting page load performance the most.</p>
    '''
    
    # Slowest Resources Section
    if performance_culprits.get('slowest_resources'):
        html += '''
        <h3>⏱️ Slowest Resources (>100ms)</h3>
        <div class="culprits-list">
        '''
        
        for i, resource in enumerate(performance_culprits['slowest_resources'][:10], 1):
            load_time = resource.get('loadTime', 0)
            resource_type = resource.get('resourceType', 'Unknown')
            url = resource.get('url', 'Unknown')
            size_kb = resource.get('size', 0) / 1024
            
            # Determine severity color
            if load_time > 1000:
                severity_class = 'critical'
                severity_icon = '🔴'
            elif load_time > 500:
                severity_class = 'high'
                severity_icon = '🟡'
            else:
                severity_class = 'medium'
                severity_icon = '🟠'
            
            html += f'''
            <div class="culprit-item {severity_class}">
                <div class="culprit-header">
                    <span class="culprit-rank">#{i}</span>
                    <span class="severity-icon">{severity_icon}</span>
                    <span class="resource-type">{resource_type}</span>
                    <span class="load-time">{load_time:.0f}ms</span>
                </div>
                <div class="culprit-details">
                    <div class="resource-url">{url}</div>
                    <div class="resource-size">Size: {size_kb:.1f}KB</div>
                </div>
            </div>
            '''
        
        html += '''
        </div>
        '''
    
    # Largest Resources Section
    if performance_culprits.get('largest_resources'):
        html += '''
        <h3>📦 Largest Resources (>100KB)</h3>
        <div class="culprits-list">
        '''
        
        for i, resource in enumerate(performance_culprits['largest_resources'][:10], 1):
            size_kb = resource.get('size', 0) / 1024
            resource_type = resource.get('resourceType', 'Unknown')
            url = resource.get('url', 'Unknown')
            load_time = resource.get('loadTime', 0)
            
            # Determine severity color based on size
            if size_kb > 1000:  # >1MB
                severity_class = 'critical'
                severity_icon = '🔴'
            elif size_kb > 500:  # >500KB
                severity_class = 'high'
                severity_icon = '🟡'
            else:
                severity_class = 'medium'
                severity_icon = '🟠'
            
            html += f'''
            <div class="culprit-item {severity_class}">
                <div class="culprit-header">
                    <span class="culprit-rank">#{i}</span>
                    <span class="severity-icon">{severity_icon}</span>
                    <span class="resource-type">{resource_type}</span>
                    <span class="resource-size">{size_kb:.1f}KB</span>
                </div>
                <div class="culprit-details">
                    <div class="resource-url">{url}</div>
                    <div class="load-time">Load Time: {load_time:.0f}ms</div>
                </div>
            </div>
            '''
        
        html += '''
        </div>
        '''
    
    # Request Breakdown Section
    if performance_culprits.get('most_requests_by_type'):
        html += '''
        <h3>📊 Requests by Type</h3>
        <div class="request-breakdown">
        '''
        
        for resource_type, count in list(performance_culprits['most_requests_by_type'].items())[:8]:
            html += f'''
            <div class="request-type">
                <span class="type-name">{resource_type}</span>
                <span class="type-count">{count} requests</span>
            </div>
            '''
        
        html += '''
        </div>
        '''
    
    # API Calls Summary
    if performance_culprits.get('api_calls'):
        api_calls = performance_culprits['api_calls']
        slow_apis = [api for api in api_calls if api.get('loadTime', 0) > 200]
        
        html += f'''
        <h3>🔗 API Calls Summary</h3>
        <div class="api-summary">
            <div class="api-stat">
                <span class="stat-label">Total API Calls:</span>
                <span class="stat-value">{len(api_calls)}</span>
            </div>
            <div class="api-stat">
                <span class="stat-label">Slow API Calls (>200ms):</span>
                <span class="stat-value">{len(slow_apis)}</span>
            </div>
        </div>
        '''
    
    # Performance Culprit Recommendations
    if performance_culprits.get('recommendations'):
        html += '''
        <h3>🎯 Recommendations</h3>
        <div class="culprit-recommendations">
        '''
        
        for rec in performance_culprits['recommendations']:
            priority_icon = "🔴" if rec['priority'] == 'High' else "🟡" if rec['priority'] == 'Medium' else "🟢"
            priority_class = rec['priority'].lower()
            
            html += f'''
            <div class="culprit-recommendation {priority_class}">
                <div class="recommendation-header">
                    <span class="priority-icon">{priority_icon}</span>
                    <span class="priority-badge">{rec['priority']}</span>
                    <span class="recommendation-title">{rec['title']}</span>
                </div>
                <div class="recommendation-description">{rec['description']}</div>
                <div class="recommendation-action"><strong>Action:</strong> {rec['action']}</div>
            </div>
            '''
        
        html += '''
        </div>
        '''
    
    html += '''
    </div>
    '''
    
    return html

def generate_enhanced_ai_analysis_section(enhanced_ai_analysis):
    """Generate HTML section for enhanced AI analysis results"""
    if not enhanced_ai_analysis:
        return ''
    
    # Check which format we're dealing with
    if 'ai_recommendations' in enhanced_ai_analysis:
        # Handle the older enhanced AI analysis format with structured recommendations
        return generate_structured_ai_analysis(enhanced_ai_analysis)
    elif 'ai_analysis' in enhanced_ai_analysis:
        # Handle the newer AI analysis format with raw insights
        return generate_insights_ai_analysis(enhanced_ai_analysis)
    else:
        return ''

def generate_structured_ai_analysis(enhanced_ai_analysis):
    """Generate HTML for the older structured AI analysis format"""
    ai_recommendations = enhanced_ai_analysis.get('ai_recommendations', {})
    if not ai_recommendations:
        return ''
    
    # Generate summary section
    summary = ai_recommendations.get('summary', {})
    overall_assessment = summary.get('overall_assessment', 'No assessment available')
    optimization_priority = summary.get('optimization_priority', 'Unknown')
    primary_concerns = summary.get('primary_concerns', [])
    
    # Generate recommendations HTML
    recommendations_html = ''
    recommendations = ai_recommendations.get('recommendations', [])
    for rec in recommendations:
        priority_icon = "🔴" if rec.get('priority') == 'Critical' else "🟡" if rec.get('priority') == 'High' else "🟢" if rec.get('priority') == 'Medium' else "🔵"
        effort_icon = "⚡" if rec.get('effort') == 'Low' else "🔧" if rec.get('effort') == 'Medium' else "🏗️"
        
        # Generate implementation steps
        steps_html = ''
        for step in rec.get('implementation_steps', []):
            steps_html += f'<li>{step}</li>'
        
        # Generate code examples if available
        code_examples_html = ''
        code_examples = rec.get('code_examples', [])
        if code_examples and isinstance(code_examples, list):
            for example in code_examples:
                if example.get('code'):
                    code_examples_html += f'''
                    <div class="code-example">
                        <h5>Code Example ({example.get('language', 'code')}):</h5>
                        <pre><code>{example.get('code', '')}</code></pre>
                        <p><em>{example.get('description', '')}</em></p>
                    </div>
                    '''
        elif code_examples and isinstance(code_examples, dict) and code_examples.get('code'):
            # Handle legacy format for backward compatibility
            code_examples_html = f'''
            <div class="code-example">
                <h5>Code Example ({code_examples.get('language', 'code')}):</h5>
                <pre><code>{code_examples.get('code', '')}</code></pre>
                <p><em>{code_examples.get('description', '')}</em></p>
            </div>
            '''
        
        recommendations_html += f'''
        <div class="ai-recommendation-item">
            <h4>{priority_icon} {rec.get('title', 'AI Recommendation')}</h4>
            <div class="recommendation-meta">
                <span class="category">📂 {rec.get('category', 'General')}</span>
                <span class="priority">🎯 {rec.get('priority', 'Medium')}</span>
                <span class="effort">{effort_icon} {rec.get('effort', 'Medium')} Effort</span>
            </div>
            <p><strong>Expected Impact:</strong> {rec.get('expected_impact', 'No impact description available')}</p>
            <div class="implementation-steps">
                <h5>Implementation Steps:</h5>
                <ul>{steps_html}</ul>
            </div>
            {code_examples_html}
            <div class="monitoring">
                <h5>📊 Monitoring:</h5>
                <p>{rec.get('monitoring', 'No monitoring guidance provided')}</p>
            </div>
        </div>
        '''
    
    # Generate primary concerns list
    concerns_html = ''
    if primary_concerns:
        concerns_html = f'''
        <div class="primary-concerns">
            <h4>🎯 Primary Performance Concerns</h4>
            <ul>
                {''.join([f'<li>{concern}</li>' for concern in primary_concerns])}
            </ul>
        </div>
        '''
    
    return f'''
    <div class="card" id="enhanced-ai-analysis">
        <h2>🤖 Enhanced AI Analysis
            <div class="tooltip-container">
                <span class="tooltip-icon">?</span>
                <div class="tooltip-content">
                    <h4>Enhanced AI Analysis</h4>
                    <p>AI-powered analysis using performance recommendations and site-specific technology tags.</p>
                    <p><span class="good-range">Good:</span> Targeted, actionable recommendations</p>
                    <p><span class="bad-range">Poor:</span> Generic or missing recommendations</p>
                    <p>Provides architecture-specific optimization guidance based on your technology stack.</p>
                </div>
            </div>
        </h2>
        
        <!-- AI Analysis Summary -->
        <div class="ai-summary">
            <h3>📊 Overall Assessment</h3>
            <p><strong>Assessment:</strong> {overall_assessment}</p>
            <p><strong>Optimization Priority:</strong> <span class="priority-{optimization_priority.lower()}">{optimization_priority}</span></p>
            {concerns_html}
        </div>
        
        <!-- AI Recommendations -->
        <div class="ai-recommendations">
            <h3>💡 AI-Powered Recommendations</h3>
            <p>Targeted recommendations based on your specific technology stack and performance issues.</p>
            {recommendations_html}
        </div>
    </div>
    '''

def generate_insights_ai_analysis(enhanced_ai_analysis):
    """Generate HTML for the newer insights-based AI analysis format"""
    ai_analysis = enhanced_ai_analysis.get('ai_analysis', {})
    performance_analysis = enhanced_ai_analysis.get('performance_analysis', {})
    technology_template = enhanced_ai_analysis.get('technology_template', {})
    
    if not ai_analysis:
        return ''
    
    # Extract key information from the actual data structure
    insights = ai_analysis.get('insights', 'No insights available')
    model_used = ai_analysis.get('model_used', 'Unknown')
    analysis_timestamp = ai_analysis.get('analysis_timestamp', 'Unknown')
    
    # Extract performance grade and score
    performance_grade = performance_analysis.get('performance_grade', 'Unknown')
    overall_score = performance_analysis.get('overall_score', 0)
    
    # Extract technology information
    tech_name = technology_template.get('name', 'Unknown Technology Stack')
    tech_description = technology_template.get('description', 'No description available')
    
    # Convert insights markdown to HTML (basic conversion)
    insights_html = insights.replace('\n', '<br>').replace('**', '<strong>').replace('**', '</strong>').replace('###', '<h3>').replace('####', '<h4>')
    
    return f'''
    <div class="card" id="enhanced-ai-analysis">
        <h2>🤖 Enhanced AI Analysis
            <div class="tooltip-container">
                <span class="tooltip-icon">?</span>
                <div class="tooltip-content">
                    <h4>Enhanced AI Analysis</h4>
                    <p>AI-powered analysis using performance recommendations and site-specific technology tags.</p>
                    <p><span class="good-range">Good:</span> Targeted, actionable recommendations</p>
                    <p><span class="bad-range">Poor:</span> Generic or missing recommendations</p>
                    <p>Provides architecture-specific optimization guidance based on your technology stack.</p>
                </div>
            </div>
        </h2>
        
        <!-- AI Analysis Summary -->
        <div class="ai-summary">
            <h3>📊 Overall Assessment</h3>
            <div class="performance-grade-display">
                <div class="grade-badge grade-{performance_grade.lower()}">{performance_grade}</div>
                <div class="score-display">{overall_score:.1f}/100</div>
            </div>
            <p><strong>Technology Stack:</strong> {tech_name}</p>
            <p><strong>Description:</strong> {tech_description}</p>
            <p><strong>Analysis Model:</strong> {model_used}</p>
            <p><strong>Analysis Time:</strong> {analysis_timestamp}</p>
        </div>
        
        <!-- AI Insights -->
        <div class="ai-insights">
            <h3>💡 AI Insights & Recommendations</h3>
            <div class="insights-content">
                {insights_html}
            </div>
        </div>
    </div>
    '''

def generate_html_report(protocol_metrics, browser_metrics, output_path, enhanced_ai_analysis=None):
    """Generate a comprehensive HTML report with Plotly visualizations"""
    
    # Load enhanced analysis reports if available
    enhanced_analysis = None
    browser_analysis = None
    
    output_dir = os.path.dirname(output_path)
    
    # Try to load enhanced performance analysis
    enhanced_file = os.path.join(output_dir, "enhanced_analysis_report.json")
    if os.path.exists(enhanced_file):
        try:
            with open(enhanced_file, 'r') as f:
                enhanced_analysis = json.load(f)
        except:
            pass
    
    # Try to load browser analysis
    browser_file = os.path.join(output_dir, "browser_analysis_report.json")
    if os.path.exists(browser_file):
        try:
            with open(browser_file, 'r') as f:
                browser_analysis = json.load(f)
        except:
            pass
    
    # Pre-format the values to avoid complex f-string expressions
    recommendations_html = generate_recommendations_html(enhanced_analysis.get('recommendations', [])) if enhanced_analysis else ''
    insights_html = generate_insights_html(browser_analysis.get('performance_insights', [])) if browser_analysis else ''
    
    # Generate enhanced analysis section
    enhanced_analysis_section = ''
    if enhanced_analysis:
        # Generate issues HTML
        issues_html = ''
        if enhanced_analysis.get('issues', {}).get('high'):
            issues_html += '''
                    <div class="metric">
                        <h3>High Priority Issues</h3>
                        <div class="value error-rate">{}</div>
                        <div class="unit">issues</div>
                    </div>
                    '''.format(len(enhanced_analysis.get('issues', {}).get('high', [])))
        if enhanced_analysis.get('issues', {}).get('medium'):
            issues_html += '''
                    <div class="metric">
                        <h3>Medium Priority Issues</h3>
                        <div class="value">{}</div>
                        <div class="unit">issues</div>
                    </div>
                    '''.format(len(enhanced_analysis.get('issues', {}).get('medium', [])))
        if enhanced_analysis.get('issues', {}).get('low'):
            issues_html += '''
                    <div class="metric">
                        <h3>Low Priority Issues</h3>
                        <div class="value">{}</div>
                        <div class="unit">issues</div>
                    </div>
                    '''.format(len(enhanced_analysis.get('issues', {}).get('low', [])))
        
        enhanced_analysis_section = '''
        <div class="test-section" id="enhanced-performance-analysis">
            <h3>Enhanced Performance Analysis</h3>
            <div class="card">
                <h2>Performance Summary</h2>
                <div class="summary-stats">
                    <div class="stat">
                        <div class="label">Performance Score</div>
                        <div class="value">{}/100</div>
                    </div>
                    <div class="stat">
                        <div class="label">Total Issues</div>
                        <div class="value">{}</div>
                    </div>
                    <div class="stat">
                        <div class="label">High Priority</div>
                        <div class="value error-rate">{}</div>
                    </div>
                    <div class="stat">
                        <div class="label">Medium Priority</div>
                        <div class="value">{}</div>
                    </div>
                </div>
                
                <h3>Performance Issues</h3>
                <div class="metrics-grid">
                    {}
                </div>
                
                <h3>Key Recommendations</h3>
                <div style="padding: 20px; background: #f8f9fa; border-radius: 8px; margin-top: 15px;">
                    {}
                </div>
            </div>
        </div>
        '''.format(
            enhanced_analysis.get('summary', {}).get('performance_score', 0),
            enhanced_analysis.get('summary', {}).get('total_issues', 0),
            enhanced_analysis.get('summary', {}).get('high_priority', 0),
            enhanced_analysis.get('summary', {}).get('medium_priority', 0),
            issues_html,
            recommendations_html
        )
    
    # Generate unified enhanced analysis section
    unified_enhanced_analysis_section = generate_unified_enhanced_analysis(enhanced_analysis, browser_metrics, protocol_metrics)
    
    # Generate enhanced AI analysis section
    enhanced_ai_analysis_section = generate_enhanced_ai_analysis_section(enhanced_ai_analysis)
    
    # Generate browser analysis section
    browser_analysis_section = ''
    if browser_analysis:
        # Extract browser metrics
        browser_summary = browser_analysis.get('summary', {})
        core_web_vitals = browser_analysis.get('core_web_vitals', {})
        resource_analysis = browser_analysis.get('resource_analysis', {})
        performance_insights = browser_analysis.get('performance_insights', [])
        
        # Generate performance insights HTML
        browser_insights_html = ''
        if performance_insights:
            for insight in performance_insights:
                severity_color = {'high': '#e74c3c', 'medium': '#f39c12', 'low': '#3498db'}.get(insight.get('severity', 'low'), '#3498db')
                browser_insights_html += f'''
                <div class="insight-item" style="border-left-color: {severity_color};">
                    <h4>{insight.get('title', 'Performance Issue')}</h4>
                    <p><strong>Description:</strong> {insight.get('description', 'No description available')}</p>
                    <p><strong>Recommendation:</strong> {insight.get('recommendation', 'No recommendation available')}</p>
                </div>
                '''
        
        browser_analysis_section = '''
        <div class="test-section browser-section" id="enhanced-browser-analysis">
            <h3>Enhanced Browser Performance Analysis</h3>
            
            <!-- Core Web Vitals Section -->
            <div class="card">
                <h2>Core Web Vitals</h2>
                <div class="metrics-grid">
                    <div class="metric">
                        <h3>Largest Contentful Paint</h3>
                        <div class="value">{lcp_ms:.0f}</div>
                        <div class="unit">ms</div>
                    </div>
                    <div class="metric">
                        <h3>First Contentful Paint</h3>
                        <div class="value">{fcp_ms:.0f}</div>
                        <div class="unit">ms</div>
                    </div>
                    <div class="metric">
                        <h3>Cumulative Layout Shift</h3>
                        <div class="value">{cls_score:.3f}</div>
                        <div class="unit">score</div>
                    </div>
                    <div class="metric">
                        <h3>Time to Interactive</h3>
                        <div class="value">{tti_ms:.0f}</div>
                        <div class="unit">ms</div>
                    </div>
                    <div class="metric">
                        <h3>First Input Delay</h3>
                        <div class="value">{fid_ms:.0f}</div>
                        <div class="unit">ms</div>
                    </div>
                    <div class="metric">
                        <h3>Total Blocking Time</h3>
                        <div class="value">{tbt_ms:.0f}</div>
                        <div class="unit">ms</div>
                    </div>
                    <div class="metric">
                        <h3>Performance Score</h3>
                        <div class="value">{performance_score:.0f}/100</div>
                        <div class="unit">score</div>
                    </div>
                </div>
            </div>
            
            <!-- Resource Analysis Section -->
            <div class="card">
                <h2>Resource Analysis</h2>
                <div class="metrics-grid">
                    <div class="metric">
                        <h3>Total Page Weight</h3>
                        <div class="value">{total_page_weight:.2f}</div>
                        <div class="unit">MB</div>
                    </div>
                    <div class="metric">
                        <h3>Total Requests</h3>
                        <div class="value">{total_requests:,}</div>
                        <div class="unit">requests</div>
                    </div>
                    <div class="metric">
                        <h3>Largest Resource</h3>
                        <div class="value">{largest_resource:.1f}</div>
                        <div class="unit">KB</div>
                    </div>
                    <div class="metric">
                        <h3>Average Resource Size</h3>
                        <div class="value">{avg_resource_size:.1f}</div>
                        <div class="unit">KB</div>
                    </div>
                </div>
                
                <!-- Resource Type Breakdown -->
                <h3>Resource Types</h3>
                <div class="summary-stats">
                    {resource_types_html}
                </div>
                
                <!-- Resource Performance Issues -->
                {resource_performance_issues_html}
                
                <!-- Resource Optimization Recommendations -->
                {resource_recommendations_html}
            </div>
            
            <!-- Performance Culprits Section -->
            {performance_culprits_html}
            
            <!-- Performance Issues Section -->
            <div class="card">
                <h2>Performance Issues</h2>
                <div class="summary-stats">
                    <div class="stat">
                        <div class="label">Total Issues</div>
                        <div class="value">{total_issues}</div>
                    </div>
                    <div class="stat">
                        <div class="label">High Severity</div>
                        <div class="value">{high_issues}</div>
                    </div>
                    <div class="stat">
                        <div class="label">Medium Severity</div>
                        <div class="value">{medium_issues}</div>
                    </div>
                    <div class="stat">
                        <div class="label">Low Severity</div>
                        <div class="value">{low_issues}</div>
                    </div>
                </div>
                
                <!-- Detailed Issues -->
                {browser_insights_html}
            </div>
        </div>
        '''.format(
            lcp_ms=browser_summary.get('lcp_ms', 0),
            fcp_ms=browser_summary.get('fcp_ms', 0),
            cls_score=browser_summary.get('cls_score', 0),
            tti_ms=browser_summary.get('tti_ms', 0),
            fid_ms=browser_summary.get('fid_ms', 0),
            tbt_ms=browser_summary.get('tbt_ms', 0),
            performance_score=browser_analysis.get('performance_score', 0),
            total_page_weight=browser_summary.get('total_page_weight_mb', 0),
            total_requests=browser_summary.get('total_requests', 0),
            largest_resource=resource_analysis.get('largest_resource_kb', 0),
            avg_resource_size=resource_analysis.get('average_resource_size_kb', 0),
            resource_types_html=generate_resource_types_html(resource_analysis.get('resource_counts', {})),
            resource_performance_issues_html=generate_resource_performance_issues_html(resource_analysis),
            resource_recommendations_html=generate_resource_recommendations_html(resource_analysis),
            performance_culprits_html=generate_performance_culprits_html(browser_analysis.get('performance_culprits', {})),
            total_issues=browser_summary.get('issues_count', 0),
            high_issues=browser_summary.get('high_severity_issues', 0),
            medium_issues=browser_summary.get('medium_severity_issues', 0),
            low_issues=browser_summary.get('low_severity_issues', 0),
            browser_insights_html=browser_insights_html
        )
    
    # Calculate success rate
    protocol_success_rate = 100 - protocol_metrics.get('error_rate', 0)
    browser_success_rate = 100 - browser_metrics.get('error_rate', 0)
    
    # Pre-format the values to avoid complex f-string expressions
    protocol_total_requests = f"{protocol_metrics.get('total_requests', 0):,}"
    protocol_avg_response = f"{protocol_metrics.get('avg_response_time', 0):.0f}"
    protocol_p95_response = f"{protocol_metrics.get('p95_response_time', 0):.0f}"
    protocol_p99_response = f"{protocol_metrics.get('p99_response_time', 0):.0f}"
    protocol_p50_response = f"{protocol_metrics.get('p50_response_time', 0):.0f}"
    protocol_p75_response = f"{protocol_metrics.get('p75_response_time', 0):.0f}"
    protocol_p90_response = f"{protocol_metrics.get('p90_response_time', 0):.0f}"
    protocol_requests_per_sec = f"{protocol_metrics.get('requests_per_second', 0):.1f}"
    protocol_data_received = f"{(protocol_metrics.get('data_received', 0) / 1024 / 1024):.1f}"
    protocol_data_sent = f"{(protocol_metrics.get('data_sent_bytes', 0) / 1024 / 1024):.1f}"
    protocol_avg_vus = f"{protocol_metrics.get('virtual_users', 0):.0f}"  # Use virtual_users as avg VUs
    protocol_total_iterations = f"{protocol_metrics.get('iterations', 0):,}"
    
    browser_total_requests = f"{browser_metrics.get('total_requests', 0):,}"
    browser_avg_response = f"{browser_metrics.get('avg_response_time', 0):.0f}"
    browser_p95_response = f"{browser_metrics.get('p95_response_time', 0):.0f}"
    browser_requests_per_sec = f"{browser_metrics.get('requests_per_second', 0):.1f}"
    browser_data_received = f"{(browser_metrics.get('data_received', 0) / 1024 / 1024):.1f}"
    
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Load Test Report - POP Website</title>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            background: #f8f9fa;
        }}
        
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
        }}
        
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px 20px;
            text-align: center;
            border-radius: 15px;
            margin-bottom: 30px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.1);
        }}
        
        .header h1 {{
            font-size: 2.8em;
            margin-bottom: 10px;
            font-weight: 700;
        }}
        
        .header .timestamp {{
            opacity: 0.9;
            font-size: 1.2em;
            margin-top: 10px;
        }}
        
        .card {{
            background: white;
            border-radius: 15px;
            padding: 30px;
            margin-bottom: 25px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.08);
            border: 1px solid #e9ecef;
        }}
        
        .card h2 {{
            color: #2c3e50;
            margin-bottom: 25px;
            font-size: 1.8em;
            border-bottom: 3px solid #3498db;
            padding-bottom: 15px;
            font-weight: 600;
        }}
        
        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 20px;
            margin: 25px 0;
        }}
        
        .metric {{
            background: linear-gradient(135deg, #ecf0f1 0%, #d5dbdb 100%);
            padding: 20px;
            border-radius: 12px;
            text-align: center;
            border-left: 4px solid #3498db;
        }}
        
        .metric h3 {{
            font-size: 0.9em !important;
            color: #7f8c8d !important;
            margin-bottom: 8px !important;
            font-weight: 500 !important;
            text-transform: none !important;
            letter-spacing: normal !important;
            line-height: 1.2 !important;
            margin-top: 0 !important;
        }}
        
        .metric .value {{
            font-size: 1.8em;
            font-weight: 700;
            color: #2c3e50;
        }}
        
        .metric .unit {{
            font-size: 0.8em;
            color: #7f8c8d;
            font-weight: 500;
            margin-top: 5px;
        }}
        
        .test-section {{
            margin-bottom: 35px;
        }}
        
        .test-section h3 {{
            color: #2c3e50;
            font-size: 2em;
            margin-bottom: 20px;
            display: flex;
            align-items: center;
            font-weight: 600;
        }}
        
        .test-section h3::before {{
            content: "";
            margin-right: 0;
            font-size: 1.5em;
        }}
        
        .browser-section h3::before {{
            content: "";
        }}
        
        /* Navigation Links */
        .navigation-links {{
            display: flex;
            flex-wrap: wrap;
            gap: 15px;
            margin-top: 20px;
        }}
        
        .nav-link {{
            display: inline-block;
            padding: 12px 20px;
            background: linear-gradient(135deg, #3498db 0%, #2980b9 100%);
            color: white;
            text-decoration: none;
            border-radius: 8px;
            font-weight: 600;
            transition: all 0.3s ease;
            box-shadow: 0 2px 8px rgba(52, 152, 219, 0.3);
        }}
        
        .nav-link:hover {{
            background: linear-gradient(135deg, #2980b9 0%, #1f5f8b 100%);
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(52, 152, 219, 0.4);
        }}
        
        .chart-container {{
            background: white;
            border-radius: 15px;
            padding: 25px;
            margin: 25px 0;
            box-shadow: 0 4px 15px rgba(0,0,0,0.08);
            border: 1px solid #e9ecef;
        }}
        
        .chart-container h3 {{
            color: #2c3e50;
            margin-bottom: 20px;
            font-size: 1.4em;
            font-weight: 600;
        }}
        
        .summary-stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 20px;
            margin: 25px 0;
        }}
        
        .stat {{
            background: linear-gradient(135deg, #ecf0f1 0%, #d5dbdb 100%);
            padding: 20px;
            border-radius: 12px;
            text-align: center;
            border-left: 4px solid #3498db;
        }}
        
        .stat .label {{
            font-size: 0.9em;
            color: #7f8c8d;
            margin-bottom: 8px;
            font-weight: 500;
        }}
        
        .stat .value {{
            font-size: 1.8em;
            font-weight: 700;
            color: #2c3e50;
        }}
        
        .success-rate {{
            color: #27ae60;
        }}
        
        .error-rate {{
            color: #e74c3c;
        }}
        
        .performance-grade {{
            background: linear-gradient(135deg, #27ae60 0%, #2ecc71 100%);
            color: white;
            border-radius: 12px;
            text-align: center;
            padding: 20px;
            border-left: 4px solid #27ae60;
        }}
        
        .performance-grade .label {{
            font-size: 0.9em;
            color: rgba(255, 255, 255, 0.9);
            margin-bottom: 8px;
            font-weight: 500;
        }}
        
        .performance-grade .score {{
            font-size: 2.5em;
            font-weight: 700;
            color: white;
        }}
        
        .insights-panel {{
            background: linear-gradient(135deg, #fff5f5 0%, #fed7d7 100%);
            border: 1px solid #feb2b2;
            border-radius: 12px;
            padding: 20px;
            margin: 20px 0;
        }}
        
        .insights-panel h3 {{
            color: #c53030;
            margin-bottom: 15px;
            font-size: 1.3em;
            font-weight: 600;
        }}
        
        .insight-item {{
            background: white;
            border-radius: 8px;
            padding: 15px;
            margin: 10px 0;
            border-left: 4px solid #e53e3e;
        }}
        
        .insight-item.high-priority {{
            border-left-color: #e53e3e;
        }}
        
        .insight-item.medium-priority {{
            border-left-color: #d69e2e;
        }}
        
        .insight-item.low-priority {{
            border-left-color: #38a169;
        }}
        
        .insight-item.success {{
            border-left-color: #38a169;
            background: #f0fff4;
        }}
        
        .recommendation-item {{
            background: white;
            border-radius: 8px;
            padding: 20px;
            margin: 20px 0;
            border-left: 4px solid #e53e3e;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        
        .recommendation-item:first-child {{
            margin-top: 0;
        }}
        
        .recommendation-item:last-child {{
            margin-bottom: 0;
        }}
        
        .recommendation-item.success {{
            border-left-color: #38a169;
            background: #f0fff4;
        }}
        
        /* Resource Analysis Styles */
        .issues-list {{
            margin: 20px 0;
        }}
        
        .issue-item {{
            background: white;
            border-radius: 8px;
            padding: 16px;
            margin: 12px 0;
            border-left: 4px solid #e53e3e;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        
        .issue-item.severity-critical {{
            border-left-color: #e53e3e;
            background: #fed7d7;
        }}
        
        .issue-item.severity-high {{
            border-left-color: #dd6b20;
            background: #feebc8;
        }}
        
        .issue-item.severity-medium {{
            border-left-color: #d69e2e;
            background: #faf089;
        }}
        
        .issue-item.severity-low {{
            border-left-color: #38a169;
            background: #c6f6d5;
        }}
        
        .issue-header {{
            display: flex;
            align-items: center;
            gap: 8px;
            margin-bottom: 8px;
        }}
        
        .severity-badge {{
            background: #e53e3e;
            color: white;
            padding: 2px 8px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: bold;
        }}
        
        .issue-type {{
            font-weight: 600;
            color: #2d3748;
        }}
        
        .issue-description {{
            margin-bottom: 8px;
            color: #4a5568;
        }}
        
        .issue-impact {{
            font-size: 14px;
            color: #718096;
        }}
        
        .recommendations-list {{
            margin: 20px 0;
        }}
        
        .recommendation-item {{
            background: white;
            border-radius: 8px;
            padding: 16px;
            margin: 12px 0;
            border-left: 4px solid #e53e3e;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        
        .recommendation-item.priority-critical {{
            border-left-color: #e53e3e;
            background: #fed7d7;
        }}
        
        .recommendation-item.priority-high {{
            border-left-color: #dd6b20;
            background: #feebc8;
        }}
        
        .recommendation-item.priority-medium {{
            border-left-color: #d69e2e;
            background: #faf089;
        }}
        
        .recommendation-item.priority-low {{
            border-left-color: #38a169;
            background: #c6f6d5;
        }}
        
        .recommendation-header {{
            display: flex;
            align-items: center;
            gap: 8px;
            margin-bottom: 8px;
        }}
        
        .priority-badge {{
            background: #e53e3e;
            color: white;
            padding: 2px 8px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: bold;
        }}
        
        .recommendation-category {{
            font-weight: 600;
            color: #2d3748;
        }}
        
        .recommendation-action {{
            margin-bottom: 8px;
            color: #4a5568;
        }}
        
        .recommendation-details {{
            font-size: 14px;
            color: #718096;
        }}
        
        /* Enhanced AI Analysis Styles */
        .ai-recommendation-item {{
            background: white;
            border-radius: 12px;
            padding: 25px;
            margin: 20px 0;
            border-left: 4px solid #8b5cf6;
            box-shadow: 0 2px 10px rgba(0,0,0,0.05);
            transition: transform 0.2s ease, box-shadow 0.2s ease;
        }}
        
        .ai-recommendation-item:hover {{
            transform: translateY(-2px);
            box-shadow: 0 4px 20px rgba(0,0,0,0.1);
        }}
        
        .recommendation-meta {{
            display: flex;
            gap: 15px;
            margin: 15px 0;
            flex-wrap: wrap;
        }}
        
        .recommendation-meta span {{
            background: #f8fafc;
            padding: 6px 12px;
            border-radius: 20px;
            font-size: 0.9em;
            font-weight: 500;
            color: #4a5568;
        }}
        
        .implementation-steps {{
            background: #f7fafc;
            border-radius: 8px;
            padding: 15px;
            margin: 15px 0;
        }}
        
        .implementation-steps h5 {{
            color: #2d3748;
            margin-bottom: 10px;
            font-size: 1.1em;
        }}
        
        .implementation-steps ul {{
            margin: 0;
            padding-left: 20px;
        }}
        
        .implementation-steps li {{
            margin: 8px 0;
            color: #4a5568;
        }}
        
        .code-example {{
            background: #1a202c;
            border-radius: 8px;
            padding: 20px;
            margin: 15px 0;
            color: #e2e8f0;
        }}
        
        .code-example h5 {{
            color: #63b3ed;
            margin-bottom: 10px;
            font-size: 1em;
        }}
        
        .code-example pre {{
            background: #2d3748;
            border-radius: 6px;
            padding: 15px;
            overflow-x: auto;
            margin: 10px 0;
        }}
        
        .code-example code {{
            color: #e2e8f0;
            font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
            font-size: 0.9em;
        }}
        
        .monitoring {{
            background: #edf2f7;
            border-radius: 8px;
            padding: 15px;
            margin: 15px 0;
        }}
        
        .monitoring h5 {{
            color: #2d3748;
            margin-bottom: 10px;
            font-size: 1.1em;
        }}
        
        .monitoring p {{
            color: #4a5568;
            margin: 0;
        }}
        
        .ai-summary {{
            background: #f0f9ff;
            border-radius: 12px;
            padding: 20px;
            margin: 20px 0;
            border-left: 4px solid #0ea5e9;
        }}
        
        .ai-summary h3 {{
            color: #0c4a6e;
            margin-bottom: 15px;
            font-size: 1.3em;
        }}
        
        .ai-summary p {{
            margin: 10px 0;
            color: #0f172a;
        }}
        
        .performance-grade-display {{
            display: flex;
            align-items: center;
            gap: 15px;
            margin: 15px 0;
            padding: 15px;
            background: white;
            border-radius: 8px;
            border: 2px solid #e5e7eb;
        }}
        
        .grade-badge {{
            font-size: 2em;
            font-weight: bold;
            padding: 10px 20px;
            border-radius: 8px;
            color: white;
            text-align: center;
            min-width: 60px;
        }}
        
        .grade-badge.grade-a {{
            background: #10b981;
        }}
        
        .grade-badge.grade-b {{
            background: #3b82f6;
        }}
        
        .grade-badge.grade-c {{
            background: #f59e0b;
        }}
        
        .grade-badge.grade-d {{
            background: #ef4444;
        }}
        
        .grade-badge.grade-f {{
            background: #dc2626;
        }}
        
        .score-display {{
            font-size: 1.5em;
            font-weight: bold;
            color: #374151;
        }}
        
        .ai-insights {{
            background: #f8fafc;
            border-radius: 12px;
            padding: 20px;
            margin: 20px 0;
            border-left: 4px solid #6366f1;
        }}
        
        .ai-insights h3 {{
            color: #4338ca;
            margin-bottom: 15px;
            font-size: 1.3em;
        }}
        
        .insights-content {{
            background: white;
            border-radius: 8px;
            padding: 20px;
            border: 1px solid #e5e7eb;
            line-height: 1.6;
        }}
        
        .insights-content h3 {{
            color: #1f2937;
            margin: 20px 0 10px 0;
            font-size: 1.2em;
        }}
        
        .insights-content h4 {{
            color: #374151;
            margin: 15px 0 8px 0;
            font-size: 1.1em;
        }}
        
        .insights-content strong {{
            color: #1f2937;
            font-weight: 600;
        }}
        
        .priority-high {{
            color: #dc2626;
            font-weight: bold;
        }}
        
        .priority-medium {{
            color: #d97706;
            font-weight: bold;
        }}
        
        .priority-low {{
            color: #059669;
            font-weight: bold;
        }}
        
        .primary-concerns {{
            background: #fef3c7;
            border-radius: 8px;
            padding: 15px;
            margin: 15px 0;
        }}
        
        .primary-concerns h4 {{
            color: #92400e;
            margin-bottom: 10px;
            font-size: 1.1em;
        }}
        
        .primary-concerns ul {{
            margin: 0;
            padding-left: 20px;
        }}
        
        .primary-concerns li {{
            margin: 8px 0;
            color: #78350f;
        }}
        
        .tech-insights {{
            background: #f0fdf4;
            border-radius: 12px;
            padding: 20px;
            margin: 20px 0;
            border-left: 4px solid #22c55e;
        }}
        
        .tech-insights h4 {{
            color: #166534;
            margin-bottom: 15px;
            font-size: 1.3em;
        }}
        
        .insights-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-top: 15px;
        }}
        
        .tech-details {{
            display: flex;
            flex-direction: column;
            gap: 15px;
        }}
        
        .tech-section {{
            background: #ffffff;
            border-radius: 8px;
            padding: 15px;
            border: 1px solid #e5e7eb;
        }}
        
        .tech-section h6 {{
            color: #374151;
            margin-bottom: 10px;
            font-size: 1em;
            font-weight: 600;
        }}
        
        .insight-category {{
            background: white;
            border-radius: 8px;
            padding: 15px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.05);
        }}
        
        .insight-category h5 {{
            color: #166534;
            margin-bottom: 10px;
            font-size: 1.1em;
        }}
        
        .insight-category ul {{
            margin: 0;
            padding-left: 20px;
        }}
        
        .insight-category li {{
            margin: 8px 0;
            color: #365314;
        }}
        
        /* Tooltip Styles */
        .tooltip-container {{
            position: relative;
            display: inline-block;
            cursor: help;
        }}
        
        .tooltip-icon {{
            display: inline-block;
            width: 16px;
            height: 16px;
            background: #4299e1;
            color: white;
            border-radius: 50%;
            text-align: center;
            font-size: 12px;
            line-height: 16px;
            margin-left: 8px;
            vertical-align: middle;
        }}
        
        .tooltip-content {{
            visibility: hidden;
            opacity: 0;
            position: absolute;
            z-index: 1000;
            bottom: 125%;
            left: 50%;
            transform: translateX(-50%);
            background: #2d3748;
            color: white;
            padding: 12px 16px;
            border-radius: 8px;
            font-size: 14px;
            line-height: 1.4;
            width: 300px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.3);
            transition: opacity 0.3s, visibility 0.3s;
        }}
        
        .tooltip-content::after {{
            content: "";
            position: absolute;
            top: 100%;
            left: 50%;
            transform: translateX(-50%);
            border: 5px solid transparent;
            border-top-color: #2d3748;
        }}
        
        .tooltip-container:hover .tooltip-content {{
            visibility: visible;
            opacity: 1;
        }}
        
        .tooltip-content h4 {{
            margin: 0 0 8px 0;
            color: #e2e8f0;
            font-size: 16px;
        }}
        
        .tooltip-content p {{
            margin: 4px 0;
            color: #cbd5e0;
        }}
        
        .tooltip-content .good-range {{
            color: #68d391;
            font-weight: 600;
        }}
        
        .tooltip-content .bad-range {{
            color: #fc8181;
            font-weight: 600;
        }}
        
        .insight-item h4 {{
            color: #2d3748;
            margin-bottom: 8px;
            font-weight: 600;
        }}
        
        .insight-item p {{
            color: #4a5568;
            font-size: 0.95em;
        }}
        
        .connection-breakdown {{
            background: #f7fafc;
            border-radius: 12px;
            padding: 20px;
            margin: 20px 0;
        }}
        
        .connection-breakdown h3 {{
            color: #2d3748;
            margin-bottom: 15px;
            font-size: 1.3em;
            font-weight: 600;
        }}
        
        .connection-item {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 10px 0;
            border-bottom: 1px solid #e2e8f0;
        }}
        
        .connection-item:last-child {{
            border-bottom: none;
        }}
        
        .connection-label {{
            font-weight: 500;
            color: #4a5568;
        }}
        
        .connection-value {{
            font-weight: 600;
            color: #2d3748;
        }}
        
        .status-codes {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
            gap: 15px;
            margin: 20px 0;
        }}
        
        .status-code {{
            background: #e6fffa;
            border: 1px solid #81e6d9;
            border-radius: 8px;
            padding: 15px;
            text-align: center;
        }}
        
        .status-code.success {{
            background: #f0fff4;
            border-color: #68d391;
        }}
        
        .status-code.error {{
            background: #fff5f5;
            border-color: #fc8181;
        }}
        
        .status-code .code {{
            font-size: 1.5em;
            font-weight: 700;
            color: #2d3748;
        }}
        
        .status-code .count {{
            font-size: 1.1em;
            color: #4a5568;
            margin-top: 5px;
        }}
        
        .status-code .percentage {{
            font-size: 0.9em;
            color: #718096;
            margin-top: 3px;
        }}
        
        @media (max-width: 768px) {{
            .container {{
                padding: 10px;
            }}
            
            .header h1 {{
                font-size: 2em;
            }}
            
            .metrics-grid {{
                grid-template-columns: 1fr;
            }}
            
            .summary-stats {{
                grid-template-columns: repeat(2, 1fr);
            }}
        }}
        
        /* Performance Culprits Styles */
        .culprits-list {{
            margin: 15px 0;
        }}
        
        .culprit-item {{
            background: #f8f9fa;
            border: 1px solid #e9ecef;
            border-radius: 8px;
            margin: 10px 0;
            padding: 15px;
            transition: all 0.3s ease;
        }}
        
        .culprit-item:hover {{
            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        }}
        
        .culprit-item.critical {{
            border-left: 4px solid #dc3545;
            background: #fff5f5;
        }}
        
        .culprit-item.high {{
            border-left: 4px solid #fd7e14;
            background: #fff8f0;
        }}
        
        .culprit-item.medium {{
            border-left: 4px solid #ffc107;
            background: #fffdf0;
        }}
        
        .culprit-header {{
            display: flex;
            align-items: center;
            gap: 10px;
            margin-bottom: 8px;
            flex-wrap: wrap;
        }}
        
        .culprit-rank {{
            background: #6c757d;
            color: white;
            padding: 2px 8px;
            border-radius: 12px;
            font-size: 0.8em;
            font-weight: bold;
        }}
        
        .severity-icon {{
            font-size: 1.2em;
        }}
        
        .resource-type {{
            background: #007bff;
            color: white;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 0.8em;
            font-weight: bold;
        }}
        
        .load-time {{
            background: #28a745;
            color: white;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 0.8em;
            font-weight: bold;
        }}
        
        .resource-size {{
            background: #17a2b8;
            color: white;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 0.8em;
            font-weight: bold;
        }}
        
        .culprit-details {{
            margin-top: 8px;
        }}
        
        .resource-url {{
            font-family: 'Courier New', monospace;
            font-size: 0.85em;
            color: #495057;
            word-break: break-all;
            margin-bottom: 4px;
        }}
        
        .request-breakdown {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 10px;
            margin: 15px 0;
        }}
        
        .request-type {{
            background: #f8f9fa;
            border: 1px solid #e9ecef;
            border-radius: 6px;
            padding: 10px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        
        .type-name {{
            font-weight: bold;
            color: #495057;
        }}
        
        .type-count {{
            background: #007bff;
            color: white;
            padding: 2px 8px;
            border-radius: 12px;
            font-size: 0.8em;
        }}
        
        .api-summary {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin: 15px 0;
        }}
        
        .api-stat {{
            background: #f8f9fa;
            border: 1px solid #e9ecef;
            border-radius: 6px;
            padding: 15px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        
        .stat-label {{
            font-weight: bold;
            color: #495057;
        }}
        
        .stat-value {{
            background: #28a745;
            color: white;
            padding: 4px 12px;
            border-radius: 12px;
            font-weight: bold;
        }}
        
        .culprit-recommendations {{
            margin: 15px 0;
        }}
        
        .culprit-recommendation {{
            background: #f8f9fa;
            border: 1px solid #e9ecef;
            border-radius: 8px;
            margin: 10px 0;
            padding: 15px;
        }}
        
        .culprit-recommendation.high {{
            border-left: 4px solid #dc3545;
            background: #fff5f5;
        }}
        
        .culprit-recommendation.medium {{
            border-left: 4px solid #ffc107;
            background: #fffdf0;
        }}
        
        .culprit-recommendation.low {{
            border-left: 4px solid #28a745;
            background: #f0fff4;
        }}
        
        .recommendation-header {{
            display: flex;
            align-items: center;
            gap: 10px;
            margin-bottom: 8px;
        }}
        
        .priority-icon {{
            font-size: 1.2em;
        }}
        
        .recommendation-title {{
            font-weight: bold;
            color: #495057;
        }}
        
        .recommendation-description {{
            color: #6c757d;
            margin-bottom: 8px;
        }}
        
        .recommendation-action {{
            color: #495057;
            font-size: 0.9em;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Load Test Report</h1>
            <div class="timestamp">POP Website Performance Analysis</div>
            <div class="timestamp">Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</div>
        </div>
        
        <!-- Navigation Links -->
        <div class="card">
            <h2>Report Navigation</h2>
            <div class="navigation-links">
                <a href="#protocol-test-results" class="nav-link">Protocol Test Results</a>
                <a href="#browser-test-results" class="nav-link">Browser Test Results</a>
                <a href="#unified-enhanced-performance-analysis" class="nav-link">Enhanced Performance Analysis</a>
                <a href="#enhanced-ai-analysis" class="nav-link">🤖 AI Analysis</a>
            </div>
        </div>
        
        <!-- Executive Summary -->
        <div class="card">
            <h2>📊 Executive Summary
                <div class="tooltip-container">
                    <span class="tooltip-icon">?</span>
                    <div class="tooltip-content">
                        <h4>Executive Summary</h4>
                        <p>High-level overview of your load test performance across protocol and browser metrics.</p>
                        <p><span class="good-range">Good:</span> High performance scores (80-100), low error rates (&lt;1%), fast response times</p>
                        <p><span class="bad-range">Poor:</span> Low performance scores (&lt;60), high error rates (&gt;5%), slow response times</p>
                    </div>
                </div>
            </h2>
            
            <div class="summary-stats">
                <div class="performance-grade">
                    <div class="label">Overall Performance Grade</div>
                    <div class="score">{get_performance_grade(protocol_metrics.get('performance_score', 0), browser_metrics.get('performance_score', 0))}</div>
                </div>
                <div class="stat">
                    <div class="label">Protocol Test Duration</div>
                    <div class="value">{protocol_metrics.get('test_duration_seconds', 0):.0f}s</div>
                </div>
                <div class="stat">
                    <div class="label">Browser Test Duration</div>
                    <div class="value">{browser_metrics.get('test_duration_seconds', 0):.0f}s</div>
                </div>
                <div class="stat">
                    <div class="label">Protocol VUs</div>
                    <div class="value">{protocol_metrics.get('virtual_users', 0)}</div>
                </div>
                <div class="stat">
                    <div class="label">Browser VUs</div>
                    <div class="value">{browser_metrics.get('max_vus', 0)}</div>
                </div>
            </div>
        </div>
        
        <!-- Protocol Test Results -->
        <div class="test-section" id="protocol-test-results">
            <h3>Protocol Test Results</h3>
            <div class="card">
                <h2>🔗 Key Metrics
                    <div class="tooltip-container">
                        <span class="tooltip-icon">?</span>
                        <div class="tooltip-content">
                            <h4>Protocol Test Metrics</h4>
                            <p>HTTP/API performance metrics from k6 load testing.</p>
                            <p><span class="good-range">Good Response Time:</span> &lt;200ms avg, &lt;500ms p95</p>
                            <p><span class="good-range">Good Throughput:</span> &gt;100 req/s</p>
                            <p><span class="good-range">Good Error Rate:</span> &lt;1%</p>
                            <p><span class="bad-range">Poor:</span> &gt;1000ms response, &lt;10 req/s, &gt;5% errors</p>
                        </div>
                    </div>
                </h2>
                <div class="metrics-grid">
                    <div class="metric">
                        <h3>Total Requests</h3>
                        <div class="value">{protocol_total_requests}</div>
                        <div class="unit">requests</div>
                    </div>
                    <div class="metric">
                        <h3>Success Rate</h3>
                        <div class="value success-rate">{protocol_success_rate:.1f}%</div>
                        <div class="unit">successful</div>
                    </div>
                    <div class="metric">
                        <h3>Avg Response Time</h3>
                        <div class="value">{protocol_avg_response}</div>
                        <div class="unit">ms</div>
                    </div>
                    <div class="metric">
                        <h3>P95 Response Time</h3>
                        <div class="value">{protocol_p95_response}</div>
                        <div class="unit">ms</div>
                    </div>
                    <div class="metric">
                        <h3>P99 Response Time</h3>
                        <div class="value">{protocol_p99_response}</div>
                        <div class="unit">ms</div>
                    </div>
                    <div class="metric">
                        <h3>Data Received</h3>
                        <div class="value">{protocol_data_received}</div>
                        <div class="unit">MB</div>
                    </div>
                </div>
                
                <!-- Enhanced Metrics Section -->
                <h3>Detailed Performance Metrics</h3>
                <div class="summary-stats">
                    <div class="stat">
                        <div class="label">P50 Response Time</div>
                        <div class="value">{protocol_p50_response}ms</div>
                    </div>
                    <div class="stat">
                        <div class="label">P75 Response Time</div>
                        <div class="value">{protocol_p75_response}ms</div>
                    </div>
                    <div class="stat">
                        <div class="label">P90 Response Time</div>
                        <div class="value">{protocol_p90_response}ms</div>
                    </div>
                    <div class="stat">
                        <div class="label">Data Sent</div>
                        <div class="value">{protocol_data_sent}MB</div>
                    </div>
                    <div class="stat">
                        <div class="label">Avg VUs</div>
                        <div class="value">{protocol_avg_vus}</div>
                    </div>
                    <div class="stat">
                        <div class="label">Total Iterations</div>
                        <div class="value">{protocol_total_iterations}</div>
                    </div>
                </div>
                
                <!-- Response Time Distribution Chart -->
                <div class="chart-container">
                    <h3>📈 Response Time Distribution
                        <div class="tooltip-container">
                            <span class="tooltip-icon">?</span>
                            <div class="tooltip-content">
                                <h4>Response Time Distribution</h4>
                                <p>Shows how response times are distributed across different percentiles.</p>
                                <p><span class="good-range">Good:</span> P95 &lt; 500ms, P99 &lt; 1000ms</p>
                                <p><span class="bad-range">Poor:</span> P95 &gt; 2000ms, P99 &gt; 5000ms</p>
                                <p>P95 means 95% of requests were faster than this value.</p>
                            </div>
                        </div>
                    </h3>
                    <div id="protocolResponseTimeChart"></div>
                </div>
                
                <!-- Connection Breakdown Chart -->
                <div class="chart-container">
                    <h3>🔗 HTTP Request Breakdown
                        <div class="tooltip-container">
                            <span class="tooltip-icon">?</span>
                            <div class="tooltip-content">
                                <h4>HTTP Request Breakdown</h4>
                                <p>Shows time spent in different phases of HTTP requests.</p>
                                <p><span class="good-range">Good:</span> Most time in "Waiting" (server processing)</p>
                                <p><span class="bad-range">Poor:</span> High "Connecting" or "TLS" times</p>
                                <p>Blocked: DNS/connection setup, Connecting: TCP handshake, TLS: SSL handshake</p>
                            </div>
                        </div>
                    </h3>
                    <div id="protocolConnectionChart"></div>
                </div>
                
                <!-- Performance Insights -->
                {generate_insights_panel(protocol_metrics.get('performance_insights', []))}
            </div>
        </div>
        
        <!-- Browser Test Results -->
        <div class="test-section browser-section" id="browser-test-results">
            <h3>Browser Test Results</h3>
            <div class="card">
                <h2>🌐 Key Metrics
                    <div class="tooltip-container">
                        <span class="tooltip-icon">?</span>
                        <div class="tooltip-content">
                            <h4>Browser Test Metrics</h4>
                            <p>Full page load performance metrics from Playwright browser testing.</p>
                            <p><span class="good-range">Good Response Time:</span> &lt;2000ms</p>
                            <p><span class="good-range">Good FCP:</span> &lt;1800ms</p>
                            <p><span class="good-range">Good TTFB:</span> &lt;600ms</p>
                            <p><span class="bad-range">Poor:</span> &gt;3000ms response, &gt;3000ms FCP</p>
                        </div>
                    </div>
                </h2>
                <div class="metrics-grid">
                    <div class="metric">
                        <h3>Total Requests</h3>
                        <div class="value">{browser_total_requests}</div>
                        <div class="unit">requests</div>
                    </div>
                    <div class="metric">
                        <h3>Success Rate</h3>
                        <div class="value success-rate">{browser_success_rate:.1f}%</div>
                        <div class="unit">successful</div>
                    </div>
                    <div class="metric">
                        <h3>Avg Response Time</h3>
                        <div class="value">{browser_avg_response}</div>
                        <div class="unit">ms</div>
                    </div>
                    <div class="metric">
                        <h3>P95 Response Time</h3>
                        <div class="value">{browser_p95_response}</div>
                        <div class="unit">ms</div>
                    </div>
                    <div class="metric">
                        <h3>Requests/Second</h3>
                        <div class="value">{browser_requests_per_sec}</div>
                        <div class="unit">req/s</div>
                    </div>
                    <div class="metric">
                        <h3>Performance Score</h3>
                        <div class="value">{browser_metrics.get('performance_score', 0):.0f}/100</div>
                        <div class="unit">score</div>
                    </div>
                </div>
                
                <!-- Core Web Vitals Section (Enhanced) -->
                <div class="card" style="margin-top: 20px;">
                    <h2>⚡ Core Web Vitals & Performance Scores
                        <div class="tooltip-container">
                            <span class="tooltip-icon">?</span>
                            <div class="tooltip-content">
                                <h4>Core Web Vitals</h4>
                                <p>Google's key metrics for user experience on web pages.</p>
                                <p><span class="good-range">Good LCP:</span> &lt;2.5s (Largest Contentful Paint)</p>
                                <p><span class="good-range">Good FID:</span> &lt;100ms (First Input Delay)</p>
                                <p><span class="good-range">Good CLS:</span> &lt;0.1 (Cumulative Layout Shift)</p>
                                <p><span class="bad-range">Poor:</span> LCP &gt;4s, FID &gt;300ms, CLS &gt;0.25</p>
                            </div>
                        </div>
                    </h2>
                    <div class="metrics-grid">
                        <div class="metric">
                            <h3>LCP Score</h3>
                            <div class="value" style="color: {'#27ae60' if browser_metrics.get('lcp_score', 0) >= 75 else '#f39c12' if browser_metrics.get('lcp_score', 0) >= 50 else '#e74c3c'}">{browser_metrics.get('lcp_score', 0):.0f}/100</div>
                            <div class="unit">score</div>
                        </div>
                        <div class="metric">
                            <h3>FID Score</h3>
                            <div class="value" style="color: {'#27ae60' if browser_metrics.get('fid_score', 0) >= 75 else '#f39c12' if browser_metrics.get('fid_score', 0) >= 50 else '#e74c3c'}">{browser_metrics.get('fid_score', 0):.0f}/100</div>
                            <div class="unit">score</div>
                        </div>
                        <div class="metric">
                            <h3>CLS Score</h3>
                            <div class="value" style="color: {'#27ae60' if browser_metrics.get('cls_score', 0) >= 75 else '#f39c12' if browser_metrics.get('cls_score', 0) >= 50 else '#e74c3c'}">{browser_metrics.get('cls_score', 0):.0f}/100</div>
                            <div class="unit">score</div>
                        </div>
                    </div>
                </div>
                
                <!-- Advanced Performance Metrics -->
                <div class="card" style="margin-top: 20px;">
                    <h2>⚡ Advanced Performance Metrics
                        <div class="tooltip-container">
                            <span class="tooltip-icon">?</span>
                            <div class="tooltip-content">
                                <h4>Advanced Performance Metrics</h4>
                                <p>Detailed browser performance metrics beyond Core Web Vitals.</p>
                                <p><span class="good-range">Good FCP:</span> &lt;1800ms (First Contentful Paint)</p>
                                <p><span class="good-range">Good DOM Loaded:</span> &lt;2000ms</p>
                                <p><span class="good-range">Good Load Complete:</span> &lt;3000ms</p>
                                <p><span class="bad-range">Poor:</span> FCP &gt;3000ms, DOM &gt;3000ms, Load &gt;5000ms</p>
                            </div>
                        </div>
                    </h2>
                    <div class="metrics-grid">
                        <div class="metric">
                            <h3>First Contentful Paint</h3>
                            <div class="value">{browser_metrics.get('avg_first_contentful_paint', 0):.0f}</div>
                            <div class="unit">ms</div>
                        </div>
                        <div class="metric">
                            <h3>DOM Content Loaded</h3>
                            <div class="value">{browser_metrics.get('avg_dom_content_loaded', 0):.0f}</div>
                            <div class="unit">ms</div>
                        </div>
                        <div class="metric">
                            <h3>Load Complete</h3>
                            <div class="value">{browser_metrics.get('avg_load_complete', 0):.0f}</div>
                            <div class="unit">ms</div>
                        </div>
                        <div class="metric">
                            <h3>Time to First Byte</h3>
                            <div class="value">{browser_metrics.get('avg_time_to_first_byte', 0):.0f}</div>
                            <div class="unit">ms</div>
                        </div>
                        <div class="metric">
                            <h3>Total Blocking Time</h3>
                            <div class="value">{browser_metrics.get('avg_total_blocking_time', 0):.0f}</div>
                            <div class="unit">ms</div>
                        </div>
                        <div class="metric">
                            <h3>Long Tasks Count</h3>
                            <div class="value">{browser_metrics.get('avg_long_tasks_count', 0):.0f}</div>
                            <div class="unit">tasks</div>
                        </div>
                    </div>
                </div>
                
                <!-- Network & Resource Metrics -->
                <div class="card" style="margin-top: 20px;">
                    <h2>🌐 Network & Resource Performance
                        <div class="tooltip-container">
                            <span class="tooltip-icon">?</span>
                            <div class="tooltip-content">
                                <h4>Network & Resource Performance</h4>
                                <p>Network timing and resource loading performance metrics.</p>
                                <p><span class="good-range">Good TTFB:</span> &lt;600ms (Time to First Byte)</p>
                                <p><span class="good-range">Good DNS:</span> &lt;100ms</p>
                                <p><span class="good-range">Good Resource Count:</span> &lt;50 resources</p>
                                <p><span class="bad-range">Poor:</span> TTFB &gt;1000ms, DNS &gt;200ms, &gt;100 resources</p>
                            </div>
                        </div>
                    </h2>
                    <div class="metrics-grid">
                        <div class="metric">
                            <h3>DNS Lookup</h3>
                            <div class="value">{browser_metrics.get('avg_dns_lookup', 0):.1f}</div>
                            <div class="unit">ms</div>
                        </div>
                        <div class="metric">
                            <h3>TCP Connection</h3>
                            <div class="value">{browser_metrics.get('avg_tcp_connection', 0):.1f}</div>
                            <div class="unit">ms</div>
                        </div>
                        <div class="metric">
                            <h3>SSL Handshake</h3>
                            <div class="value">{browser_metrics.get('avg_ssl_handshake', 0):.1f}</div>
                            <div class="unit">ms</div>
                        </div>
                        <div class="metric">
                            <h3>Resource Count</h3>
                            <div class="value">{browser_metrics.get('avg_resource_count', 0):.0f}</div>
                            <div class="unit">resources</div>
                        </div>
                        <div class="metric">
                            <h3>Resource Size</h3>
                            <div class="value">{(browser_metrics.get('avg_total_resource_size', 0) / 1024):.1f}</div>
                            <div class="unit">KB</div>
                        </div>
                        <div class="metric">
                            <h3>Data Transfer</h3>
                            <div class="value">{browser_metrics.get('data_received', 0):.1f}</div>
                            <div class="unit">MB</div>
                        </div>
                    </div>
                </div>
                
                <!-- Memory & Rendering Performance -->
                <div class="card" style="margin-top: 20px;">
                    <h2>🧠 Memory & Rendering Performance
                        <div class="tooltip-container">
                            <span class="tooltip-icon">?</span>
                            <div class="tooltip-content">
                                <h4>Memory & Rendering Performance</h4>
                                <p>Browser memory usage and rendering performance metrics.</p>
                                <p><span class="good-range">Good JS Heap:</span> &lt;25MB used</p>
                                <p><span class="good-range">Good Blocking Time:</span> &lt;100ms</p>
                                <p><span class="good-range">Good Long Tasks:</span> &lt;5 tasks</p>
                                <p><span class="bad-range">Poor:</span> &gt;50MB heap, &gt;300ms blocking, &gt;10 long tasks</p>
                            </div>
                        </div>
                    </h2>
                    <div class="metrics-grid">
                        <div class="metric">
                            <h3>JS Heap Used</h3>
                            <div class="value">{(browser_metrics.get('avg_js_heap_used', 0) / 1024 / 1024):.1f}</div>
                            <div class="unit">MB</div>
                        </div>
                        <div class="metric">
                            <h3>JS Heap Total</h3>
                            <div class="value">{(browser_metrics.get('avg_js_heap_total', 0) / 1024 / 1024):.1f}</div>
                            <div class="unit">MB</div>
                        </div>
                        <div class="metric">
                            <h3>Layout Duration</h3>
                            <div class="value">{browser_metrics.get('avg_layout_duration', 0):.1f}</div>
                            <div class="unit">ms</div>
                        </div>
                        <div class="metric">
                            <h3>Script Duration</h3>
                            <div class="value">{browser_metrics.get('avg_script_duration', 0):.1f}</div>
                            <div class="unit">ms</div>
                        </div>
                        <div class="metric">
                            <h3>Paint Duration</h3>
                            <div class="value">{browser_metrics.get('avg_paint_duration', 0):.1f}</div>
                            <div class="unit">ms</div>
                        </div>
                        <div class="metric">
                            <h3>Style Recalc</h3>
                            <div class="value">{browser_metrics.get('avg_recalc_style_duration', 0):.1f}</div>
                            <div class="unit">ms</div>
                        </div>
                    </div>
                </div>
                
                <!-- Response Time Distribution Chart -->
                <div class="chart-container">
                    <h3>📈 Response Time Distribution
                        <div class="tooltip-container">
                            <span class="tooltip-icon">?</span>
                            <div class="tooltip-content">
                                <h4>Browser Response Time Distribution</h4>
                                <p>Shows browser page load time distribution across different percentiles.</p>
                                <p><span class="good-range">Good:</span> Min &lt;1000ms, Avg &lt;2000ms, P95 &lt;3000ms</p>
                                <p><span class="bad-range">Poor:</span> Min &gt;2000ms, Avg &gt;3000ms, P95 &gt;5000ms</p>
                                <p>Browser response times include full page rendering and JavaScript execution.</p>
                            </div>
                        </div>
                    </h3>
                    <div id="browserResponseTimeChart"></div>
                </div>
                
                <!-- Connection Breakdown Chart -->
                <div class="chart-container">
                    <h3>🔗 HTTP Request Breakdown
                        <div class="tooltip-container">
                            <span class="tooltip-icon">?</span>
                            <div class="tooltip-content">
                                <h4>Browser HTTP Request Breakdown</h4>
                                <p>Shows time spent in different phases of browser HTTP requests.</p>
                                <p><span class="good-range">Good:</span> Most time in "TTFB" (server processing)</p>
                                <p><span class="bad-range">Poor:</span> High "DNS" or "TCP" connection times</p>
                                <p>DNS: Domain resolution, TCP: Connection setup, SSL: Encryption handshake</p>
                            </div>
                        </div>
                    </h3>
                    <div id="browserConnectionChart"></div>
                </div>
                
                <!-- Core Web Vitals Chart -->
                <div class="chart-container">
                    <h3>⚡ Core Web Vitals Performance
                        <div class="tooltip-container">
                            <span class="tooltip-icon">?</span>
                            <div class="tooltip-content">
                                <h4>Core Web Vitals Performance Chart</h4>
                                <p>Visual representation of Core Web Vitals scores (0-100 scale).</p>
                                <p><span class="good-range">Good Scores:</span> 75-100 (Green)</p>
                                <p><span class="bad-range">Poor Scores:</span> 0-49 (Red)</p>
                                <p>LCP: Largest Contentful Paint, FID: First Input Delay, CLS: Cumulative Layout Shift</p>
                            </div>
                        </div>
                    </h3>
                    <div id="coreWebVitalsChart"></div>
                </div>
                
                <!-- Network Performance Chart -->
                <div class="chart-container">
                    <h3>🌐 Network Performance Breakdown
                        <div class="tooltip-container">
                            <span class="tooltip-icon">?</span>
                            <div class="tooltip-content">
                                <h4>Network Performance Breakdown</h4>
                                <p>Shows network timing metrics for browser requests.</p>
                                <p><span class="good-range">Good:</span> Low DNS, TCP, and SSL times</p>
                                <p><span class="bad-range">Poor:</span> High connection setup times</p>
                                <p>Measures network latency and connection efficiency for page resources.</p>
                            </div>
                        </div>
                    </h3>
                    <div id="networkPerformanceChart"></div>
                </div>
                
                <!-- Memory Usage Chart -->
                <div class="chart-container">
                    <h3>🧠 Memory Usage
                        <div class="tooltip-container">
                            <span class="tooltip-icon">?</span>
                            <div class="tooltip-content">
                                <h4>Memory Usage Chart</h4>
                                <p>Shows JavaScript heap memory usage during page load.</p>
                                <p><span class="good-range">Good:</span> &lt;25MB used, &lt;75% of total</p>
                                <p><span class="bad-range">Poor:</span> &gt;50MB used, &gt;90% of total</p>
                                <p>High memory usage can cause performance issues and crashes.</p>
                            </div>
                        </div>
                    </h3>
                    <div id="memoryUsageChart"></div>
                </div>
                
                <!-- Status Code Distribution -->
                <h3>📊 Status Code Distribution
                    <div class="tooltip-container">
                        <span class="tooltip-icon">?</span>
                        <div class="tooltip-content">
                            <h4>Browser Status Code Distribution</h4>
                            <p>Shows HTTP response codes for browser page requests.</p>
                            <p><span class="good-range">Good:</span> 100% 2xx (success) codes</p>
                            <p><span class="bad-range">Poor:</span> Any 4xx (client errors) or 5xx (server errors)</p>
                            <p>Browser tests typically show 100% success for successful page loads.</p>
                        </div>
                    </div>
                </h3>
                <div class="status-codes">
                    {generate_browser_status_code_html(browser_metrics)}
                </div>
                
                <!-- Performance Insights -->
                {generate_insights_panel(browser_metrics.get('performance_insights', []))}
            </div>
        </div>
        
        <!-- Unified Enhanced Performance Analysis Section -->
        {unified_enhanced_analysis_section}
        
        <!-- Enhanced AI Analysis Section -->
        {enhanced_ai_analysis_section}
    </div>
    
    <script>
        // Protocol Response Time Distribution Chart
        const protocolResponseData = [
            {{
                x: ['P50', 'P75', 'P90', 'P95', 'P99'],
                y: [{protocol_metrics.get('p50_response_time', 0):.0f}, {protocol_metrics.get('p75_response_time', 0):.0f}, {protocol_metrics.get('p90_response_time', 0):.0f}, {protocol_metrics.get('p95_response_time', 0):.0f}, {protocol_metrics.get('p99_response_time', 0):.0f}],
                type: 'bar',
                marker: {{
                    color: 'rgba(52, 152, 219, 0.8)',
                    line: {{
                        color: 'rgba(52, 152, 219, 1)',
                        width: 1
                    }}
                }},
                name: 'Protocol Test'
            }}
        ];
        
        const protocolResponseLayout = {{
            title: 'Response Time Percentiles (ms)',
            xaxis: {{ title: 'Percentile' }},
            yaxis: {{ title: 'Response Time (ms)' }},
            showlegend: false,
            margin: {{ t: 50, b: 50, l: 60, r: 30 }}
        }};
        
        Plotly.newPlot('protocolResponseTimeChart', protocolResponseData, protocolResponseLayout);
        
        // Protocol Connection Breakdown Chart
        const protocolConnectionData = [
            {{
                values: [{protocol_metrics.get('connection_breakdown', {}).get('http_req_blocked', {}).get('avg', 0):.1f}, {protocol_metrics.get('connection_breakdown', {}).get('http_req_connecting', {}).get('avg', 0):.1f}, {protocol_metrics.get('connection_breakdown', {}).get('http_req_tls_handshaking', {}).get('avg', 0):.1f}, {protocol_metrics.get('connection_breakdown', {}).get('http_req_sending', {}).get('avg', 0):.1f}, {protocol_metrics.get('connection_breakdown', {}).get('http_req_waiting', {}).get('avg', 0):.1f}, {protocol_metrics.get('connection_breakdown', {}).get('http_req_receiving', {}).get('avg', 0):.1f}],
                labels: ['Blocked', 'Connecting', 'TLS Handshake', 'Sending', 'Waiting', 'Receiving'],
                type: 'pie',
                hole: 0.4,
                marker: {{
                    colors: ['#e74c3c', '#f39c12', '#f1c40f', '#2ecc71', '#3498db', '#9b59b6']
                }}
            }}
        ];
        
        const protocolConnectionLayout = {{
            title: 'HTTP Request Time Breakdown (ms)',
            showlegend: true,
            margin: {{ t: 50, b: 50, l: 30, r: 30 }}
        }};
        
        Plotly.newPlot('protocolConnectionChart', protocolConnectionData, protocolConnectionLayout);
        
        // Browser Response Time Distribution Chart (using Playwright data)
        const browserResponseData = [
            {{
                x: ['Min', 'Avg', 'P95', 'Max'],
                y: [{browser_metrics.get('min_response_time', 0):.0f}, {browser_metrics.get('avg_response_time', 0):.0f}, {browser_metrics.get('p95_response_time', 0):.0f}, {browser_metrics.get('max_response_time', 0):.0f}],
                type: 'bar',
                marker: {{
                    color: 'rgba(46, 204, 113, 0.8)',
                    line: {{
                        color: 'rgba(46, 204, 113, 1)',
                        width: 1
                    }}
                }},
                name: 'Browser Test'
            }}
        ];
        
        const browserResponseLayout = {{
            title: 'Response Time Percentiles (ms)',
            xaxis: {{ title: 'Percentile' }},
            yaxis: {{ title: 'Response Time (ms)' }},
            showlegend: false,
            margin: {{ t: 50, b: 50, l: 60, r: 30 }}
        }};
        
        Plotly.newPlot('browserResponseTimeChart', browserResponseData, browserResponseLayout);
        
        // Browser Connection Breakdown Chart (using Playwright network metrics)
        const browserConnectionData = [
            {{
                values: [{browser_metrics.get('avg_dns_lookup', 0):.1f}, {browser_metrics.get('avg_tcp_connection', 0):.1f}, {browser_metrics.get('avg_ssl_handshake', 0):.1f}, {browser_metrics.get('avg_time_to_first_byte', 0):.1f}],
                labels: ['DNS Lookup', 'TCP Connection', 'SSL Handshake', 'Time to First Byte'],
                type: 'pie',
                hole: 0.4,
                marker: {{
                    colors: ['#e74c3c', '#f39c12', '#f1c40f', '#2ecc71']
                }}
            }}
        ];
        
        const browserConnectionLayout = {{
            title: 'HTTP Request Time Breakdown (ms)',
            showlegend: true,
            margin: {{ t: 50, b: 50, l: 30, r: 30 }}
        }};
        
        Plotly.newPlot('browserConnectionChart', browserConnectionData, browserConnectionLayout);
        
        // Core Web Vitals Chart (showing scores instead of raw values)
        const coreWebVitalsData = [
            {{
                x: ['LCP Score', 'FID Score', 'CLS Score'],
                y: [{browser_metrics.get('lcp_score', 0):.0f}, {browser_metrics.get('fid_score', 0):.0f}, {browser_metrics.get('cls_score', 0):.0f}],
                type: 'bar',
                marker: {{
                    color: ['#27ae60', '#27ae60', '#27ae60']  // Green for good scores
                }},
                text: ['{browser_metrics.get('lcp_score', 0):.0f}/100', '{browser_metrics.get('fid_score', 0):.0f}/100', '{browser_metrics.get('cls_score', 0):.0f}/100'],
                textposition: 'auto'
            }}
        ];
        
        const coreWebVitalsLayout = {{
            title: 'Core Web Vitals Performance Scores',
            xaxis: {{ title: 'Metric' }},
            yaxis: {{ title: 'Score (0-100)' }},
            showlegend: false,
            margin: {{ t: 50, b: 50, l: 60, r: 30 }}
        }};
        
        Plotly.newPlot('coreWebVitalsChart', coreWebVitalsData, coreWebVitalsLayout);
        
        // Network Performance Chart
        const networkPerformanceData = [
            {{
                x: ['DNS Lookup', 'TCP Connection', 'SSL Handshake', 'TTFB'],
                y: [{browser_metrics.get('avg_dns_lookup', 0):.1f}, {browser_metrics.get('avg_tcp_connection', 0):.1f}, {browser_metrics.get('avg_ssl_handshake', 0):.1f}, {browser_metrics.get('avg_time_to_first_byte', 0):.1f}],
                type: 'bar',
                marker: {{
                    color: ['#2ecc71', '#3498db', '#9b59b6', '#e67e22']
                }},
                text: ['{browser_metrics.get('avg_dns_lookup', 0):.1f}ms', '{browser_metrics.get('avg_tcp_connection', 0):.1f}ms', '{browser_metrics.get('avg_ssl_handshake', 0):.1f}ms', '{browser_metrics.get('avg_time_to_first_byte', 0):.1f}ms'],
                textposition: 'auto'
            }}
        ];
        
        const networkPerformanceLayout = {{
            title: 'Network Performance Breakdown',
            xaxis: {{ title: 'Network Phase' }},
            yaxis: {{ title: 'Time (ms)' }},
            showlegend: false,
            margin: {{ t: 50, b: 50, l: 60, r: 30 }}
        }};
        
        Plotly.newPlot('networkPerformanceChart', networkPerformanceData, networkPerformanceLayout);
        
        // Memory Usage Chart
        const memoryUsageData = [
            {{
                values: [{browser_metrics.get('avg_js_heap_used', 0):.0f}, {(browser_metrics.get('avg_js_heap_total', 0) - browser_metrics.get('avg_js_heap_used', 0)):.0f}],
                labels: ['Used', 'Available'],
                type: 'pie',
                hole: 0.4,
                marker: {{
                    colors: ['#e74c3c', '#2ecc71']
                }},
                textinfo: 'label+percent',
                textposition: 'outside'
            }}
        ];
        
        const memoryUsageLayout = {{
            title: 'JavaScript Heap Memory Usage',
            showlegend: true,
            margin: {{ t: 50, b: 50, l: 30, r: 30 }}
        }};
        
        Plotly.newPlot('memoryUsageChart', memoryUsageData, memoryUsageLayout);
    </script>
</body>
</html>"""
    
    with open(output_path, 'w') as f:
        f.write(html)
    
    print(f"✅ HTML report generated: {output_path}")

def generate_status_code_html(status_codes):
    """Generate HTML for status code distribution"""
    if not status_codes:
        return '<p>No status code data available.</p>'
    
    html_parts = []
    total_requests = sum(status_codes.values())
    
    for status, count in status_codes.items():
        percentage = (count / total_requests) * 100 if total_requests > 0 else 0
        css_class = 'success' if status.startswith('2') else 'error' if status.startswith('4') or status.startswith('5') else ''
        
        html_parts.append(f'''
        <div class="status-code {css_class}">
            <div class="code">{status}</div>
            <div class="count">{count:,}</div>
            <div class="percentage">{percentage:.1f}%</div>
        </div>
        ''')
    
    return '\n'.join(html_parts)

def generate_browser_status_code_html(browser_metrics):
    """Generate HTML for browser test status code distribution"""
    # For browser tests, we'll show a simplified status based on success rate
    total_iterations = browser_metrics.get('total_iterations', 0)
    if total_iterations == 0:
        return '<p>No status code data available</p>'
    
    # Assume all successful browser tests return 200 (since we're not tracking individual status codes)
    success_count = total_iterations
    success_percentage = 100.0  # Browser tests that complete successfully are considered 200
    
    html = '<div class="status-code-grid">'
    html += f'''
    <div class="status-code success">
        <div class="code">200</div>
        <div class="count">{success_count:,}</div>
        <div class="percentage">{success_percentage:.1f}%</div>
    </div>
    '''
    html += '</div>'
    return html

def generate_insights_panel(insights):
    """Generate HTML for performance insights panel"""
    if not insights:
        return ''
    
    html_parts = []
    for insight in insights:
        severity_color = '#e53e3e' if insight.get('severity') == 'high' else '#d69e2e' if insight.get('severity') == 'medium' else '#38a169'
        
        html_parts.append(f'''
        <div class="insight-item" style="border-left-color: {severity_color};">
            <h4>{insight.get('message', 'Performance Issue')}</h4>
            <p><strong>Recommendation:</strong> {insight.get('recommendation', '')}</p>
        </div>
        ''')
    
    return f'''
    <div class="insights-panel">
        <h3>🚨 Performance Insights</h3>
        {chr(10).join(html_parts)}
    </div>
    '''

def get_performance_grade(protocol_score, browser_score):
    """Get overall performance grade"""
    avg_score = (protocol_score + browser_score) / 2
    
    if avg_score >= 90:
        return 'A+'
    elif avg_score >= 80:
        return 'A'
    elif avg_score >= 70:
        return 'B'
    elif avg_score >= 60:
        return 'C'
    elif avg_score >= 50:
        return 'D'
    else:
        return 'F'

def generate_unified_enhanced_analysis(enhanced_analysis, browser_metrics, protocol_metrics):
    """Generate unified enhanced performance analysis combining protocol and browser insights"""
    
    # Calculate unified performance score
    protocol_score = protocol_metrics.get('performance_score', 0)
    
    # Adjust browser score based on response time
    browser_score = browser_metrics.get('performance_score', 0)
    avg_response_time = browser_metrics.get('avg_response_time', 0)
    
    # Deduct points for slow browser response times
    if avg_response_time > 3000:  # > 3s
        browser_score = max(0, browser_score - 30)
    elif avg_response_time > 2000:  # > 2s
        browser_score = max(0, browser_score - 15)
    elif avg_response_time > 1500:  # > 1.5s
        browser_score = max(0, browser_score - 5)
    
    unified_score = (protocol_score + browser_score) / 2
    
    # Get protocol insights from enhanced analysis and performance deductions
    protocol_issues = enhanced_analysis.get('issues', {}) if enhanced_analysis else {'high': [], 'medium': [], 'low': []}
    protocol_recommendations = enhanced_analysis.get('recommendations', []) if enhanced_analysis else []
    
    # Add protocol insights from performance deductions
    protocol_deductions = protocol_metrics.get('performance_deductions', [])
    for deduction in protocol_deductions:
        if 'error rate' in deduction.lower():
            protocol_issues['high'].append({
                'category': 'Reliability',
                'issue': deduction,
                'recommendation': 'Investigate and fix error sources, improve error handling, and implement retry mechanisms'
            })
        elif 'response' in deduction.lower() and ('slow' in deduction.lower() or 'very slow' in deduction.lower()):
            protocol_issues['high'].append({
                'category': 'Performance',
                'issue': deduction,
                'recommendation': 'Optimize server performance, implement caching, and review database queries'
            })
        elif 'throughput' in deduction.lower():
            protocol_issues['medium'].append({
                'category': 'Performance',
                'issue': deduction,
                'recommendation': 'Optimize server capacity, implement load balancing, and review resource allocation'
            })
        elif 'connection' in deduction.lower() or 'dns' in deduction.lower() or 'tls' in deduction.lower():
            protocol_issues['medium'].append({
                'category': 'Network',
                'issue': deduction,
                'recommendation': 'Optimize network configuration, implement connection pooling, and review DNS settings'
            })
        elif 'server processing' in deduction.lower():
            protocol_issues['high'].append({
                'category': 'Performance',
                'issue': deduction,
                'recommendation': 'Optimize server-side processing, implement caching, and review application performance'
            })
        elif 'response size' in deduction.lower():
            protocol_issues['low'].append({
                'category': 'Efficiency',
                'issue': deduction,
                'recommendation': 'Optimize response payloads, implement compression, and review data transfer efficiency'
            })
        elif 'vu variation' in deduction.lower():
            protocol_issues['low'].append({
                'category': 'Load Distribution',
                'issue': deduction,
                'recommendation': 'Review load distribution patterns and optimize virtual user allocation'
            })
    
    # Get comprehensive browser insights from performance deductions
    browser_insights = []
    browser_deductions = browser_metrics.get('performance_deductions', [])
    
    for deduction in browser_deductions:
        if 'page load' in deduction.lower():
            browser_insights.append({
                'category': 'Performance',
                'issue': deduction,
                'recommendation': 'Optimize page loading, reduce JavaScript execution time, and implement performance optimizations'
            })
        elif 'fcp' in deduction.lower() or 'first contentful paint' in deduction.lower():
            browser_insights.append({
                'category': 'Performance',
                'issue': deduction,
                'recommendation': 'Optimize critical rendering path, reduce render-blocking resources, and improve server response times'
            })
        elif 'ttfb' in deduction.lower() or 'time to first byte' in deduction.lower():
            browser_insights.append({
                'category': 'Network',
                'issue': deduction,
                'recommendation': 'Optimize server response times, implement caching, and consider CDN usage'
            })
        elif 'dns' in deduction.lower() or 'tcp' in deduction.lower() or 'ssl' in deduction.lower():
            browser_insights.append({
                'category': 'Network',
                'issue': deduction,
                'recommendation': 'Optimize DNS resolution, improve connection performance, and consider connection optimization'
            })
        elif 'memory' in deduction.lower() or 'heap' in deduction.lower():
            browser_insights.append({
                'category': 'Memory',
                'issue': deduction,
                'recommendation': 'Optimize JavaScript memory usage, implement memory management best practices, and reduce memory leaks'
            })
        elif 'resource' in deduction.lower():
            browser_insights.append({
                'category': 'Resources',
                'issue': deduction,
                'recommendation': 'Optimize resource loading, implement lazy loading, and reduce resource count/size'
            })
        elif 'blocking' in deduction.lower() or 'long tasks' in deduction.lower():
            browser_insights.append({
                'category': 'Performance',
                'issue': deduction,
                'recommendation': 'Optimize JavaScript execution, reduce main thread blocking, and implement code splitting'
            })
        elif 'throughput' in deduction.lower():
            browser_insights.append({
                'category': 'Performance',
                'issue': deduction,
                'recommendation': 'Optimize browser performance, reduce page complexity, and improve resource loading efficiency'
            })
        else:
            browser_insights.append({
                'category': 'Performance',
                'issue': deduction,
                'recommendation': 'Review and optimize browser performance metrics'
            })
    
    # Combine all issues
    total_issues = len(protocol_issues.get('high', [])) + len(protocol_issues.get('medium', [])) + len(protocol_issues.get('low', [])) + len(browser_insights)
    
    # Generate issues HTML
    issues_html = ''
    if protocol_issues.get('high'):
        for issue in protocol_issues['high']:
            issues_html += f'''
            <div class="insight-item high-priority">
                <h4>🔴 {issue.get('issue', 'Unknown issue')}</h4>
                <p><strong>Category:</strong> Protocol Performance</p>
                <p><strong>Recommendation:</strong> {issue.get('recommendation', 'No recommendation available')}</p>
            </div>
            '''
    
    if protocol_issues.get('medium'):
        for issue in protocol_issues['medium']:
            issues_html += f'''
            <div class="insight-item medium-priority">
                <h4>🟡 {issue.get('issue', 'Unknown issue')}</h4>
                <p><strong>Category:</strong> Protocol Performance</p>
                <p><strong>Recommendation:</strong> {issue.get('recommendation', 'No recommendation available')}</p>
            </div>
            '''
    
    if protocol_issues.get('low'):
        for issue in protocol_issues['low']:
            issues_html += f'''
            <div class="insight-item low-priority">
                <h4>🟢 {issue.get('issue', 'Unknown issue')}</h4>
                <p><strong>Category:</strong> Protocol Performance</p>
                <p><strong>Recommendation:</strong> {issue.get('recommendation', 'No recommendation available')}</p>
            </div>
            '''
    
    if browser_insights:
        for insight in browser_insights:
            issues_html += f'''
            <div class="insight-item high-priority">
                <h4>🔴 {insight.get('issue', 'Unknown issue')}</h4>
                <p><strong>Category:</strong> {insight.get('category', 'Browser Performance')}</p>
                <p><strong>Recommendation:</strong> {insight.get('recommendation', 'No recommendation available')}</p>
            </div>
            '''
    
    if not issues_html:
        issues_html = '''
        <div class="insight-item success">
            <h4>✅ No Performance Issues Detected</h4>
            <p>Both protocol and browser tests show excellent performance with no significant issues identified.</p>
        </div>
        '''
    
    # Generate recommendations HTML
    recommendations_html = ''
    if protocol_recommendations:
        for rec in protocol_recommendations[:3]:  # Show top 3
            priority_icon = "🔴" if rec.get('priority') == 'high' else "🟡" if rec.get('priority') == 'medium' else "🟢"
            recommendations_html += f'''
            <div class="recommendation-item">
                <h4>{priority_icon} {rec.get('title', 'Performance Recommendation')}</h4>
                <p><strong>Category:</strong> {rec.get('category', 'General')}</p>
                <p><strong>Description:</strong> {rec.get('description', 'No description available')}</p>
                <ul>
            '''
            for action in rec.get('actions', [])[:3]:  # Show top 3 actions
                recommendations_html += f'<li>{action}</li>'
            recommendations_html += '</ul></div>'
    
    # Add protocol-specific recommendations based on deductions
    protocol_deductions = protocol_metrics.get('performance_deductions', [])
    for deduction in protocol_deductions:
        if 'throughput' in deduction.lower():
            recommendations_html += '''
            <div class="recommendation-item">
                <h4>🟡 Optimize Protocol Throughput</h4>
                <p><strong>Category:</strong> Protocol Performance</p>
                <p><strong>Description:</strong> Protocol throughput is below optimal levels, affecting overall system performance</p>
                <ul>
                    <li>Increase server capacity and resource allocation</li>
                    <li>Implement connection pooling and keep-alive connections</li>
                    <li>Optimize database queries and reduce query complexity</li>
                    <li>Consider horizontal scaling with load balancers</li>
                    <li>Review and optimize application code for better efficiency</li>
                    <li>Implement caching strategies for frequently accessed data</li>
                </ul>
            </div>
            '''
        elif 'error rate' in deduction.lower():
            recommendations_html += '''
            <div class="recommendation-item">
                <h4>🔴 Fix Protocol Error Rates</h4>
                <p><strong>Category:</strong> Protocol Reliability</p>
                <p><strong>Description:</strong> High error rates detected in protocol tests, indicating system reliability issues</p>
                <ul>
                    <li>Investigate and fix root causes of errors</li>
                    <li>Implement proper error handling and retry mechanisms</li>
                    <li>Add monitoring and alerting for error conditions</li>
                    <li>Review server logs for error patterns</li>
                    <li>Implement circuit breakers for external dependencies</li>
                    <li>Add input validation and sanitization</li>
                </ul>
            </div>
            '''
        elif 'response' in deduction.lower() and ('slow' in deduction.lower() or 'very slow' in deduction.lower()):
            recommendations_html += '''
            <div class="recommendation-item">
                <h4>🔴 Optimize Protocol Response Times</h4>
                <p><strong>Category:</strong> Protocol Performance</p>
                <p><strong>Description:</strong> Protocol response times are slower than optimal, affecting user experience</p>
                <ul>
                    <li>Optimize server-side processing and database queries</li>
                    <li>Implement response caching and CDN usage</li>
                    <li>Review and optimize application architecture</li>
                    <li>Consider database indexing and query optimization</li>
                    <li>Implement async processing for long-running operations</li>
                    <li>Add performance monitoring and profiling</li>
                </ul>
            </div>
            '''
        elif 'connection' in deduction.lower() or 'dns' in deduction.lower() or 'tls' in deduction.lower():
            recommendations_html += '''
            <div class="recommendation-item">
                <h4>🟡 Optimize Network Connections</h4>
                <p><strong>Category:</strong> Network Performance</p>
                <p><strong>Description:</strong> Network connection performance issues detected</p>
                <ul>
                    <li>Optimize DNS resolution and consider DNS caching</li>
                    <li>Implement connection pooling and reuse</li>
                    <li>Review TLS/SSL configuration and certificates</li>
                    <li>Consider HTTP/2 or HTTP/3 for better multiplexing</li>
                    <li>Optimize network routing and reduce latency</li>
                    <li>Implement connection keep-alive strategies</li>
                </ul>
            </div>
            '''
        elif 'server processing' in deduction.lower():
            recommendations_html += '''
            <div class="recommendation-item">
                <h4>🔴 Optimize Server Processing</h4>
                <p><strong>Category:</strong> Server Performance</p>
                <p><strong>Description:</strong> Server processing times are slower than optimal</p>
                <ul>
                    <li>Profile and optimize server-side code</li>
                    <li>Implement caching for expensive operations</li>
                    <li>Optimize database queries and indexing</li>
                    <li>Consider microservices architecture for better scaling</li>
                    <li>Implement async processing and background jobs</li>
                    <li>Add performance monitoring and alerting</li>
                </ul>
            </div>
            '''
    
    # Add browser-specific recommendations if response time is slow
    if avg_response_time > 2000:
        recommendations_html += '''
        <div class="recommendation-item">
            <h4>🔴 Optimize Browser Response Times</h4>
            <p><strong>Category:</strong> Browser Performance</p>
            <p><strong>Description:</strong> Browser response times are slower than optimal, affecting user experience</p>
            <ul>
                <li>Implement code splitting and lazy loading for JavaScript bundles</li>
                <li>Optimize images with modern formats (WebP, AVIF) and proper sizing</li>
                <li>Enable browser caching and CDN for static assets</li>
                <li>Minimize and compress CSS/JavaScript files</li>
                <li>Consider server-side rendering (SSR) for faster initial page loads</li>
                <li>Implement critical CSS inlining for above-the-fold content</li>
            </ul>
        </div>
        '''
    
    if not recommendations_html:
        recommendations_html = '''
        <div class="recommendation-item success">
            <h4>✅ Performance Optimization Complete</h4>
            <p>No specific recommendations needed - your application is performing excellently across all metrics.</p>
        </div>
        '''
    
    # Generate detailed metrics HTML
    detailed_metrics_html = ''
    if enhanced_analysis and enhanced_analysis.get('detailed_metrics'):
        metrics = enhanced_analysis['detailed_metrics']
        
        # HTTP Performance
        if metrics.get('http_duration'):
            http_duration = metrics['http_duration']
            detailed_metrics_html += f'''
            <div class="metric-group">
                <h4>🌐 HTTP Performance</h4>
                <div class="metrics-grid">
                    <div class="metric">
                        <h5>Average Response Time</h5>
                        <div class="value">{http_duration.get('avg', 0):.1f}ms</div>
                    </div>
                    <div class="metric">
                        <h5>95th Percentile</h5>
                        <div class="value">{http_duration.get('p95', 0):.1f}ms</div>
                    </div>
                    <div class="metric">
                        <h5>99th Percentile</h5>
                        <div class="value">{http_duration.get('p99', 0):.1f}ms</div>
                    </div>
                </div>
            </div>
            '''
        
        # Data Transfer
        if metrics.get('data_transfer'):
            data_transfer = metrics['data_transfer']
            detailed_metrics_html += f'''
            <div class="metric-group">
                <h4>📦 Data Transfer</h4>
                <div class="metrics-grid">
                    <div class="metric">
                        <h5>Total Data Received</h5>
                        <div class="value">{data_transfer.get('data_received_mb', 0):.1f}MB</div>
                    </div>
                    <div class="metric">
                        <h5>Total Data Sent</h5>
                        <div class="value">{data_transfer.get('data_sent_mb', 0):.1f}MB</div>
                    </div>
                    <div class="metric">
                        <h5>Avg Response Size</h5>
                        <div class="value">{data_transfer.get('avg_received_kb', 0):.1f}KB</div>
                    </div>
                </div>
            </div>
            '''
    
    # Browser Performance Metrics
    if browser_metrics:
        detailed_metrics_html += f'''
        <div class="metric-group">
            <h4>🌐 Browser Performance</h4>
            <div class="metrics-grid">
                <div class="metric">
                    <h5>Average Response Time</h5>
                    <div class="value">{browser_metrics.get('avg_response_time', 0):.0f}ms</div>
                </div>
                <div class="metric">
                    <h5>Core Web Vitals Score</h5>
                    <div class="value">{browser_metrics.get('performance_score', 0):.0f}/100</div>
                </div>
                <div class="metric">
                    <h5>Memory Usage</h5>
                    <div class="value">{browser_metrics.get('avg_js_heap_used', 0) / 1024 / 1024:.1f}MB</div>
                </div>
            </div>
        </div>
        '''
    
    return f'''
    <div class="test-section" id="unified-enhanced-performance-analysis">
        <h3>🚀 Enhanced Performance Analysis
            <div class="tooltip-container">
                <span class="tooltip-icon">?</span>
                <div class="tooltip-content">
                    <h4>Enhanced Performance Analysis</h4>
                    <p>Comprehensive analysis combining protocol and browser performance insights.</p>
                    <p><span class="good-range">Good Overall Score:</span> 80-100</p>
                    <p><span class="good-range">Good Issues Count:</span> 0-2 issues</p>
                    <p><span class="bad-range">Poor:</span> &lt;60 overall score, &gt;5 issues</p>
                    <p>Provides actionable recommendations for performance optimization.</p>
                </div>
            </div>
        </h3>
        
        <!-- Performance Overview -->
        <div class="card">
            <h2>📊 Unified Performance Overview
                <div class="tooltip-container">
                    <span class="tooltip-icon">?</span>
                    <div class="tooltip-content">
                        <h4>Unified Performance Overview</h4>
                        <p>Combined performance scores from both protocol and browser tests.</p>
                        <p><span class="good-range">Good Overall Score:</span> 80-100</p>
                        <p><span class="good-range">Good Individual Scores:</span> 75-100 each</p>
                        <p><span class="bad-range">Poor:</span> &lt;60 overall, &lt;50 individual scores</p>
                        <p>Balanced performance across both API and user experience metrics.</p>
                    </div>
                </div>
            </h2>
            <div class="summary-stats">
                <div class="stat">
                    <div class="label">Overall Performance Score</div>
                    <div class="value">{unified_score:.0f}/100</div>
                </div>
                <div class="stat">
                    <div class="label">Protocol Performance</div>
                    <div class="value">{protocol_score}/100</div>
                </div>
                <div class="stat">
                    <div class="label">Browser Performance</div>
                    <div class="value">{browser_score}/100</div>
                </div>
                <div class="stat">
                    <div class="label">Total Issues Found</div>
                    <div class="value">{total_issues}</div>
                </div>
            </div>
        </div>
        
        <!-- Performance Issues -->
        <div class="card">
            <h2>🔍 Performance Issues & Insights
                <div class="tooltip-container">
                    <span class="tooltip-icon">?</span>
                    <div class="tooltip-content">
                        <h4>Performance Issues & Insights</h4>
                        <p>Detailed analysis of performance problems found in your tests.</p>
                        <p><span class="good-range">Good:</span> 0-2 issues found</p>
                        <p><span class="bad-range">Poor:</span> 5+ issues found</p>
                        <p>Issues are categorized by priority: High (🔴), Medium (🟡), Low (🟢)</p>
                    </div>
                </div>
            </h2>
            <div class="insights-panel">
                {issues_html}
            </div>
        </div>
        
        <!-- Recommendations -->
        <div class="card">
            <h2>💡 Performance Recommendations
                <div class="tooltip-container">
                    <span class="tooltip-icon">?</span>
                    <div class="tooltip-content">
                        <h4>Performance Recommendations</h4>
                        <p>Actionable steps to improve your application's performance.</p>
                        <p><span class="good-range">Good:</span> Few or no recommendations needed</p>
                        <p><span class="bad-range">Poor:</span> Many recommendations indicate optimization opportunities</p>
                        <p>Each recommendation includes specific actions you can take to improve performance.</p>
                    </div>
                </div>
            </h2>
            <div class="recommendations-panel">
                {recommendations_html}
            </div>
        </div>
        
        <!-- Detailed Metrics -->
        <div class="card">
            <h2>📊 Detailed Performance Metrics
                <div class="tooltip-container">
                    <span class="tooltip-icon">?</span>
                    <div class="tooltip-content">
                        <h4>Detailed Performance Metrics</h4>
                        <p>Comprehensive breakdown of all performance metrics from both test types.</p>
                        <p><span class="good-range">Good:</span> All metrics within optimal ranges</p>
                        <p><span class="bad-range">Poor:</span> Multiple metrics outside optimal ranges</p>
                        <p>Includes protocol metrics (response times, throughput) and browser metrics (Core Web Vitals, memory).</p>
                    </div>
                </div>
            </h2>
            <div class="detailed-metrics">
                {detailed_metrics_html}
            </div>
        </div>
    </div>
    '''

def main():
    """Main function"""
    if len(sys.argv) < 2:
        print("Usage: python scripts/generate_k6_html_report.py <output_directory>")
        sys.exit(1)
    
    output_dir = sys.argv[1]
    if not os.path.exists(output_dir):
        print(f"Error: Directory not found: {output_dir}")
        sys.exit(1)
    
    # Load protocol test results
    protocol_file = os.path.join(output_dir, "protocol_summary.json")
    if not os.path.exists(protocol_file):
        print(f"Error: Protocol summary file not found: {protocol_file}")
        sys.exit(1)
    
    protocol_data = load_k6_summary(protocol_file)
    if not protocol_data:
        sys.exit(1)
    
    # Load browser test results
    browser_file = os.path.join(output_dir, "browser_summary.json")
    if not os.path.exists(browser_file):
        print(f"Error: Browser summary file not found: {browser_file}")
        sys.exit(1)
    
    browser_data = load_k6_summary(browser_file)
    if not browser_data:
        sys.exit(1)
    
    # Extract metrics
    protocol_metrics = extract_metrics(protocol_data)
    browser_metrics = extract_metrics(browser_data)
    
    # Load enhanced AI analysis results if available
    enhanced_ai_analysis = None
    # Try both possible filenames for AI analysis
    ai_files = ["ai_analysis_report.json", "enhanced_ai_analysis_report.json"]
    for ai_file in ai_files:
        ai_file_path = os.path.join(output_dir, ai_file)
        if os.path.exists(ai_file_path):
            try:
                with open(ai_file_path, 'r') as f:
                    enhanced_ai_analysis = json.load(f)
                print(f"✅ Loaded AI analysis results from {ai_file}")
                break
            except Exception as e:
                print(f"⚠️  Could not load AI analysis from {ai_file}: {e}")
    
    # Generate HTML report
    html_file = os.path.join(output_dir, "load_test_report.html")
    generate_html_report(protocol_metrics, browser_metrics, html_file, enhanced_ai_analysis)

if __name__ == "__main__":
    main()
