#!/usr/bin/env python3
"""
Generate Readable Reports
Converts JSON analysis data into human-readable formats (HTML, Markdown, Console)
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

def load_json_data(file_path):
    """Load JSON data from file"""
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading {file_path}: {e}")
        return None

def generate_html_report(data, output_path):
    """Generate a beautiful HTML report"""
    html = []
    
    # HTML Header with CSS and JavaScript
    html.append("""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Load Test & Optimization Report</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            color: #333;
            background: #f8f9fa;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }
        
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px 20px;
            text-align: center;
            border-radius: 10px;
            margin-bottom: 30px;
        }
        
        .header h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
        }
        
        .header .timestamp {
            opacity: 0.9;
            font-size: 1.1em;
        }
        
        .card {
            background: white;
            border-radius: 10px;
            padding: 25px;
            margin-bottom: 25px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        
        .card h2 {
            color: #2c3e50;
            margin-bottom: 20px;
            font-size: 1.5em;
            border-bottom: 2px solid #3498db;
            padding-bottom: 10px;
        }
        
        .metrics-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }
        
        .metric {
            text-align: center;
            padding: 20px;
            background: #f8f9fa;
            border-radius: 8px;
            border-left: 4px solid #3498db;
        }
        
        .metric-value {
            font-size: 2em;
            font-weight: bold;
            color: #2c3e50;
        }
        
        .metric-label {
            color: #7f8c8d;
            font-size: 0.9em;
            margin-top: 5px;
        }
        
        .performance-grade {
            display: inline-block;
            padding: 10px 20px;
            border-radius: 25px;
            font-weight: bold;
            font-size: 1.2em;
        }
        
        .grade-a { background: #27ae60; color: white; }
        .grade-b { background: #f39c12; color: white; }
        .grade-c { background: #e67e22; color: white; }
        .grade-d { background: #e74c3c; color: white; }
        .grade-f { background: #c0392b; color: white; }
        
        .recommendation {
            border-left: 4px solid #3498db;
            padding: 20px;
            margin: 15px 0;
            background: #f8f9fa;
            border-radius: 0 8px 8px 0;
        }
        
        .recommendation.high { border-left-color: #e74c3c; }
        .recommendation.medium { border-left-color: #f39c12; }
        .recommendation.low { border-left-color: #27ae60; }
        
        .recommendation h3 {
            color: #2c3e50;
            margin-bottom: 10px;
        }
        
        .priority-badge {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 15px;
            font-size: 0.8em;
            font-weight: bold;
            text-transform: uppercase;
        }
        
        .priority-high { background: #e74c3c; color: white; }
        .priority-medium { background: #f39c12; color: white; }
        .priority-low { background: #27ae60; color: white; }
        
        .implementation-steps {
            background: white;
            padding: 15px;
            border-radius: 5px;
            margin: 15px 0;
        }
        
        .implementation-steps ol {
            margin-left: 20px;
        }
        
        .implementation-steps li {
            margin: 8px 0;
        }
        
        .chart-container {
            position: relative;
            height: 300px;
            margin: 20px 0;
        }
        
        .tag {
            display: inline-block;
            background: #3498db;
            color: white;
            padding: 4px 8px;
            border-radius: 12px;
            font-size: 0.8em;
            margin: 2px;
        }
        
        .footer {
            text-align: center;
            padding: 20px;
            color: #7f8c8d;
            font-size: 0.9em;
        }
    </style>
</head>
<body>
    <div class="container">""")
    
    # Header
    html.append(f"""
        <div class="header">
            <h1>📊 Load Test & Optimization Report</h1>
            <div class="timestamp">Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</div>
        </div>""")
    
    # Test Configuration
    if 'test_configuration' in data:
        config = data['test_configuration']
        html.append(f"""
        <div class="card">
            <h2>🔧 Test Configuration</h2>
            <div class="metrics-grid">
                <div class="metric">
                    <div class="metric-value">{config.get('target', 'N/A')}</div>
                    <div class="metric-label">Target URL</div>
                </div>
                <div class="metric">
                    <div class="metric-value">{config.get('vus', 'N/A')}</div>
                    <div class="metric-label">Virtual Users</div>
                </div>
                <div class="metric">
                    <div class="metric-value">{config.get('duration', 'N/A')}</div>
                    <div class="metric-label">Duration</div>
                </div>
            </div>
            <p><strong>Description:</strong> {config.get('description', 'N/A')}</p>
            <p><strong>Tags:</strong> """)
        
        for tag in config.get('tags', []):
            html.append(f'<span class="tag">{tag}</span>')
        
        html.append("</p></div>")
    
    # Test Results Summary
    if 'test_results' in data:
        results = data['test_results']
        if 'test_summary' in results:
            summary = results['test_summary']
            html.append(f"""
        <div class="card">
            <h2>📈 Test Results Summary</h2>
            <div class="metrics-grid">
                <div class="metric">
                    <div class="metric-value">{summary.get('total_requests', 'N/A'):,}</div>
                    <div class="metric-label">Total Requests</div>
                </div>
                <div class="metric">
                    <div class="metric-value">{summary.get('successful_requests', 'N/A'):,}</div>
                    <div class="metric-label">Successful</div>
                </div>
                <div class="metric">
                    <div class="metric-value">{summary.get('failed_requests', 'N/A'):,}</div>
                    <div class="metric-label">Failed</div>
                </div>
                <div class="metric">
                    <div class="metric-value">{summary.get('average_response_time', 0):.0f}ms</div>
                    <div class="metric-label">Avg Response Time</div>
                </div>
                <div class="metric">
                    <div class="metric-value">{summary.get('error_rate', 0):.2f}%</div>
                    <div class="metric-label">Error Rate</div>
                </div>
            </div>
        </div>""")
    
    # Performance Analysis
    if 'performance_analysis' in data:
        perf = data['performance_analysis']
        grade = perf.get('performance_grade', 'N/A').lower()
        grade_class = f"grade-{grade}" if grade in ['a', 'b', 'c', 'd', 'f'] else "grade-c"
        
        html.append(f"""
        <div class="card">
            <h2>🎯 Performance Analysis</h2>
            <div style="text-align: center; margin: 20px 0;">
                <div class="performance-grade {grade_class}">
                    Grade: {perf.get('performance_grade', 'N/A')} ({perf.get('overall_score', 'N/A')}/100)
                </div>
            </div>
        </div>""")
    
    # Browser Analysis (Core Web Vitals)
    if 'detailed_analysis' in data and 'browser_analysis' in data['detailed_analysis']:
        browser = data['detailed_analysis']['browser_analysis']
        html.append("""
        <div class="card">
            <h2>🌐 Browser Performance Analysis (Core Web Vitals)</h2>""")
        
        # Overall browser score
        browser_score = browser.get('overall_score', 'N/A')
        browser_grade = browser.get('overall_grade', 'N/A').lower()
        browser_grade_class = f"grade-{browser_grade}" if browser_grade in ['a', 'b', 'c', 'd', 'f'] else "grade-c"
        
        html.append(f"""
            <div style="text-align: center; margin: 20px 0;">
                <div class="performance-grade {browser_grade_class}">
                    Browser Grade: {browser.get('overall_grade', 'N/A')} ({browser_score}/100)
                </div>
            </div>""")
        
        # Core Web Vitals
        core_vitals = browser.get('core_web_vitals', {})
        if core_vitals:
            html.append("""
            <h3 style="margin: 20px 0 15px 0; color: #2c3e50;">Core Web Vitals</h3>
            <div class="metrics-grid">""")
            
            for metric, data in core_vitals.items():
                value = data.get('average', 'N/A')
                grade = data.get('grade', 'N/A').lower()
                grade_class = f"grade-{grade}" if grade in ['a', 'b', 'c', 'd', 'f'] else "grade-c"
                
                html.append(f"""
                <div class="metric">
                    <div class="metric-value">{value}ms</div>
                    <div class="metric-label">{data.get('name', metric)}</div>
                    <div class="performance-grade {grade_class}" style="font-size: 0.8em; margin-top: 10px;">
                        Grade: {data.get('grade', 'N/A')}
                    </div>
                </div>""")
            
            html.append("</div>")
        
        # Navigation Timing
        navigation = browser.get('navigation_timing', {})
        if navigation:
            html.append("""
            <h3 style="margin: 30px 0 15px 0; color: #2c3e50;">Navigation Timing</h3>
            <div class="metrics-grid">""")
            
            for metric, data in navigation.items():
                value = data.get('average', 'N/A')
                grade = data.get('grade', 'N/A').lower()
                grade_class = f"grade-{grade}" if grade in ['a', 'b', 'c', 'd', 'f'] else "grade-c"
                
                html.append(f"""
                <div class="metric">
                    <div class="metric-value">{value}ms</div>
                    <div class="metric-label">{data.get('name', metric)}</div>
                    <div class="performance-grade {grade_class}" style="font-size: 0.8em; margin-top: 10px;">
                        Grade: {data.get('grade', 'N/A')}
                    </div>
                </div>""")
            
            html.append("</div>")
        
        # Resource Loading
        resources = browser.get('resource_loading', {})
        if resources:
            html.append("""
            <h3 style="margin: 30px 0 15px 0; color: #2c3e50;">Resource Loading</h3>""")
            
            resource_sizes = resources.get('resource_sizes', {})
            if resource_sizes:
                html.append("""
                <div class="metrics-grid">""")
                
                total_size = resource_sizes.get('total', 0) / 1024 / 1024  # Convert to MB
                avg_size = resource_sizes.get('average', 0) / 1024  # Convert to KB
                
                html.append(f"""
                <div class="metric">
                    <div class="metric-value">{total_size:.1f}MB</div>
                    <div class="metric-label">Total Size</div>
                </div>
                <div class="metric">
                    <div class="metric-value">{avg_size:.1f}KB</div>
                    <div class="metric-label">Average Size</div>
                </div>""")
                
                html.append("</div>")
            
            resource_counts = resources.get('resource_counts', {})
            if resource_counts:
                html.append("<h4 style='margin: 20px 0 10px 0; color: #2c3e50;'>Resource Counts by Type</h4>")
                html.append("<div style='display: flex; flex-wrap: wrap; gap: 10px;'>")
                
                for resource_type, count in resource_counts.items():
                    html.append(f"""
                    <div style='background: #f8f9fa; padding: 10px 15px; border-radius: 5px; border-left: 4px solid #3498db;'>
                        <strong>{resource_type}:</strong> {count}
                    </div>""")
                
                html.append("</div>")
        
        # User Interactions
        interactions = browser.get('user_interactions', {})
        if interactions:
            html.append("""
            <h3 style="margin: 30px 0 15px 0; color: #2c3e50;">User Interactions</h3>""")
            
            if 'script_execution' in interactions:
                script_data = interactions['script_execution']
                html.append("""
                <div class="metrics-grid">""")
                
                html.append(f"""
                <div class="metric">
                    <div class="metric-value">{script_data.get('average', 'N/A')}ms</div>
                    <div class="metric-label">Script Execution (Avg)</div>
                </div>
                <div class="metric">
                    <div class="metric-value">{script_data.get('max', 'N/A')}ms</div>
                    <div class="metric-label">Script Execution (Max)</div>
                </div>
                <div class="metric">
                    <div class="metric-value">{script_data.get('count', 'N/A')}</div>
                    <div class="metric-label">Interactions</div>
                </div>""")
                
                html.append("</div>")
            
            if 'layout_shifts' in interactions:
                shift_count = interactions['layout_shifts']
                shift_color = "#e74c3c" if shift_count > 0 else "#27ae60"
                html.append(f"""
                <div style='margin: 20px 0; padding: 15px; background: #f8f9fa; border-radius: 5px; border-left: 4px solid {shift_color};'>
                    <strong>Layout Shifts:</strong> {shift_count} detected
                    {f" ⚠️ Layout shifts may impact user experience" if shift_count > 0 else " ✅ No layout shifts detected"}
                </div>""")
        
        # Browser Performance Insights
        insights = browser.get('performance_insights', [])
        if insights:
            html.append("""
            <h3 style="margin: 30px 0 15px 0; color: #2c3e50;">Browser Performance Issues</h3>""")
            
            for insight in insights[:5]:  # Show top 5 insights
                severity = insight.get('severity', 'medium').lower()
                severity_class = f"priority-{severity}"
                
                html.append(f"""
                <div class="recommendation {severity}">
                    <h3>{insight.get('issue', 'N/A')}</h3>
                    <span class="priority-badge {severity_class}">{insight.get('severity', 'N/A').upper()}</span>
                    <p style="margin: 15px 0;"><strong>Recommendation:</strong> {insight.get('recommendation', 'N/A')}</p>
                </div>""")
        
        html.append("</div>")
    
    # AI Recommendations
    if 'recommendations' in data:
        html.append("""
        <div class="card">
            <h2>🤖 AI-Generated Recommendations</h2>""")
        
        # Show model information if available
        if 'ai_analysis' in data and 'model_used' in data['ai_analysis']:
            model_used = data['ai_analysis']['model_used']
            model_badge_class = "priority-high" if model_used == "fallback" else "priority-low"
            html.append(f"""
            <div style="margin-bottom: 20px; padding: 10px; background: #f8f9fa; border-radius: 5px;">
                <strong>AI Model Used:</strong> <span class="priority-badge {model_badge_class}">{model_used}</span>
                <span style="margin-left: 10px; color: #7f8c8d; font-size: 0.9em;">
                    {f"⚠️ Fallback analysis used due to API issues" if model_used == "fallback" else "✅ AI analysis completed successfully"}
                </span>
            </div>""")
        
        for i, rec in enumerate(data['recommendations'], 1):
            priority = rec.get('priority', 'N/A').lower()
            priority_class = f"priority-{priority}"
            
            html.append(f"""
            <div class="recommendation {priority}">
                <h3>#{i} {rec.get('title', 'N/A')}</h3>
                <span class="priority-badge {priority_class}">{rec.get('priority', 'N/A')}</span>
                <span style="margin-left: 10px; color: #7f8c8d;">Impact: {rec.get('impact', 'N/A')} | Effort: {rec.get('effort', 'N/A')}</span>
                <p style="margin: 15px 0;"><strong>Description:</strong> {rec.get('description', 'N/A')}</p>""")
            
            if 'implementation' in rec and rec['implementation']:
                html.append("""
                <div class="implementation-steps">
                    <strong>Implementation Steps:</strong>
                    <ol>""")
                for step in rec['implementation']:
                    html.append(f"<li>{step}</li>")
                html.append("</ol></div>")
            
            if 'expected_improvement' in rec:
                html.append(f'<p><strong>Expected Improvement:</strong> {rec["expected_improvement"]}</p>')
            
            if 'data_support' in rec:
                html.append(f'<p><strong>Data Support:</strong> {rec["data_support"]}</p>')
            
            html.append("</div>")
        
        html.append("</div>")
    
    # Technology Template
    if 'technology_template' in data:
        template = data['technology_template']
        html.append(f"""
        <div class="card">
            <h2>🔧 Technology-Specific Insights</h2>
            <p><strong>Template:</strong> {template.get('name', 'N/A')}</p>
            <p><strong>Description:</strong> {template.get('description', 'N/A')}</p>""")
        
        if 'optimization_areas' in template:
            areas = template['optimization_areas']
            for area_type, area_list in areas.items():
                if area_list:
                    html.append(f"<h3 style='margin: 20px 0 10px 0; color: #2c3e50;'>{area_type.title()} Optimizations</h3>")
                    for area in area_list:
                        html.append(f"""
                        <div style='margin: 15px 0; padding: 15px; background: #f8f9fa; border-radius: 5px;'>
                            <h4 style='color: #2c3e50; margin-bottom: 10px;'>{area.get('name', 'N/A')}</h4>
                            <p>{area.get('description', 'N/A')}</p>""")
                        
                        if 'recommendations' in area and area['recommendations']:
                            html.append("<ul style='margin: 10px 0;'>")
                            for rec in area['recommendations']:
                                html.append(f"<li>{rec}</li>")
                            html.append("</ul>")
                        
                        html.append("</div>")
        
        html.append("</div>")
    
    # Footer
    html.append("""
        <div class="footer">
            <p>Generated by Load Testing & Optimization Agent</p>
            <p>For detailed JSON data, check the original analysis files</p>
        </div>
    </div>
</body>
</html>""")
    
    # Write the HTML file
    with open(output_path, 'w') as f:
        f.write(''.join(html))
    
    print(f"✅ HTML report generated: {output_path}")

def generate_markdown_report(data, output_path):
    """Generate a Markdown report"""
    report = []
    
    # Header
    report.append("# Load Test & Optimization Report")
    report.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append("")
    
    # Test Configuration
    if 'test_configuration' in data:
        config = data['test_configuration']
        report.append("## Test Configuration")
        report.append(f"- **Target URL:** {config.get('target', 'N/A')}")
        report.append(f"- **Virtual Users:** {config.get('vus', 'N/A')}")
        report.append(f"- **Duration:** {config.get('duration', 'N/A')}")
        report.append(f"- **Description:** {config.get('description', 'N/A')}")
        report.append(f"- **Tags:** {', '.join(config.get('tags', []))}")
        report.append("")
    
    # Test Results Summary
    if 'test_results' in data:
        results = data['test_results']
        if 'test_summary' in results:
            summary = results['test_summary']
            report.append("## Test Results Summary")
            report.append(f"- **Total Requests:** {summary.get('total_requests', 'N/A'):,}")
            report.append(f"- **Successful Requests:** {summary.get('successful_requests', 'N/A'):,}")
            report.append(f"- **Failed Requests:** {summary.get('failed_requests', 'N/A'):,}")
            report.append(f"- **Average Response Time:** {summary.get('average_response_time', 0):.0f}ms")
            report.append(f"- **Error Rate:** {summary.get('error_rate', 0):.2f}%")
            report.append("")
    
    # Performance Analysis
    if 'performance_analysis' in data:
        perf = data['performance_analysis']
        report.append("## Performance Analysis")
        report.append(f"- **Grade:** {perf.get('performance_grade', 'N/A')}")
        report.append(f"- **Score:** {perf.get('overall_score', 'N/A')}/100")
        report.append("")
    
    # Browser Analysis (Core Web Vitals)
    if 'detailed_analysis' in data and 'browser_analysis' in data['detailed_analysis']:
        browser = data['detailed_analysis']['browser_analysis']
        report.append("## Browser Performance Analysis (Core Web Vitals)")
        report.append(f"- **Browser Grade:** {browser.get('overall_grade', 'N/A')}")
        report.append(f"- **Browser Score:** {browser.get('overall_score', 'N/A')}/100")
        report.append("")
        
        # Core Web Vitals
        core_vitals = browser.get('core_web_vitals', {})
        if core_vitals:
            report.append("### Core Web Vitals")
            for metric, data in core_vitals.items():
                report.append(f"- **{data.get('name', metric)}:** {data.get('average', 'N/A')}ms (Grade: {data.get('grade', 'N/A')})")
            report.append("")
        
        # Navigation Timing
        navigation = browser.get('navigation_timing', {})
        if navigation:
            report.append("### Navigation Timing")
            for metric, data in navigation.items():
                report.append(f"- **{data.get('name', metric)}:** {data.get('average', 'N/A')}ms (Grade: {data.get('grade', 'N/A')})")
            report.append("")
        
        # Resource Loading
        resources = browser.get('resource_loading', {})
        if resources:
            report.append("### Resource Loading")
            resource_sizes = resources.get('resource_sizes', {})
            if resource_sizes:
                total_size = resource_sizes.get('total', 0) / 1024 / 1024  # Convert to MB
                avg_size = resource_sizes.get('average', 0) / 1024  # Convert to KB
                report.append(f"- **Total Size:** {total_size:.1f}MB")
                report.append(f"- **Average Size:** {avg_size:.1f}KB")
            
            resource_counts = resources.get('resource_counts', {})
            if resource_counts:
                report.append("- **Resource Counts:**")
                for resource_type, count in resource_counts.items():
                    report.append(f"  - {resource_type}: {count}")
            report.append("")
        
        # User Interactions
        interactions = browser.get('user_interactions', {})
        if interactions:
            report.append("### User Interactions")
            if 'script_execution' in interactions:
                script_data = interactions['script_execution']
                report.append(f"- **Script Execution (Avg):** {script_data.get('average', 'N/A')}ms")
                report.append(f"- **Script Execution (Max):** {script_data.get('max', 'N/A')}ms")
                report.append(f"- **Interactions:** {script_data.get('count', 'N/A')}")
            
            if 'layout_shifts' in interactions:
                shift_count = interactions['layout_shifts']
                report.append(f"- **Layout Shifts:** {shift_count} detected")
            report.append("")
        
        # Browser Performance Insights
        insights = browser.get('performance_insights', [])
        if insights:
            report.append("### Browser Performance Issues")
            for insight in insights[:5]:  # Show top 5 insights
                report.append(f"- **{insight.get('severity', 'N/A').upper()}:** {insight.get('issue', 'N/A')}")
                report.append(f"  - Recommendation: {insight.get('recommendation', 'N/A')}")
            report.append("")
    
    # AI Recommendations
    if 'recommendations' in data:
        report.append("## AI-Generated Recommendations")
        report.append("")
        
        for i, rec in enumerate(data['recommendations'], 1):
            priority_emoji = {
                'high': '🔴',
                'medium': '🟡', 
                'low': '🟢'
            }.get(rec.get('priority', '').lower(), '⚪')
            
            report.append(f"### {priority_emoji} {i}. {rec.get('title', 'N/A')}")
            report.append(f"**Priority:** {rec.get('priority', 'N/A')} | **Impact:** {rec.get('impact', 'N/A')} | **Effort:** {rec.get('effort', 'N/A')}")
            report.append("")
            report.append(f"**Description:** {rec.get('description', 'N/A')}")
            report.append("")
            
            if 'implementation' in rec and rec['implementation']:
                report.append("**Implementation Steps:**")
                for step in rec['implementation']:
                    report.append(f"- {step}")
                report.append("")
            
            if 'expected_improvement' in rec:
                report.append(f"**Expected Improvement:** {rec['expected_improvement']}")
                report.append("")
            
            if 'data_support' in rec:
                report.append(f"**Data Support:** {rec['data_support']}")
                report.append("")
    
    # Technology Template
    if 'technology_template' in data:
        template = data['technology_template']
        report.append("## Technology-Specific Insights")
        report.append(f"**Template:** {template.get('name', 'N/A')}")
        report.append(f"**Description:** {template.get('description', 'N/A')}")
        report.append("")
        
        if 'optimization_areas' in template:
            areas = template['optimization_areas']
            for area_type, area_list in areas.items():
                if area_list:
                    report.append(f"### {area_type.title()} Optimizations")
                    for area in area_list:
                        report.append(f"#### {area.get('name', 'N/A')}")
                        report.append(f"{area.get('description', 'N/A')}")
                        report.append("")
                        if 'recommendations' in area and area['recommendations']:
                            report.append("**Recommendations:**")
                            for rec in area['recommendations']:
                                report.append(f"- {rec}")
                            report.append("")
    
    # Write the report
    with open(output_path, 'w') as f:
        f.write('\n'.join(report))
    
    print(f"✅ Markdown report generated: {output_path}")

def generate_console_summary(data):
    """Generate a console-friendly summary"""
    print("\n" + "="*60)
    print("📊 LOAD TEST & OPTIMIZATION SUMMARY")
    print("="*60)
    
    # Test Configuration
    if 'test_configuration' in data:
        config = data['test_configuration']
        print(f"🌐 Target: {config.get('target', 'N/A')}")
        print(f"👥 Virtual Users: {config.get('vus', 'N/A')}")
        print(f"⏰ Duration: {config.get('duration', 'N/A')}")
        print()
    
    # Test Results
    if 'test_results' in data and 'test_summary' in data['test_results']:
        summary = data['test_results']['test_summary']
        print("📈 PERFORMANCE METRICS")
        print(f"   Total Requests: {summary.get('total_requests', 'N/A'):,}")
        print(f"   Success Rate: {100 - summary.get('error_rate', 0):.1f}%")
        print(f"   Avg Response Time: {summary.get('average_response_time', 0):.0f}ms")
        print()
    
    # Performance Grade
    if 'performance_analysis' in data:
        perf = data['performance_analysis']
        grade = perf.get('performance_grade', 'N/A')
        score = perf.get('overall_score', 'N/A')
        print(f"🎯 PERFORMANCE GRADE: {grade} ({score}/100)")
        print()
    
    # Top Recommendations
    if 'recommendations' in data:
        print("🔧 TOP RECOMMENDATIONS")
        for i, rec in enumerate(data['recommendations'][:3], 1):  # Show top 3
            priority = rec.get('priority', 'N/A')
            title = rec.get('title', 'N/A')
            impact = rec.get('impact', 'N/A')
            print(f"   {i}. [{priority.upper()}] {title} (Impact: {impact})")
        print()
    
    print("="*60)
    print("📄 Full reports available in HTML, Markdown and JSON formats")
    print("="*60)

def main():
    """Main function"""
    if len(sys.argv) < 2:
        print("Usage: python scripts/generate_readable_report.py <ai_analysis_report.json>")
        sys.exit(1)
    
    json_file = sys.argv[1]
    if not os.path.exists(json_file):
        print(f"Error: File not found: {json_file}")
        sys.exit(1)
    
    # Load data
    data = load_json_data(json_file)
    if not data:
        sys.exit(1)
    
    # Generate reports
    base_name = Path(json_file).stem
    output_dir = Path(json_file).parent
    
    # HTML report
    html_file = output_dir / f"{base_name}_report.html"
    generate_html_report(data, html_file)
    
    # Markdown report
    markdown_file = output_dir / f"{base_name}_report.md"
    generate_markdown_report(data, markdown_file)
    
    # Console summary
    generate_console_summary(data)

if __name__ == "__main__":
    main() 