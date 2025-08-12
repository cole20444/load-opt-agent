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
    """Load k6 summary JSONL file"""
    try:
        data = []
        with open(file_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line:
                    data.append(json.loads(line))
        return data
    except Exception as e:
        print(f"Error loading {file_path}: {e}")
        return None

def extract_metrics(summary_data):
    """Extract comprehensive metrics from k6 summary data"""
    metrics = {}
    
    if not summary_data:
        return metrics
    
    print(f"Processing {len(summary_data)} data points...")
    
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

def generate_html_report(protocol_metrics, browser_metrics, output_path):
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
    browser_file = os.path.join(output_dir, "browser_summary_analysis.json")
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
            </div>
            
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
            tbt_ms=browser_summary.get('tbt_ms', 0),
            performance_score=browser_analysis.get('performance_score', 0),
            total_page_weight=browser_summary.get('total_page_weight_mb', 0),
            total_requests=browser_summary.get('total_requests', 0),
            largest_resource=resource_analysis.get('largest_resource_kb', 0),
            avg_resource_size=resource_analysis.get('average_resource_size_kb', 0),
            resource_types_html=generate_resource_types_html(resource_analysis.get('resource_counts', {})),
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
    protocol_data_sent = f"{(protocol_metrics.get('data_sent', 0) / 1024 / 1024):.1f}"
    protocol_avg_vus = f"{protocol_metrics.get('avg_vus', 0):.0f}"
    protocol_total_iterations = f"{protocol_metrics.get('total_iterations', 0):,}"
    
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
                <a href="#enhanced-performance-analysis" class="nav-link">Enhanced Performance Analysis</a>
                <a href="#enhanced-browser-analysis" class="nav-link">Enhanced Browser Performance Analysis</a>
            </div>
        </div>
        
        <!-- Executive Summary -->
        <div class="card">
            <h2>Executive Summary</h2>
            
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
                    <div class="value">{protocol_metrics.get('max_vus', 0)}</div>
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
                <h2>Key Metrics</h2>
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
                    <h3>Response Time Distribution</h3>
                    <div id="protocolResponseTimeChart"></div>
                </div>
                
                <!-- Connection Breakdown Chart -->
                <div class="chart-container">
                    <h3>HTTP Request Breakdown</h3>
                    <div id="protocolConnectionChart"></div>
                </div>
                
                <!-- Status Code Distribution -->
                <h3>Status Code Distribution</h3>
                <div class="status-codes">
                    {generate_status_code_html(protocol_metrics.get('status_code_distribution', {}))}
                </div>
                
                <!-- Performance Insights -->
                {generate_insights_panel(protocol_metrics.get('performance_insights', []))}
            </div>
        </div>
        
        <!-- Browser Test Results -->
        <div class="test-section browser-section" id="browser-test-results">
            <h3>Browser Test Results</h3>
            <div class="card">
                <h2>Key Metrics</h2>
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
                
                <!-- Response Time Distribution Chart -->
                <div class="chart-container">
                    <h3>Response Time Distribution</h3>
                    <div id="browserResponseTimeChart"></div>
                </div>
                
                <!-- Connection Breakdown Chart -->
                <div class="chart-container">
                    <h3>HTTP Request Breakdown</h3>
                    <div id="browserConnectionChart"></div>
                </div>
                
                <!-- Status Code Distribution -->
                <h3>Status Code Distribution</h3>
                <div class="status-codes">
                    {generate_status_code_html(browser_metrics.get('status_code_distribution', {}))}
                </div>
                
                <!-- Performance Insights -->
                {generate_insights_panel(browser_metrics.get('performance_insights', []))}
            </div>
        </div>
        
        <!-- Enhanced Performance Analysis Section -->
        {enhanced_analysis_section}
        
        <!-- Browser Metrics Analysis Section -->
        {browser_analysis_section}
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
        
        // Browser Response Time Distribution Chart
        const browserResponseData = [
            {{
                x: ['P50', 'P75', 'P90', 'P95', 'P99'],
                y: [{browser_metrics.get('p50_response_time', 0):.0f}, {browser_metrics.get('p75_response_time', 0):.0f}, {browser_metrics.get('p90_response_time', 0):.0f}, {browser_metrics.get('p95_response_time', 0):.0f}, {browser_metrics.get('p99_response_time', 0):.0f}],
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
        
        // Browser Connection Breakdown Chart
        const browserConnectionData = [
            {{
                values: [{browser_metrics.get('connection_breakdown', {}).get('http_req_blocked', {}).get('avg', 0):.1f}, {browser_metrics.get('connection_breakdown', {}).get('http_req_connecting', {}).get('avg', 0):.1f}, {browser_metrics.get('connection_breakdown', {}).get('http_req_tls_handshaking', {}).get('avg', 0):.1f}, {browser_metrics.get('connection_breakdown', {}).get('http_req_sending', {}).get('avg', 0):.1f}, {browser_metrics.get('connection_breakdown', {}).get('http_req_waiting', {}).get('avg', 0):.1f}, {browser_metrics.get('connection_breakdown', {}).get('http_req_receiving', {}).get('avg', 0):.1f}],
                labels: ['Blocked', 'Connecting', 'TLS Handshake', 'Sending', 'Waiting', 'Receiving'],
                type: 'pie',
                hole: 0.4,
                marker: {{
                    colors: ['#e74c3c', '#f39c12', '#f1c40f', '#2ecc71', '#3498db', '#9b59b6']
                }}
            }}
        ];
        
        const browserConnectionLayout = {{
            title: 'HTTP Request Time Breakdown (ms)',
            showlegend: true,
            margin: {{ t: 50, b: 50, l: 30, r: 30 }}
        }};
        
        Plotly.newPlot('browserConnectionChart', browserConnectionData, browserConnectionLayout);
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
    
    # Generate HTML report
    html_file = os.path.join(output_dir, "load_test_report.html")
    generate_html_report(protocol_metrics, browser_metrics, html_file)

if __name__ == "__main__":
    main()
