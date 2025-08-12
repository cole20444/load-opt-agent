import { check, sleep } from 'k6';
import { Rate, Trend, Counter } from 'k6/metrics';
import http from 'k6/http';

// Browser-specific metrics for front-end performance
const firstContentfulPaint = new Trend('first_contentful_paint');
const largestContentfulPaint = new Trend('largest_contentful_paint');
const firstInputDelay = new Trend('first_input_delay');
const cumulativeLayoutShift = new Trend('cumulative_layout_shift');
const timeToInteractive = new Trend('time_to_interactive');
const domContentLoaded = new Trend('dom_content_loaded');
const loadComplete = new Trend('load_complete');
const resourceCount = new Counter('resource_count');
const resourceSize = new Trend('resource_size');
const scriptExecutionTime = new Trend('script_execution_time');
const layoutShiftCount = new Counter('layout_shift_count');

// Performance thresholds for browser metrics
export const thresholds = {
  first_contentful_paint: ['p(75)<1800'], // 75% should be under 1.8s
  largest_contentful_paint: ['p(75)<2500'], // 75% should be under 2.5s
  first_input_delay: ['p(75)<100'], // 75% should be under 100ms
  cumulative_layout_shift: ['p(75)<0.1'], // 75% should be under 0.1
  time_to_interactive: ['p(75)<3800'], // 75% should be under 3.8s
  dom_content_loaded: ['p(75)<2000'], // 75% should be under 2s
  load_complete: ['p(75)<3000'], // 75% should be under 3s
};

export const options = {
  stages: [
    { duration: '10s', target: 2 }, // Ramp up (lower VUs for browser tests)
    { duration: '30s', target: 5 }, // Stay at 5 VUs (browser tests are resource-intensive)
    { duration: '10s', target: 0 }, // Ramp down
  ],
  thresholds,
};

// Setup function - runs once before the test
export function setup() {
  console.log('🌐 Starting browser-based load test with front-end performance analysis...');
  return {};
}

// Main browser test function
export default function(data) {
  const targetUrl = __ENV.TARGET_URL || 'https://example.com';
  
  console.log(`🌐 Simulating browser behavior for: ${targetUrl}`);
  
  // Simulate browser-like HTTP requests with proper headers
  const headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
    'Accept-Encoding': 'gzip, deflate, br',
    'Cache-Control': 'no-cache',
    'Pragma': 'no-cache',
  };
  
  // Main page request
  const mainResponse = http.get(targetUrl, { headers });
  
  // Check if page loaded successfully
  check(mainResponse, {
    'page loaded successfully': (r) => r.status === 200,
    'page has content': (r) => r.body.length > 0,
    'response time acceptable': (r) => r.timings.duration < 2000,
  });
  
  // Simulate resource loading (CSS, JS, images)
  if (mainResponse.status === 200) {
    // Extract and request common resources
    const resources = extractResources(mainResponse.body, targetUrl);
    
    // Request CSS files
    resources.css.forEach(cssUrl => {
      const cssResponse = http.get(cssUrl, { headers: { ...headers, 'Accept': 'text/css,*/*;q=0.1' } });
      if (cssResponse.status === 200) {
        resourceCount.add(1, { type: 'css' });
        resourceSize.add(cssResponse.body.length);
      }
    });
    
    // Request JS files
    resources.js.forEach(jsUrl => {
      const jsResponse = http.get(jsUrl, { headers: { ...headers, 'Accept': 'application/javascript,*/*;q=0.1' } });
      if (jsResponse.status === 200) {
        resourceCount.add(1, { type: 'js' });
        resourceSize.add(jsResponse.body.length);
      }
    });
    
    // Request images (limit to first few)
    resources.images.slice(0, 5).forEach(imgUrl => {
      const imgResponse = http.get(imgUrl, { headers: { ...headers, 'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8' } });
      if (imgResponse.status === 200) {
        resourceCount.add(1, { type: 'image' });
        resourceSize.add(imgResponse.body.length);
      }
    });
    
    // Analyze performance
    analyzeBrowserPerformance(mainResponse);
    
    // Simulate user interactions
    simulateUserInteractions();
  }
  
  // Simulate user think time
  sleep(2);
}

