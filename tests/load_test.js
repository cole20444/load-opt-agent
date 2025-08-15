import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Trend, Counter } from 'k6/metrics';

// Custom metrics for detailed analysis
const resourceLoadTime = new Trend('resource_load_time');
const resourceSize = new Trend('resource_size');
const resourceType = new Counter('resource_type');
const compressionRatio = new Trend('compression_ratio');
const dnsLookupTime = new Trend('dns_lookup_time');
const tlsHandshakeTime = new Trend('tls_handshake_time');
const serverProcessingTime = new Trend('server_processing_time');
const dataTransferTime = new Trend('data_transfer_time');

// Performance thresholds
export const thresholds = {
  http_req_duration: ['p(95)<2000'], // 95% of requests should be below 2s
  http_req_failed: ['rate<0.1'], // Error rate should be below 10%
  resource_load_time: ['p(95)<1000'], // 95% of resources should load below 1s
  compression_ratio: ['avg>0.5'], // Average compression should be >50%
};

export const options = {
  // Dynamic stages based on environment variables
  stages: [
    // Ramp up to 10 VUs over 30 seconds
    { duration: '30s', target: 10 },
    // Stay at 10 VUs for 30 seconds
    { duration: '30s', target: 10 },
  ],
  thresholds,
  // Memory and resource optimizations
  discardResponseBodies: true, // Reduce memory usage
};

// Setup function - runs once before the test
export function setup() {
  console.log('🚀 Starting enhanced load test with resource analysis...');
  return {};
}

// Main test function
export default function(data) {
  const targetUrl = __ENV.TARGET_URL || 'https://example.com';
  
  // Main page request with detailed timing analysis and retry logic
  let mainResponse;
  let retryCount = 0;
  const maxRetries = 2;
  
  while (retryCount <= maxRetries) {
    try {
      mainResponse = http.get(targetUrl, {
        headers: {
          'User-Agent': 'k6-load-test-agent/1.0',
          'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
          'Accept-Encoding': 'gzip, deflate, br',
          'Accept-Language': 'en-US,en;q=0.5',
          'Cache-Control': 'no-cache',
        },
        timeout: '30s', // Increased timeout for main page
      });
      
      // If we get here, the request was successful
      break;
    } catch (error) {
      retryCount++;
      if (retryCount <= maxRetries) {
        console.log(`⚠️  Request failed, retrying (${retryCount}/${maxRetries}): ${error.message}`);
        sleep(1); // Wait 1 second before retry
      } else {
        console.log(`❌ Request failed after ${maxRetries} retries: ${error.message}`);
        return; // Exit the function if all retries failed
      }
    }
  }

  // Record main page metrics
  check(mainResponse, {
    'main page status is 200': (r) => r.status === 200,
    'main page loads successfully': (r) => r.status >= 200 && r.status < 400,
  });

  // Analyze main page performance
  if (mainResponse.status === 200) {
    // Record detailed timing metrics
    const timing = mainResponse.timings;
    
    // DNS lookup time (blocked time)
    if (timing.dns) {
      dnsLookupTime.add(timing.dns);
    }
    
    // TLS handshake time
    if (timing.tls_handshaking) {
      tlsHandshakeTime.add(timing.tls_handshaking);
    }
    
    // Server processing time (waiting time)
    if (timing.waiting) {
      serverProcessingTime.add(timing.waiting);
    }
    
    // Data transfer time (receiving time)
    if (timing.receiving) {
      dataTransferTime.add(timing.receiving);
    }
    
    // Compression analysis
    const contentLength = mainResponse.headers['Content-Length'];
    const transferEncoding = mainResponse.headers['Content-Encoding'];
    const responseSize = mainResponse.body ? mainResponse.body.length : 0;
    
    if (contentLength && transferEncoding && responseSize > 0) {
      const originalSize = parseInt(contentLength);
      const compressedSize = responseSize;
      const ratio = originalSize > 0 ? (originalSize - compressedSize) / originalSize : 0;
      compressionRatio.add(ratio);
    }
    
    // Resource analysis - extract and analyze page resources
    if (mainResponse.body) {
      analyzePageResources(mainResponse.body, targetUrl);
    }
  }

  // Simulate user behavior with think time
  sleep(1);
}

