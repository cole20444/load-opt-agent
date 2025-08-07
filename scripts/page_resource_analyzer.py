#!/usr/bin/env python3
"""
Page Resource Analyzer
Identifies specific page performance issues like large images, unoptimized resources, etc.
"""

import json
import requests
import re
from urllib.parse import urljoin, urlparse
from typing import Dict, List, Any
import time

class PageResourceAnalyzer:
    def __init__(self, target_url: str):
        self.target_url = target_url
        self.resources = []
        self.issues = []
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'PageResourceAnalyzer/1.0',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept-Language': 'en-US,en;q=0.5',
        })
    
    def analyze_page_resources(self) -> Dict:
        """Analyze all resources on the page for performance issues"""
        print(f"🔍 Analyzing page resources for: {self.target_url}")
        
        try:
            # Fetch the main page
            response = self.session.get(self.target_url, timeout=30)
            response.raise_for_status()
            
            html_content = response.text
            print(f"✅ Successfully fetched page ({len(html_content)} bytes)")
            
            # Extract all resources
            self._extract_resources(html_content)
            
            # Analyze each resource
            self._analyze_resources()
            
            # Generate report
            return self._generate_report()
            
        except Exception as e:
            print(f"❌ Error analyzing page: {e}")
            return {}
    
    def _extract_resources(self, html_content: str):
        """Extract all resources from HTML content"""
        print("\n📋 Extracting page resources...")
        
        # Define resource patterns
        resource_patterns = [
            {
                'type': 'image',
                'patterns': [
                    r'<img[^>]+src=["\']([^"\']+)["\']',
                    r'<source[^>]+src=["\']([^"\']+)["\']',
                    r'background-image:\s*url\(["\']?([^"\']+)["\']?\)',
                ]
            },
            {
                'type': 'script',
                'patterns': [
                    r'<script[^>]+src=["\']([^"\']+)["\']',
                ]
            },
            {
                'type': 'stylesheet',
                'patterns': [
                    r'<link[^>]+href=["\']([^"\']+)["\'][^>]*rel=["\']stylesheet["\']',
                    r'<link[^>]+rel=["\']stylesheet["\'][^>]*href=["\']([^"\']+)["\']',
                ]
            },
            {
                'type': 'font',
                'patterns': [
                    r'<link[^>]+href=["\']([^"\']+)["\'][^>]*rel=["\']preload["\'][^>]*as=["\']font["\']',
                    r'@font-face[^}]+src:\s*url\(["\']?([^"\']+)["\']?\)',
                ]
            },
            {
                'type': 'api',
                'patterns': [
                    r'fetch\(["\']([^"\']+)["\']',
                    r'\.get\(["\']([^"\']+)["\']',
                    r'\.post\(["\']([^"\']+)["\']',
                ]
            }
        ]
        
        for resource_type in resource_patterns:
            for pattern in resource_type['patterns']:
                matches = re.findall(pattern, html_content, re.IGNORECASE)
                for match in matches:
                    if match and not match.startswith('data:'):
                        full_url = urljoin(self.target_url, match)
                        self.resources.append({
                            'type': resource_type['type'],
                            'url': full_url,
                            'original_url': match,
                            'analyzed': False
                        })
        
        # Remove duplicates
        seen_urls = set()
        unique_resources = []
        for resource in self.resources:
            if resource['url'] not in seen_urls:
                seen_urls.add(resource['url'])
                unique_resources.append(resource)
        
        self.resources = unique_resources
        print(f"📊 Found {len(self.resources)} unique resources:")
        
        # Count by type
        type_counts = {}
        for resource in self.resources:
            resource_type = resource['type']
            type_counts[resource_type] = type_counts.get(resource_type, 0) + 1
        
        for resource_type, count in type_counts.items():
            print(f"   • {resource_type}: {count}")
    
    def _analyze_resources(self):
        """Analyze each resource for performance issues"""
        print(f"\n🔬 Analyzing {len(self.resources)} resources...")
        
        for i, resource in enumerate(self.resources):
            print(f"  Analyzing {i+1}/{len(self.resources)}: {resource['url'][:60]}...")
            
            try:
                # Fetch resource with timing
                start_time = time.time()
                response = self.session.get(resource['url'], timeout=10, stream=True)
                load_time = (time.time() - start_time) * 1000  # Convert to ms
                
                # Get content length
                content_length = response.headers.get('Content-Length')
                if content_length:
                    size = int(content_length)
                else:
                    # Read content to get size
                    content = response.content
                    size = len(content)
                
                # Analyze resource
                resource.update({
                    'analyzed': True,
                    'status_code': response.status_code,
                    'size': size,
                    'load_time': load_time,
                    'headers': dict(response.headers),
                    'issues': []
                })
                
                # Check for specific issues
                self._check_resource_issues(resource, response)
                
            except Exception as e:
                resource.update({
                    'analyzed': True,
                    'error': str(e),
                    'issues': [f'Failed to load: {e}']
                })
    
    def _check_resource_issues(self, resource: Dict, response):
        """Check for specific performance issues in a resource"""
        resource_type = resource['type']
        size = resource['size']
        load_time = resource['load_time']
        headers = resource['headers']
        
        # Size-based issues
        size_thresholds = {
            'image': 500 * 1024,  # 500KB
            'script': 100 * 1024,  # 100KB
            'stylesheet': 50 * 1024,  # 50KB
            'font': 200 * 1024,  # 200KB
            'api': 50 * 1024,  # 50KB
        }
        
        threshold = size_thresholds.get(resource_type, 100 * 1024)
        if size > threshold:
            resource['issues'].append({
                'type': 'large_size',
                'severity': 'medium',
                'description': f'Large {resource_type} ({size/1024:.1f}KB)',
                'recommendation': self._get_size_recommendation(resource_type, size)
            })
        
        # Load time issues
        time_thresholds = {
            'image': 1000,  # 1s
            'script': 500,  # 500ms
            'stylesheet': 300,  # 300ms
            'font': 800,  # 800ms
            'api': 2000,  # 2s
        }
        
        threshold = time_thresholds.get(resource_type, 1000)
        if load_time > threshold:
            resource['issues'].append({
                'type': 'slow_load',
                'severity': 'medium',
                'description': f'Slow {resource_type} load ({load_time:.0f}ms)',
                'recommendation': 'Consider CDN, caching, or optimization'
            })
        
        # Compression issues
        encoding = headers.get('Content-Encoding')
        if not encoding and size > 10 * 1024:
            resource['issues'].append({
                'type': 'no_compression',
                'severity': 'low',
                'description': f'Uncompressed {resource_type} ({size/1024:.1f}KB)',
                'recommendation': 'Enable gzip/brotli compression'
            })
        
        # Caching issues
        cache_control = headers.get('Cache-Control', '')
        if not cache_control or 'no-cache' in cache_control or 'no-store' in cache_control:
            resource['issues'].append({
                'type': 'no_caching',
                'severity': 'low',
                'description': f'Uncached {resource_type}',
                'recommendation': 'Implement proper caching headers'
            })
        
        # Image-specific issues
        if resource_type == 'image':
            self._check_image_issues(resource, headers)
        
        # Script-specific issues
        if resource_type == 'script':
            self._check_script_issues(resource, headers)
        
        # API-specific issues
        if resource_type == 'api':
            self._check_api_issues(resource, headers)
    
    def _check_image_issues(self, resource: Dict, headers):
        """Check for image-specific optimization issues"""
        content_type = headers.get('Content-Type', '')
        url = resource['url'].lower()
        
        # Check for unoptimized formats
        if '.png' in url and resource['size'] > 100 * 1024:
            resource['issues'].append({
                'type': 'unoptimized_image',
                'severity': 'medium',
                'description': 'Large PNG image - consider WebP conversion',
                'recommendation': 'Convert to WebP format for better compression'
            })
        
        # Check for missing responsive images
        if 'image' in content_type and resource['size'] > 200 * 1024:
            resource['issues'].append({
                'type': 'no_responsive',
                'severity': 'low',
                'description': 'Large image without responsive variants',
                'recommendation': 'Implement responsive images with srcset'
            })
    
    def _check_script_issues(self, resource: Dict, headers):
        """Check for script-specific optimization issues"""
        url = resource['url'].lower()
        
        # Check for unminified scripts
        if '.js' in url and not any(x in url for x in ['.min.js', '.bundle.js', '.chunk.js']):
            if resource['size'] > 50 * 1024:
                resource['issues'].append({
                    'type': 'unminified_script',
                    'severity': 'medium',
                    'description': 'Large unminified JavaScript file',
                    'recommendation': 'Minify JavaScript and enable tree-shaking'
                })
        
        # Check for render-blocking scripts
        if not any(x in url for x in ['async', 'defer', 'module']):
            resource['issues'].append({
                'type': 'render_blocking',
                'severity': 'medium',
                'description': 'Render-blocking script',
                'recommendation': 'Add async/defer attributes or use ES modules'
            })
    
    def _check_api_issues(self, resource: Dict, headers):
        """Check for API-specific issues"""
        # Check for missing API versioning
        if '/api/' in resource['url'] and not re.search(r'/v\d+/', resource['url']):
            resource['issues'].append({
                'type': 'no_versioning',
                'severity': 'low',
                'description': 'API endpoint without versioning',
                'recommendation': 'Implement API versioning for stability'
            })
        
        # Check for large API responses
        if resource['size'] > 100 * 1024:
            resource['issues'].append({
                'type': 'large_api_response',
                'severity': 'medium',
                'description': 'Large API response',
                'recommendation': 'Implement pagination or selective field fetching'
            })
    
    def _get_size_recommendation(self, resource_type: str, size: int) -> str:
        """Get specific recommendations based on resource type and size"""
        recommendations = {
            'image': 'Optimize images, use WebP format, implement lazy loading',
            'script': 'Minify JavaScript, enable tree-shaking, use code splitting',
            'stylesheet': 'Minify CSS, remove unused styles, use critical CSS',
            'font': 'Use font-display: swap, subset fonts, consider system fonts',
            'api': 'Implement pagination, selective field fetching, or GraphQL'
        }
        return recommendations.get(resource_type, 'Consider optimization or compression')
    
    def _generate_report(self) -> Dict:
        """Generate comprehensive resource analysis report"""
        print(f"\n📊 Generating resource analysis report...")
        
        # Calculate statistics
        total_size = sum(r['size'] for r in self.resources if r.get('analyzed') and 'size' in r)
        total_load_time = sum(r['load_time'] for r in self.resources if r.get('analyzed') and 'load_time' in r)
        
        # Count issues by severity
        all_issues = []
        for resource in self.resources:
            if resource.get('analyzed') and 'issues' in resource:
                all_issues.extend(resource['issues'])
        
        high_issues = [i for i in all_issues if i.get('severity') == 'high']
        medium_issues = [i for i in all_issues if i.get('severity') == 'medium']
        low_issues = [i for i in all_issues if i.get('severity') == 'low']
        
        # Calculate performance score
        total_issues = len(all_issues)
        score = max(0, 100 - (len(high_issues) * 15) - (len(medium_issues) * 8) - (len(low_issues) * 3))
        
        report = {
            'summary': {
                'target_url': self.target_url,
                'total_resources': len(self.resources),
                'total_size': total_size,
                'total_load_time': total_load_time,
                'total_issues': total_issues,
                'high_priority': len(high_issues),
                'medium_priority': len(medium_issues),
                'low_priority': len(low_issues),
                'performance_score': score
            },
            'resources': self.resources,
            'issues': {
                'high': high_issues,
                'medium': medium_issues,
                'low': low_issues
            },
            'recommendations': self._generate_resource_recommendations(all_issues)
        }
        
        return report
    
    def _generate_resource_recommendations(self, issues: List[Dict]) -> List[Dict]:
        """Generate prioritized recommendations based on resource issues"""
        recommendations = []
        
        # Group issues by type
        issue_types = {}
        for issue in issues:
            issue_type = issue.get('type', 'unknown')
            if issue_type not in issue_types:
                issue_types[issue_type] = []
            issue_types[issue_type].append(issue)
        
        # Generate recommendations for each issue type
        if 'large_size' in issue_types:
            recommendations.append({
                'priority': 'medium',
                'category': 'Resource Size',
                'title': 'Optimize Large Resources',
                'description': f"{len(issue_types['large_size'])} resources are larger than optimal",
                'actions': [
                    'Compress images using WebP format',
                    'Minify CSS and JavaScript files',
                    'Implement lazy loading for images',
                    'Use CDN for static assets',
                    'Consider code splitting for large scripts'
                ]
            })
        
        if 'no_compression' in issue_types:
            recommendations.append({
                'priority': 'low',
                'category': 'Compression',
                'title': 'Enable Compression',
                'description': f"{len(issue_types['no_compression'])} resources lack compression",
                'actions': [
                    'Enable gzip compression on server',
                    'Consider brotli compression for better ratios',
                    'Configure compression for all text-based resources'
                ]
            })
        
        if 'no_caching' in issue_types:
            recommendations.append({
                'priority': 'low',
                'category': 'Caching',
                'title': 'Implement Caching',
                'description': f"{len(issue_types['no_caching'])} resources lack caching",
                'actions': [
                    'Set appropriate Cache-Control headers',
                    'Use ETags for cache validation',
                    'Implement cache busting for versioned resources'
                ]
            })
        
        return recommendations
    
    def print_report(self, report: Dict):
        """Print the resource analysis report"""
        print("\n" + "="*80)
        print("🎨 PAGE RESOURCE ANALYSIS REPORT")
        print("="*80)
        
        summary = report.get('summary', {})
        print(f"\n🎯 PERFORMANCE SCORE: {summary.get('performance_score', 0)}/100")
        print(f"📊 RESOURCES ANALYZED: {summary.get('total_resources', 0)}")
        print(f"📦 TOTAL SIZE: {summary.get('total_size', 0)/1024/1024:.1f}MB")
        print(f"⏱️  TOTAL LOAD TIME: {summary.get('total_load_time', 0):.0f}ms")
        print(f"📈 ISSUES FOUND: {summary.get('total_issues', 0)}")
        print(f"   🔴 High Priority: {summary.get('high_priority', 0)}")
        print(f"   🟡 Medium Priority: {summary.get('medium_priority', 0)}")
        print(f"   🟢 Low Priority: {summary.get('low_priority', 0)}")
        
        # Show top issues by type
        issues = report.get('issues', {})
        if issues['high'] or issues['medium']:
            print(f"\n🔴 TOP ISSUES:")
            all_issues = issues['high'] + issues['medium']
            for issue in all_issues[:5]:  # Show top 5
                print(f"   • {issue.get('description', 'Unknown issue')}")
        
        # Show recommendations
        recommendations = report.get('recommendations', [])
        if recommendations:
            print(f"\n💡 RECOMMENDATIONS:")
            for rec in recommendations:
                priority_icon = "🔴" if rec['priority'] == 'high' else "🟡" if rec['priority'] == 'medium' else "🟢"
                print(f"\n   {priority_icon} {rec['title']}")
                print(f"   {rec['description']}")
                print(f"   Actions:")
                for action in rec['actions']:
                    print(f"     • {action}")

def main():
    """Main function to run page resource analysis"""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python page_resource_analyzer.py <target_url>")
        print("Example: python page_resource_analyzer.py https://example.com")
        return
    
    target_url = sys.argv[1]
    
    analyzer = PageResourceAnalyzer(target_url)
    report = analyzer.analyze_page_resources()
    
    if report:
        analyzer.print_report(report)
        
        # Save detailed report
        with open("output/page_resource_analysis.json", 'w') as f:
            json.dump(report, f, indent=2)
        print(f"\n💾 Detailed report saved to: output/page_resource_analysis.json")
    else:
        print("❌ Failed to generate resource analysis report")

if __name__ == "__main__":
    main() 