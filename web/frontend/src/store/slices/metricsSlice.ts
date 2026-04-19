import { createSlice, PayloadAction } from '@reduxjs/toolkit';

interface Metric {
  metricType: string;
  metricValue: number;
  metricUnit: string;
  collectedAt: string;
  tags?: Record<string, any>;
}

interface OverviewMetrics {
  activeSessions: number;
  lockedSessions: number;
  tablespaceUsedPercent: number;
  slowQueriesCount: number;
  criticalAlerts: number;
  warningAlerts: number;
  instanceHealthStatus: string;
  lastUpdate: string;
}

interface MetricsState {
  overview: OverviewMetrics | null;
  metrics: Record<string, Metric[]>;
  isLoading: boolean;
  error: string | null;
  lastRefresh: string | null;
}

const initialState: MetricsState = {
  overview: null,
  metrics: {},
  isLoading: false,
  error: null,
  lastRefresh: null,
};

export const metricsSlice = createSlice({
  name: 'metrics',
  initialState,
  reducers: {
    setLoading: (state, action: PayloadAction<boolean>) => {
      state.isLoading = action.payload;
    },
    setOverviewMetrics: (state, action: PayloadAction<OverviewMetrics>) => {
      state.overview = action.payload;
      state.lastRefresh = new Date().toISOString();
    },
    setMetrics: (
      state,
      action: PayloadAction<{ type: string; data: Metric[] }>
    ) => {
      state.metrics[action.payload.type] = action.payload.data;
    },
    updateMetric: (state, action: PayloadAction<Metric>) => {
      const type = action.payload.metricType;
      if (!state.metrics[type]) {
        state.metrics[type] = [];
      }
      state.metrics[type].push(action.payload);
    },
    setError: (state, action: PayloadAction<string | null>) => {
      state.error = action.payload;
    },
  },
});

export const { setLoading, setOverviewMetrics, setMetrics, updateMetric, setError } =
  metricsSlice.actions;
export default metricsSlice.reducer;
