import React, { useEffect, useState } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { RootState, AppDispatch } from '../store';
import {
  setLoading,
  setOverviewMetrics,
  setError,
} from '../store/slices/metricsSlice';
import { selectInstance } from '../store/slices/instanceSlice';
import api from '../services/api';
import MetricCard from './MetricCard';
import AlertsList from './AlertsList';
import InstanceSelector from './InstanceSelector';
import MetricChart from './MetricChart';
import { useMetricUpdates } from '../hooks/useWebSocket';

const Dashboard: React.FC = () => {
  const dispatch = useDispatch<AppDispatch>();
  const { overview, isLoading } = useSelector((state: RootState) => state.metrics);
  const { instances, selectedInstanceId } = useSelector((state: RootState) => state.instances);
  const { accessToken } = useSelector((state: RootState) => state.auth);
  const { isConnected } = useMetricUpdates(selectedInstanceId || '', accessToken || '');

  const [refreshInterval, setRefreshInterval] = useState(30000); // 30 seconds

  useEffect(() => {
    if (!selectedInstanceId) return;

    const fetchMetrics = async () => {
      dispatch(setLoading(true));
      try {
        const response = await api.getOverviewMetrics(selectedInstanceId);
        dispatch(setOverviewMetrics(response.data));
        dispatch(setError(null));
      } catch (error) {
        dispatch(setError('Failed to fetch metrics'));
        console.error('Error fetching metrics:', error);
      } finally {
        dispatch(setLoading(false));
      }
    };

    fetchMetrics();
    const interval = setInterval(fetchMetrics, refreshInterval);
    return () => clearInterval(interval);
  }, [selectedInstanceId, dispatch, refreshInterval]);

  const getHealthColor = (status: string): string => {
    switch (status) {
      case 'healthy':
        return 'text-green-600';
      case 'degraded':
        return 'text-yellow-600';
      case 'critical':
        return 'text-red-600';
      default:
        return 'text-gray-600';
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white shadow">
        <div className="max-w-7xl mx-auto px-4 py-6">
          <div className="flex justify-between items-center">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">Oracle Monitor</h1>
              <p className="text-gray-600 mt-1">Real-time database monitoring</p>
            </div>
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-2">
                <div className={`w-3 h-3 rounded-full ${isConnected ? 'bg-green-500' : 'bg-gray-400'}`} />
                <span className="text-sm text-gray-600">
                  {isConnected ? 'Connected' : 'Disconnected'}
                </span>
              </div>
              <select
                onChange={(e) => dispatch(selectInstance(e.target.value))}
                value={selectedInstanceId || ''}
                className="px-4 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="">Select Instance</option>
                {instances.map((instance) => (
                  <option key={instance.id} value={instance.id}>
                    {instance.name}
                  </option>
                ))}
              </select>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-4 py-8">
        {selectedInstanceId && overview ? (
          <>
            {/* Health Status */}
            <div className="mb-8">
              <div className="bg-white rounded-lg shadow p-6">
                <div className="flex justify-between items-center">
                  <div>
                    <h2 className="text-lg font-semibold text-gray-900">Instance Health</h2>
                    <p className="text-gray-600 mt-1">Last updated: {new Date(overview.lastUpdate).toLocaleTimeString()}</p>
                  </div>
                  <div className={`text-4xl font-bold ${getHealthColor(overview.instanceHealthStatus)}`}>
                    {overview.instanceHealthStatus.charAt(0).toUpperCase() +
                      overview.instanceHealthStatus.slice(1)}
                  </div>
                </div>
              </div>
            </div>

            {/* KPI Cards */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
              <MetricCard
                title="Active Sessions"
                value={overview.activeSessions}
                unit="sessions"
                icon="👥"
                trend={overview.activeSessions > 200 ? 'warning' : 'normal'}
              />
              <MetricCard
                title="Locks"
                value={overview.lockedSessions}
                unit="locks"
                icon="🔒"
                trend={overview.lockedSessions > 0 ? 'warning' : 'normal'}
              />
              <MetricCard
                title="Tablespace"
                value={overview.tablespaceUsedPercent}
                unit="%"
                icon="💾"
                trend={overview.tablespaceUsedPercent > 80 ? 'warning' : 'normal'}
              />
              <MetricCard
                title="Slow Queries"
                value={overview.slowQueriesCount}
                unit="queries"
                icon="⏱️"
                trend={overview.slowQueriesCount > 5 ? 'warning' : 'normal'}
              />
            </div>

            {/* Alerts Section */}
            <div className="mb-8">
              <div className="bg-white rounded-lg shadow">
                <div className="p-6 border-b border-gray-200">
                  <h2 className="text-lg font-semibold text-gray-900">Recent Alerts</h2>
                </div>
                <AlertsList instanceId={selectedInstanceId} />
              </div>
            </div>

            {/* Charts Section */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
              <div className="bg-white rounded-lg shadow p-6">
                <h3 className="text-lg font-semibold text-gray-900 mb-4">CPU Usage</h3>
                <MetricChart metricType="cpu_usage" instanceId={selectedInstanceId} />
              </div>
              <div className="bg-white rounded-lg shadow p-6">
                <h3 className="text-lg font-semibold text-gray-900 mb-4">Memory Usage</h3>
                <MetricChart metricType="memory_shared_pool_mb" instanceId={selectedInstanceId} />
              </div>
            </div>
          </>
        ) : (
          <div className="bg-white rounded-lg shadow p-12 text-center">
            <p className="text-gray-600">Select an instance to view metrics</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default Dashboard;
