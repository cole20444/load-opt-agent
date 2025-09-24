import { check, sleep } from 'k6';
import { Rate, Trend, Counter } from 'k6/metrics';

// Try to import browser module with error handling
let browser;
try {
  browser = require('k6/browser');
  console.log('✅ k6/browser module loaded successfully');
} catch (e) {
  console.log('❌ k6/browser module failed to load:', e.message);
  browser = null;
}

// Simple browser metrics for testing
const pageLoadTime = new Trend('page_load_time');
const browserRequests = new Counter('browser_requests');
const browserModuleStatus = new Counter('browser_module_status');

// Performance thresholds for browser metrics
export const thresholds = {
  page_load_time: ['p(95)<5000'],
  browser_requests: ['count>0'],
};

export const options = {
  vus: 5,
  duration: '30s',
  scenarios: {
    ui: {
      executor: 'shared-iterations',
      vus: 5,
      iterations: 5,
      exec: 'default',
      options: {
        browser: {
          type: 'chromium',
          headless: true,
        },
      },
    },
  },
  thresholds,
};


export function setup() {
  console.log('🌐 Starting browser-based load test with front-end performance analysis...');
  return {};
}

export default async function () {
  const targetUrl = __ENV.TARGET_URL || 'https://example.com';
  console.log(`🌐 Starting simple browser test for: ${targetUrl}`);

  // Check if browser module is available
  if (!browser) {
    console.log('❌ Browser module not available, falling back to basic test');
    browserModuleStatus.add(0); // 0 = not available
    sleep(1);
    return;
  }

  browserModuleStatus.add(1); // 1 = available

  try {
    const page = await browser.newPage();
    console.log('✅ Browser page created successfully');

    // Track network requests and resources
    const resources = [];
    const networkRequests = [];
    
    // Listen to network requests
    page.on('request', (request) => {
      networkRequests.push({
        url: request.url(),
        method: request.method(),
        resourceType: request.resourceType(),
        timestamp: Date.now()
      });
    });
    
    // Listen to network responses
    page.on('response', async (response) => {
      try {
        const request = response.request();
        const url = request.url();
        const resourceType = request.resourceType();
        
        // Get response size if available
        const headers = response.headers();
        const contentLength = headers['content-length'];
        const size = contentLength ? parseInt(contentLength) : 0;
        
        resources.push({
          url: url,
          resourceType: resourceType,
          status: response.status(),
          size: size,
          timestamp: Date.now(),
          loadTime: 0 // Will be calculated later
        });
      } catch (error) {
        console.log('Error tracking response:', error.message);
      }
    });

    const startTime = Date.now();
    await page.goto(targetUrl, { waitUntil: 'load' });
    const loadTime = Date.now() - startTime;

    // Calculate load times for resources
    resources.forEach(resource => {
      resource.loadTime = loadTime - (resource.timestamp - startTime);
    });

    // Record simple metrics
    pageLoadTime.add(loadTime);
    browserRequests.add(1);

    // Basic check
    const content = await page.content();
    check(content, {
      'page has content': (html) => !!html && html.length > 0,
    });

    console.log(`📊 Page loaded in ${loadTime}ms`);
    console.log(`📊 Captured ${resources.length} resources and ${networkRequests.length} network requests`);

    // Log slowest resources
    const slowestResources = resources
      .filter(r => r.loadTime > 0)
      .sort((a, b) => b.loadTime - a.loadTime)
      .slice(0, 5);
    
    if (slowestResources.length > 0) {
      console.log('🐌 Slowest resources:');
      slowestResources.forEach((resource, index) => {
        console.log(`  ${index + 1}. ${resource.resourceType}: ${resource.loadTime.toFixed(0)}ms - ${resource.url.substring(0, 80)}...`);
      });
    }

    await page.close();
    console.log('✅ Browser page closed successfully');

  } catch (error) {
    console.log('❌ Browser test failed:', error.message);
    browserModuleStatus.add(2); // 2 = error
  }

  sleep(1);
}


export function teardown() {
  console.log('✅ Browser-based load test completed with front-end performance analysis');
}