// Function to analyze page resources
function analyzePageResources(htmlContent, baseUrl) {
  try {
    // Extract resource URLs from HTML
    const resourcePatterns = [
      { type: 'image', pattern: /<img[^>]+src=["']([^"']+)["']/gi },
      { type: 'script', pattern: /<script[^>]+src=["']([^"']+)["']/gi },
      { type: 'stylesheet', pattern: /<link[^>]+href=["']([^"']+)["'][^>]*rel=["']stylesheet["']/gi },
      { type: 'font', pattern: /<link[^>]+href=["']([^"']+)["'][^>]*rel=["']preload["'][^>]*as=["']font["']/gi },
    ];

    const resources = new Set();
    
    // Extract resource URLs
    resourcePatterns.forEach(({ type, pattern }) => {
      let match;
      while ((match = pattern.exec(htmlContent)) !== null) {
        const url = match[1];
        let fullUrl = url;
        if (!url.startsWith('http')) {
          // Simple URL construction for k6 environment
          if (url.startsWith('/')) {
            fullUrl = baseUrl.replace(/\/$/, '') + url;
          } else {
            fullUrl = baseUrl.replace(/\/$/, '') + '/' + url;
          }
        }
        resources.add({ type, url: fullUrl });
      }
    });

    // Analyze each resource (sample a few to avoid overwhelming the test)
    const sampleResources = Array.from(resources).slice(0, 5);
    
    sampleResources.forEach(({ type, url }) => {
      try {
        const resourceResponse = http.get(url, {
          headers: {
            'User-Agent': 'k6-load-test-agent/1.0',
            'Accept-Encoding': 'gzip, deflate, br',
          },
          timeout: '20s', // Increased timeout for resources
        });

        if (resourceResponse.status === 200) {
          // Record resource metrics
          resourceLoadTime.add(resourceResponse.timings.duration);
          resourceSize.add(resourceResponse.body ? resourceResponse.body.length : 0);
          resourceType.add(1, { type });
          
          // Analyze resource-specific issues
          analyzeResourceIssues(type, url, resourceResponse);
        }
      } catch (error) {
        console.log(`Failed to analyze resource: ${url} - ${error.message}`);
      }
    });
    
  } catch (error) {
    console.log(`Error analyzing page resources: ${error.message}`);
  }
}

// Function to analyze specific resource issues
function analyzeResourceIssues(type, url, response) {
  const size = response.body ? response.body.length : 0;
  const loadTime = response.timings.duration;
  
  // Define thresholds for different resource types
  const thresholds = {
    image: { size: 500 * 1024, loadTime: 1000 }, // 500KB, 1s
    script: { size: 100 * 1024, loadTime: 500 }, // 100KB, 500ms
    stylesheet: { size: 50 * 1024, loadTime: 300 }, // 50KB, 300ms
    font: { size: 200 * 1024, loadTime: 800 }, // 200KB, 800ms
  };
  
  const threshold = thresholds[type] || { size: 100 * 1024, loadTime: 500 };
  
  // Check for performance issues
  if (size > threshold.size) {
    console.log(`⚠️  Large ${type} detected: ${url} (${(size / 1024).toFixed(1)}KB)`);
  }
  
  if (loadTime > threshold.loadTime) {
    console.log(`🐌 Slow ${type} detected: ${url} (${loadTime}ms)`);
  }
  
  // Check for compression
  const encoding = response.headers['Content-Encoding'];
  if (!encoding && size > 10 * 1024) {
    console.log(`📦 Uncompressed ${type} detected: ${url} (${(size / 1024).toFixed(1)}KB)`);
  }
  
  // Check for caching headers
  const cacheControl = response.headers['Cache-Control'];
  if (!cacheControl || cacheControl.includes('no-cache')) {
    console.log(`🔄 Uncached ${type} detected: ${url}`);
  }
}

// Teardown function - runs once after the test
export function teardown(data) {
  console.log('✅ Enhanced load test completed with resource analysis');
}
