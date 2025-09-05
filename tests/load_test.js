import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  vus: 10,
  duration: '30s',
};

export default function() {
  const targetUrl = __ENV.TARGET_URL || 'https://example.com';
  
  // Simple HTTP GET request
  const response = http.get(targetUrl);
  
  // Check response
  check(response, {
    'status is 200': (r) => r.status === 200,
    'response time < 5000ms': (r) => r.timings.duration < 5000,
  });
  
  // Sleep between iterations
  sleep(1);
}
