#!/usr/bin/env python3
"""
Enhanced Playwright-based browser test with advanced performance metrics
Captures comprehensive Core Web Vitals, memory usage, and rendering performance
"""

import asyncio
import json
import time
from datetime import datetime
from playwright.async_api import async_playwright
import os

class AdvancedPlaywrightBrowserTest:
    def __init__(self, target_url, duration_minutes=2, vus=5):
        self.target_url = target_url
        self.duration_seconds = duration_minutes * 60
        self.vus = vus
        self.results = []
        
    async def run_single_test(self, page):
        """Run a single browser test and collect comprehensive metrics"""
        start_time = time.time()
        
        try:
            # Navigate to the page
            response = await page.goto(self.target_url, wait_until='networkidle')
            
            # Wait a bit for all metrics to be available
            await page.wait_for_timeout(2000)
            
            # Collect comprehensive performance metrics
            metrics = await page.evaluate("""
                () => {
                    return new Promise((resolve) => {
                        const metrics = {};
                        
                        // Get navigation timing
                        const nav = performance.getEntriesByType('navigation')[0];
                        if (nav) {
                            metrics.dom_content_loaded = nav.domContentLoadedEventEnd - nav.fetchStart;
                            metrics.load_complete = nav.loadEventEnd - nav.fetchStart;
                            metrics.time_to_first_byte = nav.responseStart - nav.fetchStart;
                            metrics.dns_lookup = nav.domainLookupEnd - nav.domainLookupStart;
                            metrics.tcp_connection = nav.connectEnd - nav.connectStart;
                            metrics.ssl_handshake = nav.secureConnectionStart > 0 ? nav.connectEnd - nav.secureConnectionStart : 0;
                        }
                        
                        // Get paint timing
                        const paints = performance.getEntriesByType('paint');
                        paints.forEach(paint => {
                            if (paint.name === 'first-contentful-paint') {
                                metrics.first_contentful_paint = paint.startTime;
                            }
                            if (paint.name === 'first-paint') {
                                metrics.first_paint = paint.startTime;
                            }
                        });
                        
                        // Get LCP (Largest Contentful Paint)
                        const lcpEntries = performance.getEntriesByType('largest-contentful-paint');
                        if (lcpEntries.length > 0) {
                            metrics.largest_contentful_paint = lcpEntries[lcpEntries.length - 1].startTime;
                        }
                        
                        // Get CLS (Cumulative Layout Shift)
                        let clsValue = 0;
                        const clsEntries = performance.getEntriesByType('layout-shift');
                        clsEntries.forEach(entry => {
                            if (!entry.hadRecentInput) {
                                clsValue += entry.value;
                            }
                        });
                        metrics.cumulative_layout_shift = clsValue;
                        
                        // Get FID (First Input Delay) - approximate
                        const fidEntries = performance.getEntriesByType('first-input');
                        if (fidEntries.length > 0) {
                            metrics.first_input_delay = fidEntries[0].processingStart - fidEntries[0].startTime;
                        }
                        
                        // Get resource timing
                        const resources = performance.getEntriesByType('resource');
                        metrics.resource_count = resources.length;
                        metrics.total_resource_size = resources.reduce((sum, r) => sum + (r.transferSize || 0), 0);
                        
                        // Calculate resource timing statistics
                        const resourceLoadTimes = resources.map(r => r.responseEnd - r.startTime);
                        if (resourceLoadTimes.length > 0) {
                            metrics.avg_resource_load_time = resourceLoadTimes.reduce((a, b) => a + b, 0) / resourceLoadTimes.length;
                            metrics.max_resource_load_time = Math.max(...resourceLoadTimes);
                        }
                        
                        // Get memory usage
                        if (performance.memory) {
                            metrics.js_heap_used = performance.memory.usedJSHeapSize;
                            metrics.js_heap_total = performance.memory.totalJSHeapSize;
                            metrics.js_heap_limit = performance.memory.jsHeapSizeLimit;
                        }
                        
                        // Get long tasks (tasks > 50ms)
                        const longTasks = performance.getEntriesByType('longtask');
                        metrics.long_tasks_count = longTasks.length;
                        metrics.total_blocking_time = longTasks.reduce((sum, task) => sum + task.duration, 0);
                        
                        // Get layout and rendering metrics
                        const layoutEntries = performance.getEntriesByType('measure');
                        let layoutDuration = 0;
                        let recalcStyleDuration = 0;
                        let scriptDuration = 0;
                        let paintDuration = 0;
                        
                        layoutEntries.forEach(entry => {
                            if (entry.name.includes('layout')) layoutDuration += entry.duration;
                            if (entry.name.includes('recalc')) recalcStyleDuration += entry.duration;
                            if (entry.name.includes('script')) scriptDuration += entry.duration;
                            if (entry.name.includes('paint')) paintDuration += entry.duration;
                        });
                        
                        metrics.layout_duration = layoutDuration;
                        metrics.recalc_style_duration = recalcStyleDuration;
                        metrics.script_duration = scriptDuration;
                        metrics.paint_duration = paintDuration;
                        
                        resolve(metrics);
                    });
                }
            """)
            
            # Get additional metrics from page
            try:
                # Get viewport size
                viewport = await page.viewport_size()
                metrics['viewport_width'] = viewport['width']
                metrics['viewport_height'] = viewport['height']
                
                # Get page title
                title = await page.title()
                metrics['page_title'] = title
                
                # Get URL after redirects
                current_url = page.url
                metrics['final_url'] = current_url
                
            except Exception as e:
                print(f"Warning: Could not get additional page metrics: {e}")
            
            # Simulate user interaction for FID measurement
            try:
                await page.click('body')
                await page.wait_for_timeout(100)
            except:
                pass
            
            end_time = time.time()
            metrics['total_time'] = end_time - start_time
            metrics['status'] = response.status if response else 0
            
            return metrics
            
        except Exception as e:
            return {
                'error': str(e),
                'total_time': time.time() - start_time,
                'status': 0
            }
    
    async def run_load_test(self):
        """Run the load test with multiple virtual users"""
        async with async_playwright() as p:
            # Launch browser with performance monitoring
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    '--no-sandbox', 
                    '--disable-dev-shm-usage',
                    '--enable-precise-memory-info',
                    '--enable-gpu-benchmarking',
                    '--enable-threaded-compositing'
                ]
            )
            
            start_time = time.time()
            tasks = []
            
            # Create tasks for each virtual user
            for i in range(self.vus):
                task = asyncio.create_task(self.run_virtual_user(browser, i))
                tasks.append(task)
            
            # Wait for all tasks to complete or timeout
            try:
                await asyncio.wait_for(
                    asyncio.gather(*tasks, return_exceptions=True),
                    timeout=self.duration_seconds
                )
            except asyncio.TimeoutError:
                print(f"Test completed after {self.duration_seconds} seconds")
            
            await browser.close()
            
            # Calculate comprehensive summary
            return self.calculate_comprehensive_summary()
    
    async def run_virtual_user(self, browser, user_id):
        """Run a single virtual user for the duration of the test"""
        context = await browser.new_context()
        page = await context.new_page()
        
        start_time = time.time()
        iteration = 0
        
        while time.time() - start_time < self.duration_seconds:
            iteration += 1
            result = await self.run_single_test(page)
            result['user_id'] = user_id
            result['iteration'] = iteration
            result['timestamp'] = datetime.now().isoformat()
            
            self.results.append(result)
            
            # Small delay between iterations
            await asyncio.sleep(1)
        
        await context.close()
    
    def calculate_comprehensive_summary(self):
        """Calculate comprehensive summary metrics from all results"""
        if not self.results:
            return {}
        
        # Filter out error results
        successful_results = [r for r in self.results if 'error' not in r]
        
        summary = {
            'total_iterations': len(self.results),
            'successful_iterations': len(successful_results),
            'error_rate': (len(self.results) - len(successful_results)) / len(self.results) if self.results else 0,
            'total_vus': self.vus,
            'test_duration': self.duration_seconds,
            'target_url': self.target_url
        }
        
        if successful_results:
            # Define all metrics to calculate statistics for
            metrics_to_analyze = [
                'total_time', 'dom_content_loaded', 'load_complete', 
                'first_contentful_paint', 'first_paint', 'largest_contentful_paint',
                'cumulative_layout_shift', 'first_input_delay', 'time_to_first_byte',
                'resource_count', 'total_resource_size', 'avg_resource_load_time',
                'js_heap_used', 'js_heap_total', 'long_tasks_count', 'total_blocking_time',
                'layout_duration', 'recalc_style_duration', 'script_duration', 'paint_duration',
                'dns_lookup', 'tcp_connection', 'ssl_handshake'
            ]
            
            for metric in metrics_to_analyze:
                values = [r.get(metric, 0) for r in successful_results if metric in r and r[metric] is not None]
                if values:
                    summary[f'avg_{metric}'] = sum(values) / len(values)
                    summary[f'min_{metric}'] = min(values)
                    summary[f'max_{metric}'] = max(values)
                    summary[f'p50_{metric}'] = sorted(values)[len(values)//2] if values else 0
                    summary[f'p95_{metric}'] = sorted(values)[int(len(values)*0.95)] if values else 0
                    summary[f'p99_{metric}'] = sorted(values)[int(len(values)*0.99)] if values else 0
            
            # Calculate Core Web Vitals scores
            summary['lcp_score'] = self.calculate_lcp_score(summary.get('avg_largest_contentful_paint', 0))
            summary['fid_score'] = self.calculate_fid_score(summary.get('avg_first_input_delay', 0))
            summary['cls_score'] = self.calculate_cls_score(summary.get('avg_cumulative_layout_shift', 0))
            
            # Calculate overall performance score
            summary['performance_score'] = (summary['lcp_score'] + summary['fid_score'] + summary['cls_score']) / 3
        
        return summary
    
    def calculate_lcp_score(self, lcp_ms):
        """Calculate LCP score (0-100)"""
        if lcp_ms <= 2500: return 100
        elif lcp_ms <= 4000: return 75
        else: return 50
    
    def calculate_fid_score(self, fid_ms):
        """Calculate FID score (0-100)"""
        if fid_ms <= 100: return 100
        elif fid_ms <= 300: return 75
        else: return 50
    
    def calculate_cls_score(self, cls_value):
        """Calculate CLS score (0-100)"""
        if cls_value <= 0.1: return 100
        elif cls_value <= 0.25: return 75
        else: return 50

async def main():
    """Main function to run the advanced browser test"""
    target_url = os.getenv('TARGET_URL', 'https://wearepop.com')
    duration_minutes = int(os.getenv('DURATION_MINUTES', '2'))
    vus = int(os.getenv('VUS', '5'))
    
    print(f"🚀 Starting Advanced Playwright browser test")
    print(f"📊 Target: {target_url}")
    print(f"⏱️  Duration: {duration_minutes} minutes")
    print(f"👥 Virtual Users: {vus}")
    
    test = AdvancedPlaywrightBrowserTest(target_url, duration_minutes, vus)
    summary = await test.run_load_test()
    
    # Save results
    output_file = os.getenv('OUTPUT_FILE', 'playwright_advanced_results.json')
    with open(output_file, 'w') as f:
        json.dump({
            'summary': summary,
            'detailed_results': test.results
        }, f, indent=2)
    
    print(f"✅ Advanced test completed!")
    print(f"📊 Results saved to: {output_file}")
    print(f"📈 Core Web Vitals Scores:")
    print(f"   LCP: {summary.get('lcp_score', 0):.0f}/100")
    print(f"   FID: {summary.get('fid_score', 0):.0f}/100") 
    print(f"   CLS: {summary.get('cls_score', 0):.0f}/100")
    print(f"   Overall: {summary.get('performance_score', 0):.0f}/100")

if __name__ == "__main__":
    asyncio.run(main())