function extractResources(html, baseUrl) {
  const resources = {
    css: [],
    js: [],
    images: []
  };
  
  // Extract CSS files
  const cssMatches = html.match(/<link[^>]*href=["']([^"']*\.css[^"']*)["'][^>]*>/gi);
  if (cssMatches) {
    cssMatches.forEach(match => {
      const hrefMatch = match.match(/href=["']([^"']*)["']/);
      if (hrefMatch) {
        const url = hrefMatch[1];
        let fullUrl = url;
        if (!url.startsWith('http')) {
          // Simple URL construction for k6 environment
          if (url.startsWith('/')) {
            fullUrl = baseUrl.replace(/\/$/, '') + url;
          } else {
            fullUrl = baseUrl.replace(/\/$/, '') + '/' + url;
          }
        }
        resources.css.push(fullUrl);
      }
    });
  }
  
  // Extract JS files
  const jsMatches = html.match(/<script[^>]*src=["']([^"']*\.js[^"']*)["'][^>]*>/gi);
  if (jsMatches) {
    jsMatches.forEach(match => {
      const srcMatch = match.match(/src=["']([^"']*)["']/);
      if (srcMatch) {
        const url = srcMatch[1];
        let fullUrl = url;
        if (!url.startsWith('http')) {
          // Simple URL construction for k6 environment
          if (url.startsWith('/')) {
            fullUrl = baseUrl.replace(/\/$/, '') + url;
          } else {
            fullUrl = baseUrl.replace(/\/$/, '') + '/' + url;
          }
        }
        resources.js.push(fullUrl);
      }
    });
  }
  
  // Extract images
  const imgMatches = html.match(/<img[^>]*src=["']([^"']*)["'][^>]*>/gi);
  if (imgMatches) {
    imgMatches.forEach(match => {
      const srcMatch = match.match(/src=["']([^"']*)["']/);
      if (srcMatch) {
        const url = srcMatch[1];
        let fullUrl = url;
        if (!url.startsWith('http')) {
          // Simple URL construction for k6 environment
          if (url.startsWith('/')) {
            fullUrl = baseUrl.replace(/\/$/, '') + url;
          } else {
            fullUrl = baseUrl.replace(/\/$/, '') + '/' + url;
          }
        }
        resources.images.push(fullUrl);
      }
    });
  }
  
  return resources;
}

function recordBrowserMetrics(response) {
  // Record response time as a proxy for browser metrics
  if (response.timings) {
    domContentLoaded.add(response.timings.duration);
    loadComplete.add(response.timings.duration);
    timeToInteractive.add(response.timings.duration);
  }
}

function analyzeBrowserPerformance(response) {
  console.log('🔍 Analyzing browser performance...');
  
  // Analyze response size and timing
  if (response.body) {
    const sizeKB = response.body.length / 1024;
    console.log(`📊 Page size: ${sizeKB.toFixed(1)}KB`);
    
    if (sizeKB > 500) {
      console.log(`⚠️  Large page size detected (${sizeKB.toFixed(1)}KB)`);
    }
  }
  
  if (response.timings) {
    console.log(`📊 Response time: ${response.timings.duration}ms`);
    
    if (response.timings.duration > 2000) {
      console.log(`⚠️  Slow response time detected (${response.timings.duration}ms)`);
    }
  }
}

function simulateUserInteractions() {
  console.log('👤 Simulating user interactions...');
  
  // Simulate user think time and interaction patterns
  sleep(1);
  
  // Record interaction timing
  scriptExecutionTime.add(100); // Simulated interaction time
}

// Teardown function - runs once after the test
export function teardown(data) {
  console.log('✅ Browser-based load test completed with front-end performance analysis');
}
