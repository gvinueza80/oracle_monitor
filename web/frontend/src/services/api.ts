import axios, { AxiosInstance, AxiosError } from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api';

class ApiClient {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: API_BASE_URL,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Request interceptor to add token
    this.client.interceptors.request.use((config) => {
      const token = localStorage.getItem('accessToken');
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
      return config;
    });

    // Response interceptor to handle token refresh
    this.client.interceptors.response.use(
      (response) => response,
      async (error: AxiosError) => {
        if (error.response?.status === 401) {
          const refreshToken = localStorage.getItem('refreshToken');
          if (refreshToken) {
            try {
              const response = await axios.post(`${API_BASE_URL}/auth/refresh`, {
                refresh_token: refreshToken,
              });
              localStorage.setItem('accessToken', response.data.access_token);
              return this.client.request(error.config!);
            } catch {
              localStorage.removeItem('accessToken');
              localStorage.removeItem('refreshToken');
              window.location.href = '/login';
            }
          }
        }
        return Promise.reject(error);
      }
    );
  }

  // Auth endpoints
  login(username: string, password: string) {
    return this.client.post('/auth/login', { username, password });
  }

  logout() {
    return this.client.post('/auth/logout');
  }

  // Metrics endpoints
  getOverviewMetrics(instanceId: string) {
    return this.client.get('/metrics/overview', { params: { instance_id: instanceId } });
  }

  getSessions(instanceId: string, limit = 100, offset = 0) {
    return this.client.get('/metrics/sessions', {
      params: { instance_id: instanceId, limit, offset },
    });
  }

  getLocks(instanceId: string) {
    return this.client.get('/metrics/locks', { params: { instance_id: instanceId } });
  }

  getSlowQueries(instanceId: string, limit = 10) {
    return this.client.get('/metrics/slow-queries', {
      params: { instance_id: instanceId, limit },
    });
  }

  getTablespace(instanceId: string) {
    return this.client.get('/metrics/tablespace', { params: { instance_id: instanceId } });
  }

  getMetricHistory(instanceId: string, metricType: string, hours = 24) {
    return this.client.get(`/metrics/${metricType}/history`, {
      params: { instance_id: instanceId, hours },
    });
  }

  // Alerts endpoints
  getAlerts(instanceId: string, severity?: string, limit = 100, offset = 0) {
    return this.client.get('/alerts', {
      params: { instance_id: instanceId, severity, limit, offset },
    });
  }

  getAlertRules(instanceId: string) {
    return this.client.get('/alerts/rules', { params: { instance_id: instanceId } });
  }

  createAlertRule(instanceId: string, rule: any) {
    return this.client.post('/alerts/rules', rule, {
      params: { instance_id: instanceId },
    });
  }

  updateAlertRule(ruleId: string, rule: any) {
    return this.client.put(`/alerts/rules/${ruleId}`, rule);
  }

  deleteAlertRule(ruleId: string) {
    return this.client.delete(`/alerts/rules/${ruleId}`);
  }

  acknowledgeAlert(alertId: number) {
    return this.client.post(`/alerts/${alertId}/acknowledge`);
  }

  resolveAlert(alertId: number) {
    return this.client.post(`/alerts/${alertId}/resolve`);
  }

  // Instances endpoints
  getInstances() {
    return this.client.get('/instances');
  }

  getInstance(instanceId: string) {
    return this.client.get(`/instances/${instanceId}`);
  }

  createInstance(instance: any) {
    return this.client.post('/instances', instance);
  }

  updateInstance(instanceId: string, instance: any) {
    return this.client.put(`/instances/${instanceId}`, instance);
  }

  deleteInstance(instanceId: string) {
    return this.client.delete(`/instances/${instanceId}`);
  }

  testConnection(instanceId: string) {
    return this.client.post(`/instances/${instanceId}/test-connection`);
  }

  // Analytics endpoints
  getMetricTrend(instanceId: string, metricType: string, hours = 24) {
    return this.client.get(`/analytics/metrics/${metricType}/trend`, {
      params: { instance_id: instanceId, hours },
    });
  }

  forecastMetric(instanceId: string, metricType: string, forecastHours = 24) {
    return this.client.get(`/analytics/metrics/${metricType}/forecast`, {
      params: { instance_id: instanceId, forecast_hours: forecastHours },
    });
  }

  detectAnomalies(instanceId: string, metricType: string, lookbackHours = 24) {
    return this.client.get(`/analytics/metrics/${metricType}/anomalies`, {
      params: { instance_id: instanceId, lookback_hours: lookbackHours },
    });
  }

  compareMetricPeriods(instanceId: string, metricType: string, period1Hours = 24, period2Hours = 24) {
    return this.client.get(`/analytics/metrics/${metricType}/compare`, {
      params: {
        instance_id: instanceId,
        period_1_hours: period1Hours,
        period_2_hours: period2Hours,
      },
    });
  }

  getAlertPatterns(instanceId: string, days = 7) {
    return this.client.get('/analytics/alerts/patterns', {
      params: { instance_id: instanceId, days },
    });
  }

  generateDailyReport(instanceId: string) {
    return this.client.get('/analytics/report/daily', {
      params: { instance_id: instanceId },
    });
  }
}

export default new ApiClient();
