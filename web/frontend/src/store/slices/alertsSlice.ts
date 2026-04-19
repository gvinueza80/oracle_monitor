import { createSlice, PayloadAction } from '@reduxjs/toolkit';

interface AlertHistory {
  id: number;
  ruleId: string;
  triggeredAt: string;
  acknowledgedAt?: string;
  resolvedAt?: string;
  metricValue?: number;
  metricUnit?: string;
  message?: string;
  status: string;
}

interface AlertRule {
  id: string;
  instanceId: string;
  name: string;
  description?: string;
  metricType: string;
  threshold: number;
  condition: string;
  severity: string;
  enabled: boolean;
  notifications?: Record<string, any>;
  suppressUntil?: string;
  createdAt: string;
}

interface AlertsState {
  alerts: AlertHistory[];
  rules: AlertRule[];
  isLoading: boolean;
  error: string | null;
  filters: {
    severity?: string;
    status?: string;
  };
}

const initialState: AlertsState = {
  alerts: [],
  rules: [],
  isLoading: false,
  error: null,
  filters: {},
};

export const alertsSlice = createSlice({
  name: 'alerts',
  initialState,
  reducers: {
    setLoading: (state, action: PayloadAction<boolean>) => {
      state.isLoading = action.payload;
    },
    setAlerts: (state, action: PayloadAction<AlertHistory[]>) => {
      state.alerts = action.payload;
    },
    setRules: (state, action: PayloadAction<AlertRule[]>) => {
      state.rules = action.payload;
    },
    addAlert: (state, action: PayloadAction<AlertHistory>) => {
      state.alerts.unshift(action.payload);
    },
    addRule: (state, action: PayloadAction<AlertRule>) => {
      state.rules.push(action.payload);
    },
    updateRule: (state, action: PayloadAction<AlertRule>) => {
      const index = state.rules.findIndex((r) => r.id === action.payload.id);
      if (index !== -1) {
        state.rules[index] = action.payload;
      }
    },
    deleteRule: (state, action: PayloadAction<string>) => {
      state.rules = state.rules.filter((r) => r.id !== action.payload);
    },
    acknowledgeAlert: (state, action: PayloadAction<number>) => {
      const alert = state.alerts.find((a) => a.id === action.payload);
      if (alert) {
        alert.status = 'acknowledged';
        alert.acknowledgedAt = new Date().toISOString();
      }
    },
    resolveAlert: (state, action: PayloadAction<number>) => {
      const alert = state.alerts.find((a) => a.id === action.payload);
      if (alert) {
        alert.status = 'resolved';
        alert.resolvedAt = new Date().toISOString();
      }
    },
    setFilters: (state, action: PayloadAction<{ severity?: string; status?: string }>) => {
      state.filters = action.payload;
    },
    setError: (state, action: PayloadAction<string | null>) => {
      state.error = action.payload;
    },
  },
});

export const {
  setLoading,
  setAlerts,
  setRules,
  addAlert,
  addRule,
  updateRule,
  deleteRule,
  acknowledgeAlert,
  resolveAlert,
  setFilters,
  setError,
} = alertsSlice.actions;
export default alertsSlice.reducer;
