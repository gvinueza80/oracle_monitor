/**
 * Enhanced API client with retry logic and error handling
 */

import axios, { AxiosError, AxiosInstance } from 'axios';
import { withRetry, CircuitBreaker } from '../utils/retry';
import { logger } from '../utils/logger';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api';

class EnhancedApiClient {
  private client: AxiosInstance;
  private circuitBreaker: CircuitBreaker;

  constructor() {
    this.client = axios.create({
      baseURL: API_BASE_URL,
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    this.circuitBreaker = new CircuitBreaker(
      async () => this.client.get('/health'),
      { failureThreshold: 5, resetTimeout: 60000 }
    );

    this.setupInterceptors();
  }

  private setupInterceptors() {
    // Request interceptor
    this.client.interceptors.request.use((config) => {
      const token = localStorage.getItem('accessToken');
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
      return config;
    });

    // Response interceptor
    this.client.interceptors.response.use(
      (response) => response,
      async (error: AxiosError) => {
        if (error.response?.status === 401) {
          logger.warn('Unauthorized, attempting token refresh');
          const refreshToken = localStorage.getItem('refreshToken');
          if (refreshToken) {
            try {
              const response = await axios.post(`${API_BASE_URL}/auth/refresh`, {
                refresh_token: refreshToken,
              });
              localStorage.setItem('accessToken', response.data.access_token);
              return this.client.request(error.config!);
            } catch (refreshError) {
              logger.error('Token refresh failed', refreshError as Error);
              localStorage.removeItem('accessToken');
              localStorage.removeItem('refreshToken');
              window.location.href = '/login';
            }
          }
        }

        logger.error('API request failed', error as Error, {
          status: error.response?.status,
          path: error.config?.url,
        });

        return Promise.reject(error);
      }
    );
  }

  async get<T>(url: string, config?: any): Promise<T> {
    return withRetry(
      async () => {
        const response = await this.client.get<T>(url, config);
        return response.data;
      },
      { maxRetries: 3, initialDelay: 1000 }
    );
  }

  async post<T>(url: string, data?: any, config?: any): Promise<T> {
    return withRetry(
      async () => {
        const response = await this.client.post<T>(url, data, config);
        return response.data;
      },
      { maxRetries: 2, initialDelay: 1000 }
    );
  }

  async put<T>(url: string, data?: any, config?: any): Promise<T> {
    return withRetry(
      async () => {
        const response = await this.client.put<T>(url, data, config);
        return response.data;
      },
      { maxRetries: 2, initialDelay: 1000 }
    );
  }

  async delete<T>(url: string, config?: any): Promise<T> {
    return withRetry(
      async () => {
        const response = await this.client.delete<T>(url, config);
        return response.data;
      },
      { maxRetries: 1, initialDelay: 500 }
    );
  }

  async checkHealth(): Promise<boolean> {
    try {
      await this.circuitBreaker.execute();
      return true;
    } catch {
      return false;
    }
  }
}

export const apiClient = new EnhancedApiClient();
