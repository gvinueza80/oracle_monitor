import http from 'k6/http';
import { check, sleep, group } from 'k6';

export const options = {
  stages: [
    { duration: '2m', target: 100 },
    { duration: '5m', target: 200 },
    { duration: '5m', target: 300 },
    { duration: '2m', target: 400 },
    { duration: '5m', target: 400 },
    { duration: '2m', target: 0 },
  ],
  thresholds: {
    http_req_duration: ['p(95)<1000', 'p(99)<2000'],
    http_req_failed: ['rate<0.05'],
  },
};

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000/api';
const AUTH_TOKEN = __ENV.AUTH_TOKEN || '';

export default function () {
  const headers = {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${AUTH_TOKEN}`,
  };

  group('Read-heavy workload', function () {
    http.get(`${BASE_URL}/metrics/overview/1`, {
      headers,
      tags: { name: 'Overview' },
    });

    http.get(`${BASE_URL}/metrics/history/1?page=1`, {
      headers,
      tags: { name: 'History' },
    });

    http.get(`${BASE_URL}/metrics/sessions/1`, {
      headers,
      tags: { name: 'Sessions' },
    });

    http.get(`${BASE_URL}/analytics/trend/1?metric_type=cpu_usage`, {
      headers,
      tags: { name: 'Trend' },
    });

    sleep(0.5);
  });

  group('Mixed workload', function () {
    // Read
    const res1 = http.get(`${BASE_URL}/alerts/history?page=1`, {
      headers,
      tags: { name: 'AlertHistory' },
    });

    check(res1, {
      'status is 200': (r) => r.status === 200,
    });

    // Write - create alert rule
    const payload = JSON.stringify({
      instance_id: 1,
      name: `Rule-${Date.now()}`,
      metric_type: 'cpu_usage',
      threshold: 80,
      operator: 'gt',
      enabled: true,
    });

    const res2 = http.post(`${BASE_URL}/alerts/rules`, payload, {
      headers,
      tags: { name: 'CreateRule' },
    });

    check(res2, {
      'create rule status is 201': (r) => r.status === 201,
    });

    sleep(0.5);
  });
}
