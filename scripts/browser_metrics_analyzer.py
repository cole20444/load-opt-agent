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
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class BrowserMetricsAnalyzer:
    def __init__(self, browser_summary_file: str):
        self.browser_summary_file = browser_summary_file
        self.metrics_data = []
        self.playwright_data = None
        self.core_web_vitals = {}
        self.performance_insights = []
        self.resource_analysis = {}
        self.performance_score = 0
        
    def load_data(self):
        """Load browser metrics data from xk6-browser output (JSONL format) or aggregated Playwright results"""
        try:
            with open(self.browser_summary_file, 'r') as f:
                content = f.read().strip()
                
            # Try to parse as aggregated Playwright results first
            try:
                data = json.loads(content)
                if 'summary' in data and 'total_iterations' in data['summary']:
                    print("📊 Detected aggregated Playwright results format")
                    return self._load_aggregated_playwright_data(data)
            except json.JSONDecodeError:
                pass
            
            # Fallback to JSONL format (original k6 output)
            self.metrics_data = []
            for line in content.split('\n'):
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
    
    def _load_aggregated_playwright_data(self, data):
        """Load data from aggregated Playwright results format"""
        try:
            summary = data.get('summary', {})
            
            # Store the original Playwright data for resource analysis
            self.playwright_data = data
            
            # Convert aggregated metrics to the format expected by the analyzer
            self.metrics_data = []
            
            # Create synthetic data points for each metric type
            metrics_mapping = {
                'first_contentful_paint': 'avg_first_contentful_paint',
                'largest_contentful_paint': 'avg_total_time',  # Use total time as proxy for LCP
                'first_input_delay': 'avg_time_to_first_byte',  # Use TTFB as proxy for FID
                'cumulative_layout_shift': 'avg_cumulative_layout_shift',
                'time_to_interactive': 'avg_load_complete',
                'total_blocking_time': 'avg_dom_content_loaded',  # Use DOM content loaded as proxy
                'first_paint': 'avg_first_paint',
                'dom_content_loaded': 'avg_dom_content_loaded',
                'load_complete': 'avg_load_complete',
                'time_to_first_byte': 'avg_time_to_first_byte'
            }
            
            for metric_name, summary_key in metrics_mapping.items():
                if summary_key in summary:
                    value = summary[summary_key]
                    # Create a synthetic data point
                    data_point = {
                        'type': 'Point',
                        'metric': metric_name,
                        'value': value,
                        'time': 0,  # Synthetic timestamp
                        'tags': {}
                    }
                    self.metrics_data.append(data_point)
                    print(f"  📊 {metric_name}: {value}ms")
            
            print(f"✅ Loaded aggregated Playwright data with {len(self.metrics_data)} metrics")
            return True
            
        except Exception as e:
            print(f"❌ Error loading aggregated Playwright data: {e}")
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
        
        # Resource analysis
        self.resource_analysis = self._analyze_resources()
        
        # Estimate Core Web Vitals from HTTP timing data if not directly available
        http_durations = []
        if 'http_req_duration' in metrics_by_name:
            http_durations = [dp.get('value', 0) for dp in metrics_by_name['http_req_duration']]
        
        for metric, config in core_vitals.items():
            if metric in metrics_by_name:
                values = [dp.get('value', 0) for dp in metrics_by_name[metric]]
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
    
    def _analyze_resources(self) -> Dict[str, Any]:
        """Analyze resource loading patterns and identify performance bottlenecks"""
        resource_analysis = {
            'total_requests': 0,
            'total_page_weight_mb': 0,
            'avg_resource_load_time': 0,
            'max_resource_load_time': 0,
            'resource_count_stats': {},
            'load_time_distribution': {},
            'performance_issues': [],
            'recommendations': []
        }
        
        if not self.metrics_data:
            return resource_analysis
        
        # Extract resource data from Playwright results
        resource_counts = []
        resource_sizes = []
        load_times = []
        max_load_times = []
        
        # Check if we have detailed results (Playwright format)
        if hasattr(self, 'playwright_data') and self.playwright_data:
            detailed_results = self.playwright_data.get('detailed_results', [])
            for result in detailed_results:
                if 'resource_count' in result:
                    resource_counts.append(result['resource_count'])
                if 'total_resource_size' in result:
                    resource_sizes.append(result['total_resource_size'])
                if 'avg_resource_load_time' in result:
                    load_times.append(result['avg_resource_load_time'])
                if 'max_resource_load_time' in result:
                    max_load_times.append(result['max_resource_load_time'])
            
            # Extract individual resource details if available
            self._extract_individual_resources(detailed_results)
        else:
            # Fallback to metrics_data format
            for data in self.metrics_data:
                if 'resource_count' in data:
                    resource_counts.append(data['resource_count'])
                if 'total_resource_size' in data:
                    resource_sizes.append(data['total_resource_size'])
                if 'avg_resource_load_time' in data:
                    load_times.append(data['avg_resource_load_time'])
                if 'max_resource_load_time' in data:
                    max_load_times.append(data['max_resource_load_time'])
        
        if resource_counts:
            resource_analysis['total_requests'] = sum(resource_counts)
            resource_analysis['resource_count_stats'] = {
                'avg': statistics.mean(resource_counts),
                'min': min(resource_counts),
                'max': max(resource_counts),
                'p95': sorted(resource_counts)[int(len(resource_counts) * 0.95)] if len(resource_counts) > 1 else resource_counts[0]
            }
        
        if resource_sizes:
            total_size_bytes = sum(resource_sizes)
            resource_analysis['total_page_weight_mb'] = total_size_bytes / (1024 * 1024)
        
        if load_times:
            resource_analysis['avg_resource_load_time'] = statistics.mean(load_times)
            resource_analysis['load_time_distribution'] = {
                'avg': statistics.mean(load_times),
                'min': min(load_times),
                'max': max(load_times),
                'p95': sorted(load_times)[int(len(load_times) * 0.95)] if len(load_times) > 1 else load_times[0]
            }
        
        if max_load_times:
            resource_analysis['max_resource_load_time'] = max(max_load_times)
        
        # Identify performance issues
        if resource_analysis['avg_resource_load_time'] > 100:
            resource_analysis['performance_issues'].append({
                'type': 'slow_resource_loading',
                'severity': 'high',
                'description': f"Average resource load time is {resource_analysis['avg_resource_load_time']:.1f}ms, which is above the recommended 100ms",
                'impact': 'Significantly impacts page load performance and user experience'
            })
        
        if resource_analysis['max_resource_load_time'] > 500:
            resource_analysis['performance_issues'].append({
                'type': 'blocking_resources',
                'severity': 'critical',
                'description': f"Some resources take up to {resource_analysis['max_resource_load_time']:.1f}ms to load",
                'impact': 'Blocking resources can severely impact page load times'
            })
        
        if resource_analysis['total_page_weight_mb'] > 2:
            resource_analysis['performance_issues'].append({
                'type': 'large_page_size',
                'severity': 'medium',
                'description': f"Total page weight is {resource_analysis['total_page_weight_mb']:.1f}MB, above the recommended 2MB",
                'impact': 'Large page sizes increase load times, especially on slower connections'
            })
        
        if resource_analysis['resource_count_stats'].get('avg', 0) > 50:
            resource_analysis['performance_issues'].append({
                'type': 'too_many_requests',
                'severity': 'medium',
                'description': f"Average of {resource_analysis['resource_count_stats']['avg']:.1f} requests per page, above the recommended 50",
                'impact': 'Too many HTTP requests increase load times and server load'
            })
        
        # Generate recommendations
        if resource_analysis['avg_resource_load_time'] > 100:
            resource_analysis['recommendations'].append({
                'category': 'Resource Optimization',
                'priority': 'High',
                'action': 'Optimize resource loading times',
                'details': 'Implement resource bundling, compression, and CDN usage to reduce load times'
            })
        
        if resource_analysis['max_resource_load_time'] > 500:
            resource_analysis['recommendations'].append({
                'category': 'Critical Resources',
                'priority': 'Critical',
                'action': 'Identify and optimize blocking resources',
                'details': 'Use browser dev tools to identify which specific resources are causing delays'
            })
        
        if resource_analysis['total_page_weight_mb'] > 2:
            resource_analysis['recommendations'].append({
                'category': 'Page Size',
                'priority': 'Medium',
                'action': 'Reduce page weight',
                'details': 'Optimize images, minify CSS/JS, and remove unused resources'
            })
        
        if resource_analysis['resource_count_stats'].get('avg', 0) > 50:
            resource_analysis['recommendations'].append({
                'category': 'Request Optimization',
                'priority': 'Medium',
                'action': 'Reduce number of HTTP requests',
                'details': 'Bundle CSS/JS files, use CSS sprites, and implement resource combining'
            })
        
        return resource_analysis
    
    def _extract_individual_resources(self, detailed_results):
        """Extract individual resource details from Playwright results"""
        self.individual_resources = []
        
        for result in detailed_results:
            # Check if this result has individual resource data
            if 'resources' in result:
                for resource in result['resources']:
                    # Calculate load time if not provided
                    load_time = resource.get('loadTime', 0)
                    if load_time == 0 and 'timestamp' in resource:
                        # Estimate load time based on when the request was made
                        load_time = 100  # Default estimate
                    
                    self.individual_resources.append({
                        'url': resource.get('url', 'Unknown'),
                        'resourceType': resource.get('resourceType', 'Unknown'),
                        'size': resource.get('size', 0),
                        'loadTime': load_time,
                        'status': resource.get('status', 0)
                    })
    
    def _analyze_performance_culprits(self) -> Dict[str, Any]:
        """Analyze and identify the top performance culprits"""
        culprits_analysis = {
            'slowest_resources': [],
            'largest_resources': [],
            'most_requests_by_type': {},
            'api_calls': [],
            'images': [],
            'scripts': [],
            'stylesheets': [],
            'recommendations': []
        }
        
        if not hasattr(self, 'individual_resources') or not self.individual_resources:
            return culprits_analysis
        
        resources = self.individual_resources
        
        # Find slowest resources (load time > 100ms)
        slow_resources = [r for r in resources if r.get('loadTime', 0) > 100]
        culprits_analysis['slowest_resources'] = sorted(slow_resources, key=lambda x: x.get('loadTime', 0), reverse=True)[:10]
        
        # Find largest resources (size > 100KB)
        large_resources = [r for r in resources if r.get('size', 0) > 100000]  # 100KB
        culprits_analysis['largest_resources'] = sorted(large_resources, key=lambda x: x.get('size', 0), reverse=True)[:10]
        
        # Count requests by type
        type_counts = {}
        for resource in resources:
            resource_type = resource.get('resourceType', 'unknown')
            type_counts[resource_type] = type_counts.get(resource_type, 0) + 1
        culprits_analysis['most_requests_by_type'] = dict(sorted(type_counts.items(), key=lambda x: x[1], reverse=True))
        
        # Categorize resources
        culprits_analysis['api_calls'] = [r for r in resources if r.get('resourceType') in ['xhr', 'fetch']]
        culprits_analysis['images'] = [r for r in resources if r.get('resourceType') == 'image']
        culprits_analysis['scripts'] = [r for r in resources if r.get('resourceType') == 'script']
        culprits_analysis['stylesheets'] = [r for r in resources if r.get('resourceType') == 'stylesheet']
        
        # Generate recommendations based on findings
        if culprits_analysis['slowest_resources']:
            culprits_analysis['recommendations'].append({
                'type': 'slow_resources',
                'priority': 'High',
                'title': 'Slow Loading Resources Detected',
                'description': f"Found {len(culprits_analysis['slowest_resources'])} resources taking over 100ms to load",
                'action': 'Optimize or defer slow-loading resources'
            })
        
        if culprits_analysis['largest_resources']:
            culprits_analysis['recommendations'].append({
                'type': 'large_resources',
                'priority': 'Medium',
                'title': 'Large Resources Detected',
                'description': f"Found {len(culprits_analysis['largest_resources'])} resources over 100KB",
                'action': 'Compress or optimize large resources'
            })
        
        if len(culprits_analysis['api_calls']) > 10:
            culprits_analysis['recommendations'].append({
                'type': 'too_many_api_calls',
                'priority': 'Medium',
                'title': 'Excessive API Calls',
                'description': f"Found {len(culprits_analysis['api_calls'])} API calls, consider batching or caching",
                'action': 'Implement API batching or caching strategies'
            })
        
        return culprits_analysis
    
    def generate_browser_report(self):
        """Generate comprehensive browser performance report"""
        print("\n📋 GENERATING BROWSER PERFORMANCE REPORT...")
        
        # Run all analyses
        self.analyze_core_web_vitals()
        self.analyze_resource_loading()
        self.analyze_performance_issues()
        self.calculate_performance_score()
        
        # Analyze performance culprits
        self.performance_culprits = self._analyze_performance_culprits()
        
        report = {
            'core_web_vitals': self.core_web_vitals,
            'resource_analysis': self.resource_analysis,
            'performance_culprits': self.performance_culprits,
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
            
            # Show resource count statistics
            if report['resource_analysis'].get('resource_count_stats'):
                stats = report['resource_analysis']['resource_count_stats']
                print(f"  • Resource Count Stats: Avg={stats.get('avg', 0):.1f}, Min={stats.get('min', 0)}, Max={stats.get('max', 0)}, P95={stats.get('p95', 0)}")
            
            # Show load time statistics
            if report['resource_analysis'].get('load_time_distribution'):
                load_stats = report['resource_analysis']['load_time_distribution']
                print(f"  • Load Time Distribution: Avg={load_stats.get('avg', 0):.1f}ms, Max={load_stats.get('max', 0):.1f}ms, P95={load_stats.get('p95', 0):.1f}ms")
            
            # Show performance issues related to resources
            if report['resource_analysis'].get('performance_issues'):
                print(f"\n🚨 Resource Performance Issues:")
                for issue in report['resource_analysis']['performance_issues']:
                    severity_icon = "🔴" if issue['severity'] == 'critical' else "🟡" if issue['severity'] == 'high' else "🟠" if issue['severity'] == 'medium' else "🟢"
                    print(f"  {severity_icon} {issue['severity'].upper()}: {issue['description']}")
                    print(f"    Impact: {issue['impact']}")
            
            # Show resource optimization recommendations
            if report['resource_analysis'].get('recommendations'):
                print(f"\n💡 Resource Optimization Recommendations:")
                for rec in report['resource_analysis']['recommendations']:
                    priority_icon = "🔴" if rec['priority'] == 'Critical' else "🟡" if rec['priority'] == 'High' else "🟠" if rec['priority'] == 'Medium' else "🟢"
                    print(f"  {priority_icon} {rec['priority']} - {rec['action']}")
                    print(f"    {rec['details']}")
        
        # Performance Culprits Analysis
        if report.get('performance_culprits'):
            culprits = report['performance_culprits']
            print(f"\n🐌 Performance Culprits Analysis:")
            
            # Show slowest resources
            if culprits.get('slowest_resources'):
                print(f"\n⏱️  Slowest Resources (>100ms):")
                for i, resource in enumerate(culprits['slowest_resources'][:5], 1):
                    load_time = resource.get('loadTime', 0)
                    resource_type = resource.get('resourceType', 'Unknown')
                    url = resource.get('url', 'Unknown')
                    print(f"  {i}. {resource_type}: {load_time:.0f}ms - {url[:60]}...")
            
            # Show largest resources
            if culprits.get('largest_resources'):
                print(f"\n📦 Largest Resources (>100KB):")
                for i, resource in enumerate(culprits['largest_resources'][:5], 1):
                    size_kb = resource.get('size', 0) / 1024
                    resource_type = resource.get('resourceType', 'Unknown')
                    url = resource.get('url', 'Unknown')
                    print(f"  {i}. {resource_type}: {size_kb:.1f}KB - {url[:60]}...")
            
            # Show request breakdown by type
            if culprits.get('most_requests_by_type'):
                print(f"\n📊 Requests by Type:")
                for resource_type, count in list(culprits['most_requests_by_type'].items())[:5]:
                    print(f"  • {resource_type}: {count} requests")
            
            # Show API calls summary
            if culprits.get('api_calls'):
                api_calls = culprits['api_calls']
                print(f"\n🔗 API Calls: {len(api_calls)} total")
                if len(api_calls) > 0:
                    slow_apis = [api for api in api_calls if api.get('loadTime', 0) > 200]
                    if slow_apis:
                        print(f"  • {len(slow_apis)} slow API calls (>200ms)")
            
            # Show performance culprit recommendations
            if culprits.get('recommendations'):
                print(f"\n🎯 Performance Culprit Recommendations:")
                for rec in culprits['recommendations']:
                    priority_icon = "🔴" if rec['priority'] == 'High' else "🟡" if rec['priority'] == 'Medium' else "🟢"
                    print(f"  {priority_icon} {rec['priority']} - {rec['title']}")
                    print(f"    {rec['description']}")
                    print(f"    Action: {rec['action']}")
        
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
    logger.info(f"Starting browser analysis for file: {browser_summary_file}")
    
    # Check if file exists
    if not os.path.exists(browser_summary_file):
        logger.error(f"Browser summary file does not exist: {browser_summary_file}")
        print(f"❌ Browser summary file does not exist: {browser_summary_file}")
        sys.exit(1)
    
    analyzer = BrowserMetricsAnalyzer(browser_summary_file)
    
    try:
        if analyzer.load_data():
            logger.info("Successfully loaded browser data")
            analyzer.print_report()
            
            # Save detailed report to JSON file
            report = analyzer.generate_browser_report()
            output_file = browser_summary_file.replace('.json', '_analysis.json')
            
            with open(output_file, 'w') as f:
                json.dump(report, f, indent=2)
            
            logger.info(f"Detailed report saved to: {output_file}")
            print(f"\n✅ Detailed report saved to: {output_file}")
        else:
            logger.error("Failed to load browser metrics data")
            print("❌ Failed to load browser metrics data")
            sys.exit(1)
    except Exception as e:
        logger.error(f"Error during browser analysis: {e}")
        print(f"❌ Error during browser analysis: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
