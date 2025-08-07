#!/usr/bin/env python3
"""
Enhanced Performance Analyzer
Identifies specific page performance issues from k6 load test data
"""

import json
import sys
import os
from collections import defaultdict
from typing import Dict, List, Any
import re

class EnhancedPerformanceAnalyzer:
    def __init__(self, summary_file: str, test_report_file: str):
        self.summary_file = summary_file
        self.test_report_file = test_report_file
        self.metrics_data = []
        self.issues = []
        
    def load_data(self):
        """Load k6 metrics data"""
        try:
            with open(self.summary_file, 'r') as f:
                for line in f:
                    try:
                        data = json.loads(line.strip())
                        if data.get('type') == 'Point':
                            self.metrics_data.append(data)
                    except json.JSONDecodeError:
                        continue
            print(f"✅ Loaded {len(self.metrics_data)} data points from k6 summary")
        except FileNotFoundError:
            print(f"❌ Summary file not found: {self.summary_file}")
            return False
        return True
    
    def analyze_performance_issues(self):
        """Analyze performance issues from k6 data"""
        print("\n🔍 ANALYZING PERFORMANCE ISSUES...")
        
        # Group metrics by type
        metrics_by_name = defaultdict(list)
        for data in self.metrics_data:
            metric_name = data.get('metric', 'unknown')
            metrics_by_name[metric_name].append(data)
        
        # Analyze HTTP timing breakdown
        self._analyze_http_timing(metrics_by_name)
        
        # Analyze data transfer
        self._analyze_data_transfer(metrics_by_name)
        
        # Analyze resource loading
        self._analyze_resource_loading(metrics_by_name)
        
        # Analyze load distribution
        self._analyze_load_distribution(metrics_by_name)
        
        # Analyze error patterns
        self._analyze_error_patterns(metrics_by_name)
        
        return self.issues
    
    def _analyze_http_timing(self, metrics_by_name: Dict):
        """Analyze HTTP timing breakdown to identify bottlenecks"""
        print("\n📊 HTTP Timing Analysis:")
        
        timing_metrics = {
            'http_req_blocked': 'DNS/Connection Pool',
            'http_req_connecting': 'TCP Connection',
            'http_req_tls_handshaking': 'TLS Handshake',
            'http_req_sending': 'Request Sending',
            'http_req_waiting': 'Server Processing',
            'http_req_receiving': 'Response Receiving'
        }
        
        for metric, description in timing_metrics.items():
            if metric in metrics_by_name:
                data_points = metrics_by_name[metric]
                values = [dp.get('data', {}).get('value', 0) for dp in data_points]
                
                if values:
                    avg_time = sum(values) / len(values)
                    max_time = max(values)
                    p95_time = sorted(values)[int(len(values) * 0.95)]
                    
                    print(f"  {description}:")
                    print(f"    Average: {avg_time:.1f}ms")
                    print(f"    Max: {max_time:.1f}ms")
                    print(f"    95th percentile: {p95_time:.1f}ms")
                    
                    # Identify issues
                    if avg_time > 500:
                        self.issues.append({
                            'type': 'timing',
                            'severity': 'high' if avg_time > 1000 else 'medium',
                            'category': description,
                            'issue': f'Slow {description.lower()} (avg: {avg_time:.1f}ms)',
                            'recommendation': self._get_timing_recommendation(metric, avg_time)
                        })
    
    def _analyze_data_transfer(self, metrics_by_name: Dict):
        """Analyze data transfer patterns"""
        print("\n📦 Data Transfer Analysis:")
        
        if 'data_sent' in metrics_by_name and 'data_received' in metrics_by_name:
            sent_data = [dp.get('data', {}).get('value', 0) for dp in metrics_by_name['data_sent']]
            received_data = [dp.get('data', {}).get('value', 0) for dp in metrics_by_name['data_received']]
            
            if sent_data and received_data:
                avg_sent = sum(sent_data) / len(sent_data)
                avg_received = sum(received_data) / len(received_data)
                
                print(f"  Average data sent: {avg_sent:.1f} bytes")
                print(f"  Average data received: {avg_received:.1f} bytes ({avg_received/1024:.1f}KB)")
                
                # Check for large payloads
                if avg_received > 100 * 1024:  # 100KB
                    self.issues.append({
                        'type': 'payload',
                        'severity': 'medium',
                        'category': 'Data Transfer',
                        'issue': f'Large response payloads (avg: {avg_received/1024:.1f}KB)',
                        'recommendation': 'Consider implementing compression, lazy loading, or pagination'
                    })
    
    def _analyze_resource_loading(self, metrics_by_name: Dict):
        """Analyze resource loading patterns"""
        print("\n🎨 Resource Loading Analysis:")
        
        # Look for custom resource metrics
        resource_metrics = ['resource_load_time', 'resource_size', 'resource_type']
        
        for metric in resource_metrics:
            if metric in metrics_by_name:
                data_points = metrics_by_name[metric]
                print(f"  {metric}: {len(data_points)} data points")
                
                if metric == 'resource_size':
                    values = [dp.get('data', {}).get('value', 0) for dp in data_points]
                    if values:
                        avg_size = sum(values) / len(values)
                        max_size = max(values)
                        print(f"    Average size: {avg_size/1024:.1f}KB")
                        print(f"    Max size: {max_size/1024:.1f}KB")
                        
                        # Check for large resources
                        if avg_size > 200 * 1024:  # 200KB
                            self.issues.append({
                                'type': 'resource',
                                'severity': 'medium',
                                'category': 'Resource Size',
                                'issue': f'Large resources detected (avg: {avg_size/1024:.1f}KB)',
                                'recommendation': 'Optimize images, minify CSS/JS, use WebP format'
                            })
    
    def _analyze_load_distribution(self, metrics_by_name: Dict):
        """Analyze virtual user distribution"""
        print("\n👥 Load Distribution Analysis:")
        
        if 'vus' in metrics_by_name:
            vus_data = [dp.get('data', {}).get('value', 0) for dp in metrics_by_name['vus']]
            if vus_data:
                avg_vus = sum(vus_data) / len(vus_data)
                max_vus = max(vus_data)
                print(f"  Average VUs: {avg_vus:.1f}")
                print(f"  Max VUs: {max_vus}")
                
                # Check for load distribution issues
                if max_vus > 0 and avg_vus / max_vus < 0.5:
                    self.issues.append({
                        'type': 'load',
                        'severity': 'low',
                        'category': 'Load Distribution',
                        'issue': 'Uneven load distribution detected',
                        'recommendation': 'Consider adjusting ramp-up/down patterns'
                    })
    
    def _analyze_error_patterns(self, metrics_by_name: Dict):
        """Analyze error patterns"""
        print("\n❌ Error Pattern Analysis:")
        
        if 'http_req_failed' in metrics_by_name:
            failed_data = [dp.get('data', {}).get('value', 0) for dp in metrics_by_name['http_req_failed']]
            if failed_data:
                error_rate = sum(failed_data) / len(failed_data)
                print(f"  Error rate: {error_rate:.2%}")
                
                if error_rate > 0.05:  # 5%
                    self.issues.append({
                        'type': 'error',
                        'severity': 'high',
                        'category': 'Error Rate',
                        'issue': f'High error rate detected ({error_rate:.2%})',
                        'recommendation': 'Investigate server errors, network issues, or application bugs'
                    })
    
    def _get_timing_recommendation(self, metric: str, avg_time: float) -> str:
        """Get specific recommendations based on timing metrics"""
        recommendations = {
            'http_req_blocked': 'Implement DNS caching, connection pooling, or CDN',
            'http_req_connecting': 'Use connection pooling, reduce DNS lookups',
            'http_req_tls_handshaking': 'Enable TLS session resumption, use HTTP/2',
            'http_req_waiting': 'Optimize server processing, database queries, or caching',
            'http_req_receiving': 'Implement compression, reduce payload size',
            'http_req_sending': 'Optimize request size, use efficient protocols'
        }
        return recommendations.get(metric, 'Investigate network and server configuration')
    
    def generate_page_analysis_report(self) -> Dict:
        """Generate a comprehensive page performance analysis report"""
        if not self.load_data():
            return {}
        
        issues = self.analyze_performance_issues()
        
        # Categorize issues by severity
        high_issues = [i for i in issues if i['severity'] == 'high']
        medium_issues = [i for i in issues if i['severity'] == 'medium']
        low_issues = [i for i in issues if i['severity'] == 'low']
        
        # Calculate performance score
        total_issues = len(issues)
        score = max(0, 100 - (len(high_issues) * 20) - (len(medium_issues) * 10) - (len(low_issues) * 5))
        
        report = {
            'summary': {
                'total_issues': total_issues,
                'high_priority': len(high_issues),
                'medium_priority': len(medium_issues),
                'low_priority': len(low_issues),
                'performance_score': score
            },
            'issues': {
                'high': high_issues,
                'medium': medium_issues,
                'low': low_issues
            },
            'recommendations': self._generate_prioritized_recommendations(issues)
        }
        
        return report
    
    def _generate_prioritized_recommendations(self, issues: List[Dict]) -> List[Dict]:
        """Generate prioritized recommendations based on issues"""
        recommendations = []
        
        # Group by category
        categories = defaultdict(list)
        for issue in issues:
            categories[issue['category']].append(issue)
        
        # Generate category-specific recommendations
        for category, category_issues in categories.items():
            if category == 'Server Processing':
                recommendations.append({
                    'priority': 'high',
                    'category': category,
                    'title': 'Optimize Server Processing',
                    'description': 'Server processing time is the biggest bottleneck',
                    'actions': [
                        'Implement server-side caching (Redis, Memcached)',
                        'Optimize database queries and add indexes',
                        'Consider database connection pooling',
                        'Implement API response caching',
                        'Use CDN for static assets'
                    ]
                })
            elif category == 'TLS Handshake':
                recommendations.append({
                    'priority': 'medium',
                    'category': category,
                    'title': 'Optimize TLS Configuration',
                    'description': 'TLS handshake time can be reduced',
                    'actions': [
                        'Enable TLS session resumption',
                        'Use HTTP/2 for multiplexing',
                        'Optimize certificate chain',
                        'Consider using a CDN with edge TLS termination'
                    ]
                })
            elif category == 'Data Transfer':
                recommendations.append({
                    'priority': 'medium',
                    'category': category,
                    'title': 'Optimize Payload Sizes',
                    'description': 'Response payloads are larger than optimal',
                    'actions': [
                        'Enable gzip/brotli compression',
                        'Implement lazy loading for images',
                        'Use pagination for large datasets',
                        'Optimize API response structure',
                        'Consider using GraphQL for selective data fetching'
                    ]
                })
        
        return recommendations
    
    def print_report(self, report: Dict):
        """Print the analysis report"""
        print("\n" + "="*80)
        print("📊 ENHANCED PAGE PERFORMANCE ANALYSIS REPORT")
        print("="*80)
        
        summary = report.get('summary', {})
        print(f"\n🎯 PERFORMANCE SCORE: {summary.get('performance_score', 0)}/100")
        print(f"📈 ISSUES FOUND: {summary.get('total_issues', 0)}")
        print(f"   🔴 High Priority: {summary.get('high_priority', 0)}")
        print(f"   🟡 Medium Priority: {summary.get('medium_priority', 0)}")
        print(f"   🟢 Low Priority: {summary.get('low_priority', 0)}")
        
        # Show high priority issues
        high_issues = report.get('issues', {}).get('high', [])
        if high_issues:
            print(f"\n🔴 HIGH PRIORITY ISSUES:")
            for issue in high_issues:
                print(f"   • {issue['issue']}")
                print(f"     Recommendation: {issue['recommendation']}")
        
        # Show recommendations
        recommendations = report.get('recommendations', [])
        if recommendations:
            print(f"\n💡 PRIORITIZED RECOMMENDATIONS:")
            for rec in recommendations:
                priority_icon = "🔴" if rec['priority'] == 'high' else "🟡" if rec['priority'] == 'medium' else "🟢"
                print(f"\n   {priority_icon} {rec['title']}")
                print(f"   Category: {rec['category']}")
                print(f"   Description: {rec['description']}")
                print(f"   Actions:")
                for action in rec['actions']:
                    print(f"     • {action}")

def main():
    """Main function to run enhanced performance analysis"""
    summary_file = "output/summary.json"
    test_report_file = "output/test_report.json"
    
    if not os.path.exists(summary_file):
        print(f"❌ Summary file not found: {summary_file}")
        print("Please run a load test first using: python run_test.py")
        return
    
    analyzer = EnhancedPerformanceAnalyzer(summary_file, test_report_file)
    report = analyzer.generate_page_analysis_report()
    
    if report:
        analyzer.print_report(report)
        
        # Save detailed report
        with open("output/enhanced_analysis_report.json", 'w') as f:
            json.dump(report, f, indent=2)
        print(f"\n💾 Detailed report saved to: output/enhanced_analysis_report.json")
    else:
        print("❌ Failed to generate analysis report")

if __name__ == "__main__":
    main() 