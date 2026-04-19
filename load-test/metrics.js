import http from 'k6/http';
import { check, sleep, group } from 'k6';

export const options = {
  stages: [
    { duration: '1m', target: 10 },
    { duration: '3m', target: 50 },
    { duration: '2m', target: 100 },
    { duration: '1m', target: 0 },
  ],
  thresholds: {
    http_req_duration: ['p(95)<500', 'p(99)<1000'],
    http_req_failed: ['rate<0.1'],
    'group_duration{staticContent:yes}': ['p(99)<250'],
  },
};

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000/api';
const AUTH_TOKEN = __ENV.AUTH_TOKEN || '';

export default function () {
  const headers = {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${AUTH_TOKEN}`,
  };

  group('Metrics Endpoints', function () {
    // Get metrics overview
    const overviewRes = http.get(`${BASE_URL}/metrics/overview/1`, {
      headers,
      tags: { name: 'MetricsOverview' },
    });

    check(overviewRes, {
      'overview status is 200': (r) => r.status === 200,
      'overview has metrics': (r) => r.body.includes('metrics'),
    });

    sleep(1);

    // Get metric history
    const historyRes = http.get(
      `${BASE_URL}/metrics/history/1?page=1&per_page=50`,
      {
        headers,
        tags: { name: 'MetricsHistory' },
      }
    );

    check(historyRes, {
      'history status is 200': (r) => r.status === 200,
      'history has items': (r) => r.body.includes('items'),
    });

    sleep(1);

    // Get sessions
    const sessionsRes = http.get(`${BASE_URL}/metrics/sessions/1`, {
      headers,
      tags: { name: 'SessionsMetrics' },
    });

    check(sessionsRes, {
      'sessions status is 200': (r) => r.status === 200,
    });

    sleep(1);

    // Get locks
    const locksRes = http.get(`${BASE_URL}/metrics/locks/1`, {
      headers,
      tags: { name: 'LocksMetrics' },
    });

    check(locksRes, {
      'locks status is 200': (r) => r.status === 200,
    });

    sleep(1);

    // Get tablespace
    const tablespaceRes = http.get(`${BASE_URL}/metrics/tablespace/1`, {
      headers,
      tags: { name: 'TablespaceMetrics' },
    });

    check(tablespaceRes, {
      'tablespace status is 200': (r) => r.status === 200,
    });

    sleep(1);
  });

  group('Analytics Endpoints', function () {
    // Get trend
    const trendRes = http.get(
      `${BASE_URL}/analytics/trend/1?metric_type=cpu_usage`,
      {
        headers,
        tags: { name: 'TrendAnalysis' },
      }
    );

    check(trendRes, {
      'trend status is 200': (r) => r.status === 200,
    });

    sleep(1);

    // Get forecast
    const forecastRes = http.get(
      `${BASE_URL}/analytics/forecast/1?metric_type=memory_usage`,
      {
        headers,
        tags: { name: 'Forecast' },
      }
    );

    check(forecastRes, {
      'forecast status is 200': (r) => r.status === 200,
    });

    sleep(1);

    // Get anomalies
    const anomaliesRes = http.get(
      `${BASE_URL}/analytics/anomalies/1?metric_type=sessions`,
      {
        headers,
        tags: { name: 'Anomalies' },
      }
    );

    check(anomaliesRes, {
      'anomalies status is 200': (r) => r.status === 200,
    });

    sleep(1);
  });

  group('Alert Endpoints', function () {
    // List alert history
    const historyRes = http.get(
      `${BASE_URL}/alerts/history?page=1&per_page=20`,
      {
        headers,
        tags: { name: 'AlertHistory' },
      }
    );

    check(historyRes, {
      'alert history status is 200': (r) => r.status === 200,
    });

    sleep(1);

    // List alert rules
    const rulesRes = http.get(`${BASE_URL}/alerts/rules`, {
      headers,
      tags: { name: 'AlertRules' },
    });

    check(rulesRes, {
      'alert rules status is 200': (r) => r.status === 200,
    });

    sleep(1);
  });
}
