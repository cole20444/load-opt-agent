import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Trend, Counter } from 'k6/metrics';

// Custom metrics
const errorRate = new Rate('errors');
const responseTime = new Trend('response_time');
const requestSize = new Trend('request_size');
const responseSize = new Trend('response_size');
const successCounter = new Counter('successful_requests');
const failureCounter = new Counter('failed_requests');

export let options = {
    vus: parseInt(__ENV.VUS) || 50,
    duration: __ENV.DURATION || '30s',
    thresholds: {
        'http_req_duration': ['p(95)<2000'], // 95% of requests should be below 2s
        'http_req_failed': ['rate<0.1'],     // Error rate should be less than 10%
        'errors': ['rate<0.1'],              // Custom error rate
    },
};

export default function () {
    const targetUrl = __ENV.TARGET_URL || 'https://example.com';
    
    // Record request start time for timing
    const startTime = Date.now();
    
    try {
        // Make HTTP request
        let res = http.get(targetUrl, {
            timeout: '10s',
            headers: {
                'User-Agent': 'Load-Test-Agent/1.0',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
            }
        });
        
        // Record response time
        const responseTimeMs = Date.now() - startTime;
        responseTime.add(responseTimeMs);
        
        // Record payload sizes
        responseSize.add(res.body.length);
        
        // Check response
        const success = check(res, {
            "status is 200": (r) => r.status === 200,
            "response time < 2000ms": (r) => r.timings.duration < 2000,
            "response has content": (r) => r.body.length > 0,
        });
        
        if (success) {
            successCounter.add(1);
            errorRate.add(0); // No error
        } else {
            failureCounter.add(1);
            errorRate.add(1); // Error occurred
            console.log(`Request failed: ${res.status} - ${targetUrl}`);
        }
        
    } catch (error) {
        failureCounter.add(1);
        errorRate.add(1);
        console.log(`Request error: ${error.message} - ${targetUrl}`);
    }
    
    // Think time between requests
    sleep(1);
}

// Setup and teardown functions for additional context
export function setup() {
    console.log(`Starting load test with ${__ENV.VUS || 50} VUs for ${__ENV.DURATION || '30s'}`);
    console.log(`Target URL: ${__ENV.TARGET_URL || 'https://example.com'}`);
}

export function teardown(data) {
    console.log('Load test completed');
}
