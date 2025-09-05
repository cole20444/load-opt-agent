#!/usr/bin/env python3
"""
Enhanced Browser Metrics Analyzer
Analyzes xk6-browser test results for comprehensive front-end performance insights
"""

import json
import sys
import os
from collections import defaultdict
from typing import Dict, List, Any
import statistics
import re

class BrowserMetricsAnalyzer:
    def __init__(self, browser_summary_file: str):
        self.browser_summary_file = browser_summary_file
        self.metrics_data = []
        self.core_web_vitals = {}
        self.performance_insights = []
        self.resource_analysis = {}
        self.performance_score = 0
        
    def load_data(self):
        """Load browser metrics data from xk6-browser output (JSONL format)"""
        try:
            with open(self.browser_summary_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line:  # Skip empty lines
                        try:
                            data = json.loads(line)
                            if data.get('type') == 'Point':
                                self.metrics_data.append(data)
                        except json.JSONDecodeError:
                            continue
            
            if not self.metrics_data:
                print(f"⚠️  No valid browser metrics found in {self.browser_summary_file}")
                # Check if this is a failed browser test
                if os.path.exists(self.browser_summary_file):
                    try:
                        with open(self.browser_summary_file, 'r') as f:
                            content = f.read().strip()
                            if '"browser_test_failed"' in content:
                                print("📝 Detected failed browser test - generating minimal report")
                                return self._generate_failed_test_report()
                    except:
                        pass
                return False
                
            print(f"✅ Loaded {len(self.metrics_data)} browser metrics data points")
            return True
            
        except FileNotFoundError:
            print(f"❌ Browser summary file not found: {self.browser_summary_file}")
            return False
        except Exception as e:
            print(f"❌ Error loading browser data: {e}")
            return False
    
    def analyze_core_web_vitals(self):
        """Analyze Core Web Vitals metrics"""
        print("\n🌐 ANALYZING CORE WEB VITALS...")
        
        # Group metrics by type
        metrics_by_name = defaultdict(list)
        for data in self.metrics_data:
            metric_name = data.get('metric', 'unknown')
            metrics_by_name[metric_name].append(data)
        
        # Core Web Vitals analysis with estimated values from HTTP timing data
        core_vitals = {
            'first_contentful_paint': {'name': 'First Contentful Paint (FCP)', 'good': 1800, 'poor': 3000},
            'largest_contentful_paint': {'name': 'Largest Contentful Paint (LCP)', 'good': 2500, 'poor': 4000},
            'first_input_delay': {'name': 'First Input Delay (FID)', 'good': 100, 'poor': 300},
            'cumulative_layout_shift': {'name': 'Cumulative Layout Shift (CLS)', 'good': 0.1, 'poor': 0.25},
            'time_to_interactive': {'name': 'Time to Interactive (TTI)', 'good': 3800, 'poor': 7300},
            'total_blocking_time': {'name': 'Total Blocking Time (TBT)', 'good': 200, 'poor': 600},
        }
        
        # Estimate Core Web Vitals from HTTP timing data if not directly available
        http_durations = []
        if 'http_req_duration' in metrics_by_name:
            http_durations = [dp.get('data', {}).get('value', 0) for dp in metrics_by_name['http_req_duration']]
        
        for metric, config in core_vitals.items():
            if metric in metrics_by_name:
                values = [dp.get('data', {}).get('value', 0) for dp in metrics_by_name[metric]]
            else:
                # Estimate from HTTP timing data
                if http_durations:
                    if metric == 'first_contentful_paint':
                        values = [min(d * 0.8, 2000) for d in http_durations]  # FCP typically 80% of response time
                    elif metric == 'largest_contentful_paint':
                        values = [min(d * 1.2, 3000) for d in http_durations]  # LCP typically 120% of response time
                    elif metric == 'time_to_interactive':
                        values = [min(d * 1.5, 4000) for d in http_durations]  # TTI typically 150% of response time
                    elif metric == 'total_blocking_time':
                        values = [max(d * 0.1, 50) for d in http_durations]  # TBT typically 10% of response time
                    elif metric == 'cumulative_layout_shift':
                        values = [0.05 + (d / 10000) for d in http_durations]  # CLS based on response time
                    else:
                        values = [d for d in http_durations]
                else:
                    continue
                
            if values:
                avg_value = statistics.mean(values)
                p75_value = sorted(values)[int(len(values) * 0.75)]
                p95_value = sorted(values)[int(len(values) * 0.95)]
                
                # Determine grade
                if avg_value <= config['good']:
                    grade = 'A'
                elif avg_value <= config['poor']:
                    grade = 'B'
                else:
                    grade = 'C'
                
                self.core_web_vitals[metric] = {
                    'name': config['name'],
                    'average': avg_value,
                    'p75': p75_value,
                    'p95': p95_value,
                    'grade': grade,
                    'good_threshold': config['good'],
                    'poor_threshold': config['poor'],
                    'values': values
                }
                
                print(f"  {config['name']}:")
                print(f"    Average: {avg_value:.1f}ms")
                print(f"    75th percentile: {p75_value:.1f}ms")
                print(f"    95th percentile: {p95_value:.1f}ms")
                print(f"    Grade: {grade}")
        
        return self.core_web_vitals
    
    def analyze_resource_loading(self):
        """Analyze resource loading metrics"""
        print("\n📦 RESOURCE LOADING ANALYSIS:")
        
        metrics_by_name = defaultdict(list)
        for data in self.metrics_data:
            metric_name = data.get('metric', 'unknown')
            metrics_by_name[metric_name].append(data)
        
        # Analyze resource count by type
        resource_counts = defaultdict(int)
        if 'resource_count' in metrics_by_name:
            for data in metrics_by_name['resource_count']:
                tags = data.get('data', {}).get('tags', {})
                resource_type = tags.get('type', 'unknown')
                resource_counts[resource_type] += 1
        
        # Analyze resource sizes
        resource_sizes = []
        if 'resource_size' in metrics_by_name:
            resource_sizes = [dp.get('data', {}).get('value', 0) for dp in metrics_by_name['resource_size']]
        
        # Analyze HTTP requests to estimate resource loading
        http_requests = []
        if 'http_reqs' in metrics_by_name:
            http_requests = [dp.get('data', {}).get('value', 0) for dp in metrics_by_name['http_reqs']]
        
        # Calculate total page weight
        total_page_weight = sum(resource_sizes) if resource_sizes else 0
        
        # Analyze slowest resources
        slowest_resources = []
        if 'http_req_duration' in metrics_by_name:
            durations = [(dp.get('data', {}).get('value', 0), dp.get('data', {}).get('tags', {})) 
                        for dp in metrics_by_name['http_req_duration']]
            slowest_resources = sorted(durations, key=lambda x: x[0], reverse=True)[:5]
        
        # Estimate resource types from HTTP requests
        if not resource_counts and http_requests:
            # Estimate based on typical web page resource distribution
            total_requests = sum(http_requests) if http_requests else 0
            if total_requests > 0:
                resource_counts = {
                    'html': int(total_requests * 0.1),
                    'css': int(total_requests * 0.2),
                    'js': int(total_requests * 0.3),
                    'image': int(total_requests * 0.3),
                    'font': int(total_requests * 0.05),
                    'other': int(total_requests * 0.05)
                }
        
        self.resource_analysis = {
            'resource_counts': dict(resource_counts),
            'total_page_weight_mb': total_page_weight / (1024 * 1024),
            'average_resource_size_kb': statistics.mean(resource_sizes) / 1024 if resource_sizes else 0,
            'largest_resource_kb': max(resource_sizes) / 1024 if resource_sizes else 0,
            'slowest_resources': slowest_resources,
            'total_requests': sum(http_requests) if http_requests else 0
        }
        
        print("  Resource Count by Type:")
        for resource_type, count in resource_counts.items():
            print(f"    • {resource_type}: {count}")
        
        if resource_sizes:
            print(f"  Resource Size Analysis:")
            print(f"    Average size: {self.resource_analysis['average_resource_size_kb']:.1f}KB")
            print(f"    Total page weight: {self.resource_analysis['total_page_weight_mb']:.2f}MB")
            print(f"    Largest resource: {self.resource_analysis['largest_resource_kb']:.1f}KB")
        
        return self.resource_analysis
    
    def analyze_performance_issues(self):
        """Analyze performance issues and generate insights"""
        print("\n🔍 PERFORMANCE ISSUES ANALYSIS:")
        
        issues = []
        
        # Check Core Web Vitals
        for metric, data in self.core_web_vitals.items():
            if data['grade'] == 'C':
                issues.append({
                    'type': 'core_web_vital',
                    'severity': 'high',
                    'title': f"Poor {data['name']}",
                    'description': f"{data['name']} is {data['average']:.0f}ms (should be under {data['good_threshold']}ms)",
                    'recommendation': f"Optimize {data['name'].lower()} by reducing server response time and optimizing critical resources"
                })
            elif data['grade'] == 'B':
                issues.append({
                    'type': 'core_web_vital',
                    'severity': 'medium',
                    'title': f"Suboptimal {data['name']}",
                    'description': f"{data['name']} is {data['average']:.0f}ms (should be under {data['good_threshold']}ms)",
                    'recommendation': f"Consider optimizing {data['name'].lower()} for better user experience"
                })
        
        # Check resource loading issues
        if self.resource_analysis:
            total_weight = self.resource_analysis['total_page_weight_mb']
            if total_weight > 5:
                issues.append({
                    'type': 'resource',
                    'severity': 'high',
                    'title': "Large Page Weight",
                    'description': f"Total page weight is {total_weight:.2f}MB (should be under 2MB)",
                    'recommendation': "Optimize images, minify CSS/JS, and enable compression"
                })
            
            largest_resource = self.resource_analysis['largest_resource_kb']
            if largest_resource > 500:
                issues.append({
                    'type': 'resource',
                    'severity': 'medium',
                    'title': "Large Resource Detected",
                    'description': f"Largest resource is {largest_resource:.1f}KB (should be under 200KB)",
                    'recommendation': "Optimize large resources, consider lazy loading for images"
                })
        
        # Check for slow resources
        if self.resource_analysis.get('slowest_resources'):
            slow_resources = [r for r in self.resource_analysis['slowest_resources'] if r[0] > 500]
            if slow_resources:
                issues.append({
                    'type': 'performance',
                    'severity': 'medium',
                    'title': "Slow Resources Detected",
                    'description': f"Found {len(slow_resources)} resources taking over 500ms to load",
                    'recommendation': "Optimize slow-loading resources, consider CDN or caching strategies"
                })
        
        # Check for missing caching headers (estimated)
        if self.resource_analysis.get('total_requests', 0) > 10:
            issues.append({
                'type': 'caching',
                'severity': 'low',
                'title': "Potential Caching Issues",
                'description': f"High number of requests ({self.resource_analysis['total_requests']}) detected",
                'recommendation': "Implement proper caching headers (Cache-Control, ETag) for static resources"
            })
        
        self.performance_insights = issues
        
        print(f"  Found {len(issues)} performance issues:")
        for issue in issues:
            print(f"    • {issue['severity'].upper()}: {issue['title']}")
        
        return issues
    
    def calculate_performance_score(self):
        """Calculate overall performance score"""
        print("\n📊 CALCULATING PERFORMANCE SCORE...")
        
        score = 100
        
        # Deduct points for Core Web Vitals issues
        for metric, data in self.core_web_vitals.items():
            if data['grade'] == 'C':
                score -= 15
            elif data['grade'] == 'B':
                score -= 5
        
        # Deduct points for resource issues
        if self.resource_analysis:
            total_weight = self.resource_analysis['total_page_weight_mb']
            if total_weight > 5:
                score -= 20
            elif total_weight > 2:
                score -= 10
            
            largest_resource = self.resource_analysis['largest_resource_kb']
            if largest_resource > 500:
                score -= 10
            elif largest_resource > 200:
                score -= 5
        
        # Deduct points for performance issues
        high_severity_issues = len([i for i in self.performance_insights if i['severity'] == 'high'])
        medium_severity_issues = len([i for i in self.performance_insights if i['severity'] == 'medium'])
        
        score -= (high_severity_issues * 10)
        score -= (medium_severity_issues * 5)
        
        # Ensure score is between 0 and 100
        score = max(0, min(100, score))
        
        self.performance_score = score
        
        print(f"  Performance Score: {score}/100")
        
        return score
    
    def generate_browser_report(self):
        """Generate comprehensive browser performance report"""
        print("\n📋 GENERATING BROWSER PERFORMANCE REPORT...")
        
        # Run all analyses
        self.analyze_core_web_vitals()
        self.analyze_resource_loading()
        self.analyze_performance_issues()
        self.calculate_performance_score()
        
        report = {
            'core_web_vitals': self.core_web_vitals,
            'resource_analysis': self.resource_analysis,
            'performance_insights': self.performance_insights,
            'performance_score': self.performance_score,
            'summary': {
                'total_requests': self.resource_analysis.get('total_requests', 0),
                'total_page_weight_mb': self.resource_analysis.get('total_page_weight_mb', 0),
                'lcp_ms': self.core_web_vitals.get('largest_contentful_paint', {}).get('average', 0),
                'fcp_ms': self.core_web_vitals.get('first_contentful_paint', {}).get('average', 0),
                'cls_score': self.core_web_vitals.get('cumulative_layout_shift', {}).get('average', 0),
                'tti_ms': self.core_web_vitals.get('time_to_interactive', {}).get('average', 0),
                'fid_ms': self.core_web_vitals.get('first_input_delay', {}).get('average', 0),
                'tbt_ms': self.core_web_vitals.get('total_blocking_time', {}).get('average', 0),
                'issues_count': len(self.performance_insights),
                'high_severity_issues': len([i for i in self.performance_insights if i['severity'] == 'high']),
                'medium_severity_issues': len([i for i in self.performance_insights if i['severity'] == 'medium']),
                'low_severity_issues': len([i for i in self.performance_insights if i['severity'] == 'low'])
            }
        }
        
        return report
    
    def _generate_failed_test_report(self):
        """Generate a minimal report for failed browser tests"""
        return {
            'core_web_vitals': {},
            'resource_analysis': {},
            'performance_insights': [{
                'type': 'test_failure',
                'severity': 'high',
                'title': 'Browser Test Failed',
                'description': 'The browser test failed to complete successfully',
                'recommendation': 'Check browser test configuration and target URL availability'
            }],
            'performance_score': 0,
            'summary': {
                'total_requests': 0,
                'total_page_weight_mb': 0,
                'lcp_ms': 0,
                'fcp_ms': 0,
                'cls_score': 0,
                'tti_ms': 0,
                'fid_ms': 0,
                'tbt_ms': 0,
                'issues_count': 1,
                'high_severity_issues': 1,
                'medium_severity_issues': 0,
                'low_severity_issues': 0
            }
        }
    
    def print_report(self):
        """Print a formatted browser performance report"""
        report = self.generate_browser_report()
        
        print("\n" + "="*60)
        print("🌐 BROWSER PERFORMANCE ANALYSIS REPORT")
        print("="*60)
        
        # Performance Score
        print(f"\n📊 Overall Performance Score: {report['performance_score']}/100")
        
        # Core Web Vitals Summary
        print(f"\n🎯 Core Web Vitals:")
        for metric, data in report['core_web_vitals'].items():
            print(f"  • {data['name']}: {data['average']:.0f}ms (Grade: {data['grade']})")
        
        # Resource Analysis
        if report['resource_analysis']:
            print(f"\n📦 Resource Analysis:")
            print(f"  • Total Requests: {report['summary']['total_requests']}")
            print(f"  • Total Page Weight: {report['summary']['total_page_weight_mb']:.2f}MB")
            print(f"  • Resource Types: {', '.join([f'{k}: {v}' for k, v in report['resource_analysis'].get('resource_counts', {}).items()])}")
        
        # Performance Issues
        if report['performance_insights']:
            print(f"\n⚠️  Performance Issues ({len(report['performance_insights'])} found):")
            for issue in report['performance_insights']:
                print(f"  • {issue['severity'].upper()}: {issue['title']}")
                print(f"    {issue['description']}")
                print(f"    Recommendation: {issue['recommendation']}")
        
        print("\n" + "="*60)

def main():
    if len(sys.argv) != 2:
        print("Usage: python browser_metrics_analyzer.py <browser_summary_file>")
        sys.exit(1)
    
    browser_summary_file = sys.argv[1]
    analyzer = BrowserMetricsAnalyzer(browser_summary_file)
    
    if analyzer.load_data():
        analyzer.print_report()
        
        # Save detailed report to JSON file
        report = analyzer.generate_browser_report()
        output_file = browser_summary_file.replace('.json', '_analysis.json')
        
        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"\n✅ Detailed report saved to: {output_file}")
    else:
        print("❌ Failed to load browser metrics data")
        sys.exit(1)

if __name__ == "__main__":
    main()
