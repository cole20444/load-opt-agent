#!/usr/bin/env python3
"""
Manual HTML Report Generator
Creates HTML report from existing analysis files
"""

import json
import os
import sys
from datetime import datetime

def load_analysis_file(file_path):
    """Load analysis JSON file"""
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading {file_path}: {e}")
        return None

def generate_html_report(output_dir):
    """Generate HTML report from analysis files"""
    
    # Load analysis files
    enhanced_analysis = load_analysis_file(os.path.join(output_dir, 'enhanced_analysis_report.json'))
    browser_analysis = load_analysis_file(os.path.join(output_dir, 'browser_summary_analysis.json'))
    
    if not enhanced_analysis:
        print("❌ Enhanced analysis file not found")
        return
    
    # Extract metrics from enhanced analysis
    summary = enhanced_analysis.get('summary', {})
    issues_data = enhanced_analysis.get('issues', {})
    recommendations = enhanced_analysis.get('recommendations', [])
    
    # Flatten issues by severity
    issues = []
    for severity, issue_list in issues_data.items():
        for issue in issue_list:
            issue['severity'] = severity
            issues.append(issue)
    
    # Extract browser metrics if available
    browser_summary = {}
    browser_issues = []
    if browser_analysis:
        browser_summary = browser_analysis.get('summary', {})
        browser_issues = browser_analysis.get('performance_insights', [])
    
    # Generate HTML
    html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Load Test Report - Manual Generation</title>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
        }}
        
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 20px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            overflow: hidden;
        }}
        
        .header {{
            background: linear-gradient(135deg, #2c3e50 0%, #34495e 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }}
        
        .header h1 {{
            margin: 0;
            font-size: 2.5em;
            font-weight: 700;
        }}
        
        .timestamp {{
            margin-top: 10px;
            opacity: 0.8;
            font-size: 1.1em;
        }}
        
        .card {{
            background: white;
            border-radius: 15px;
            padding: 25px;
            margin: 25px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.08);
            border: 1px solid #e9ecef;
        }}
        
        .card h2 {{
            color: #2c3e50;
            margin-bottom: 20px;
            font-size: 1.8em;
            font-weight: 600;
        }}
        
        .summary-stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
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
        
        .issue {{
            background: #fff5f5;
            border: 1px solid #fed7d7;
            border-radius: 8px;
            padding: 15px;
            margin: 10px 0;
        }}
        
        .issue.high {{
            border-left: 4px solid #e53e3e;
        }}
        
        .issue.medium {{
            border-left: 4px solid #d69e2e;
        }}
        
        .issue.low {{
            border-left: 4px solid #38a169;
        }}
        
        .issue h4 {{
            margin: 0 0 10px 0;
            color: #2c3e50;
        }}
        
        .recommendation {{
            background: #f0fff4;
            border: 1px solid #c6f6d5;
            border-radius: 8px;
            padding: 15px;
            margin: 10px 0;
        }}
        
        .recommendation h4 {{
            margin: 0 0 10px 0;
            color: #2c3e50;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Load Test Report</h1>
            <div class="timestamp">Manual Generation from Analysis Files</div>
            <div class="timestamp">Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</div>
        </div>
        
        <!-- Executive Summary -->
        <div class="card">
            <h2>Executive Summary</h2>
            
            <div class="summary-stats">
                <div class="performance-grade">
                    <div class="label">Overall Performance Grade</div>
                    <div class="score">{summary.get('performance_score', 0)}/100</div>
                </div>
                <div class="stat">
                    <div class="label">Total Issues Found</div>
                    <div class="value">{summary.get('total_issues', 0)}</div>
                </div>
                <div class="stat">
                    <div class="label">High Priority Issues</div>
                    <div class="value">{summary.get('high_priority', 0)}</div>
                </div>
                <div class="stat">
                    <div class="label">Medium Priority Issues</div>
                    <div class="value">{summary.get('medium_priority', 0)}</div>
                </div>
            </div>
        </div>
        
        <!-- Enhanced Performance Analysis -->
        <div class="card">
            <h2>Enhanced Performance Analysis</h2>
            
            <h3>Performance Issues</h3>
            {generate_issues_html(issues)}
            
            <h3>Recommendations</h3>
            {generate_recommendations_html(recommendations)}
        </div>
        
        <!-- Browser Analysis (if available) -->
        {generate_browser_section(browser_summary, browser_issues) if browser_analysis else ''}
    </div>
</body>
</html>
"""
    
    # Write HTML file
    output_path = os.path.join(output_dir, 'manual_load_test_report.html')
    with open(output_path, 'w') as f:
        f.write(html)
    
    print(f"✅ Manual HTML report generated: {output_path}")

def generate_issues_html(issues):
    """Generate HTML for issues"""
    if not issues:
        return '<p>No issues found.</p>'
    
    html_parts = []
    for issue in issues:
        severity = issue.get('severity', 'medium').lower()
        html_parts.append(f'''
        <div class="issue {severity}">
            <h4>{issue.get('title', 'Performance Issue')}</h4>
            <p><strong>Description:</strong> {issue.get('description', 'No description available')}</p>
            <p><strong>Recommendation:</strong> {issue.get('recommendation', 'No recommendation available')}</p>
        </div>
        ''')
    
    return '\n'.join(html_parts)

def generate_recommendations_html(recommendations):
    """Generate HTML for recommendations"""
    if not recommendations:
        return '<p>No recommendations available.</p>'
    
    html_parts = []
    for rec in recommendations:
        html_parts.append(f'''
        <div class="recommendation">
            <h4>{rec.get('title', 'Recommendation')}</h4>
            <p><strong>Category:</strong> {rec.get('category', 'General')}</p>
            <p><strong>Description:</strong> {rec.get('description', 'No description available')}</p>
            <p><strong>Actions:</strong></p>
            <ul>
                {generate_actions_html(rec.get('actions', []))}
            </ul>
        </div>
        ''')
    
    return '\n'.join(html_parts)

def generate_actions_html(actions):
    """Generate HTML for actions"""
    if not actions:
        return '<li>No specific actions defined</li>'
    
    return '\n'.join([f'<li>{action}</li>' for action in actions])

def generate_browser_section(browser_summary, browser_issues):
    """Generate browser analysis section"""
    if not browser_summary:
        return ''
    
    return f'''
        <div class="card">
            <h2>Browser Performance Analysis</h2>
            
            <div class="summary-stats">
                <div class="stat">
                    <div class="label">Browser Performance Score</div>
                    <div class="value">{browser_summary.get('performance_score', 0)}/100</div>
                </div>
                <div class="stat">
                    <div class="label">Total Requests</div>
                    <div class="value">{browser_summary.get('total_requests', 0):,}</div>
                </div>
                <div class="stat">
                    <div class="label">Page Weight</div>
                    <div class="value">{browser_summary.get('total_page_weight_mb', 0):.2f}MB</div>
                </div>
            </div>
            
            <h3>Core Web Vitals</h3>
            {generate_core_web_vitals_html(browser_summary.get('core_web_vitals', {}))}
            
            <h3>Browser Performance Issues</h3>
            {generate_issues_html(browser_issues)}
        </div>
    '''

def generate_core_web_vitals_html(cwv):
    """Generate HTML for Core Web Vitals"""
    if not cwv:
        return '<p>No Core Web Vitals data available.</p>'
    
    html_parts = []
    for metric, value in cwv.items():
        if isinstance(value, dict) and 'avg' in value:
            html_parts.append(f'''
            <div class="stat">
                <div class="label">{metric.replace('_', ' ').title()}</div>
                <div class="value">{value['avg']:.0f}ms</div>
            </div>
            ''')
    
    return f'<div class="summary-stats">{"".join(html_parts)}</div>'

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python generate_manual_report.py <output_directory>")
        sys.exit(1)
    
    output_dir = sys.argv[1]
    if not os.path.exists(output_dir):
        print(f"❌ Output directory not found: {output_dir}")
        sys.exit(1)
    
    generate_html_report(output_dir)
