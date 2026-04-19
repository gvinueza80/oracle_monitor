import { configureStore } from '@reduxjs/toolkit';
import authReducer from './slices/authSlice';
import instanceReducer from './slices/instanceSlice';
import metricsReducer from './slices/metricsSlice';
import alertsReducer from './slices/alertsSlice';

export const store = configureStore({
  reducer: {
    auth: authReducer,
    instances: instanceReducer,
    metrics: metricsReducer,
    alerts: alertsReducer,
  },
});

export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;
