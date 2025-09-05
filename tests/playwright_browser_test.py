#!/usr/bin/env python3
"""
Playwright-based browser test for Azure containers
This is an alternative to k6/browser that works better in containerized environments
"""

import asyncio
import json
import time
from datetime import datetime
from playwright.async_api import async_playwright
import os

class PlaywrightBrowserTest:
    def __init__(self, target_url, duration_minutes=2, vus=5):
        self.target_url = target_url
        self.duration_seconds = duration_minutes * 60
        self.vus = vus
        self.results = []
        
    async def run_single_test(self, page):
        """Run a single browser test and collect metrics"""
        start_time = time.time()
        
        try:
            # Navigate to the page
            response = await page.goto(self.target_url, wait_until='networkidle')
            
            # Collect Core Web Vitals
            metrics = await page.evaluate("""
                () => {
                    return new Promise((resolve) => {
                        const metrics = {};
                        
                        // Get navigation timing
                        const nav = performance.getEntriesByType('navigation')[0];
                        if (nav) {
                            metrics.dom_content_loaded = nav.domContentLoadedEventEnd - nav.fetchStart;
                            metrics.load_complete = nav.loadEventEnd - nav.fetchStart;
                        }
                        
                        // Get paint timing
                        const paints = performance.getEntriesByType('paint');
                        paints.forEach(paint => {
                            if (paint.name === 'first-contentful-paint') {
                                metrics.first_contentful_paint = paint.startTime;
                            }
                        });
                        
                        // Get resource timing
                        const resources = performance.getEntriesByType('resource');
                        metrics.resource_count = resources.length;
                        metrics.total_resource_size = resources.reduce((sum, r) => sum + (r.transferSize || 0), 0);
                        
                        resolve(metrics);
                    });
                }
            """)
            
            # Simulate user interaction
            await page.click('body')  # Simple click
            await page.wait_for_timeout(100)
            
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
            # Launch browser
            browser = await p.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-dev-shm-usage']
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
            
            # Calculate summary metrics
            return self.calculate_summary()
    
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
    
    def calculate_summary(self):
        """Calculate summary metrics from all results"""
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
            # Calculate averages for key metrics
            metrics_to_average = [
                'total_time', 'dom_content_loaded', 'load_complete', 
                'first_contentful_paint', 'resource_count', 'total_resource_size'
            ]
            
            for metric in metrics_to_average:
                values = [r.get(metric, 0) for r in successful_results if metric in r]
                if values:
                    summary[f'avg_{metric}'] = sum(values) / len(values)
                    summary[f'min_{metric}'] = min(values)
                    summary[f'max_{metric}'] = max(values)
        
        return summary

async def main():
    """Main function to run the browser test"""
    target_url = os.getenv('TARGET_URL', 'https://wearepop.com')
    duration_minutes = int(os.getenv('DURATION_MINUTES', '2'))
    vus = int(os.getenv('VUS', '5'))
    
    print(f"🚀 Starting Playwright browser test")
    print(f"📊 Target: {target_url}")
    print(f"⏱️  Duration: {duration_minutes} minutes")
    print(f"👥 Virtual Users: {vus}")
    
    test = PlaywrightBrowserTest(target_url, duration_minutes, vus)
    summary = await test.run_load_test()
    
    # Save results
    output_file = os.getenv('OUTPUT_FILE', 'playwright_results.json')
    with open(output_file, 'w') as f:
        json.dump({
            'summary': summary,
            'detailed_results': test.results
        }, f, indent=2)
    
    print(f"✅ Test completed!")
    print(f"📊 Results saved to: {output_file}")
    print(f"📈 Summary: {json.dumps(summary, indent=2)}")

if __name__ == "__main__":
    asyncio.run(main())
