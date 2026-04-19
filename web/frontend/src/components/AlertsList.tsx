import React, { useEffect } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { RootState, AppDispatch } from '../store';
import { setAlerts, setLoading, acknowledgeAlert, resolveAlert } from '../store/slices/alertsSlice';
import api from '../services/api';

interface AlertsListProps {
  instanceId: string;
}

const AlertsList: React.FC<AlertsListProps> = ({ instanceId }) => {
  const dispatch = useDispatch<AppDispatch>();
  const { alerts, isLoading } = useSelector((state: RootState) => state.alerts);

  useEffect(() => {
    const fetchAlerts = async () => {
      dispatch(setLoading(true));
      try {
        const response = await api.getAlerts(instanceId);
        dispatch(setAlerts(response.data.alerts || []));
      } catch (error) {
        console.error('Error fetching alerts:', error);
      } finally {
        dispatch(setLoading(false));
      }
    };

    fetchAlerts();
    const interval = setInterval(fetchAlerts, 10000); // Refresh every 10 seconds
    return () => clearInterval(interval);
  }, [instanceId, dispatch]);

  const getSeverityColor = (severity: string): string => {
    switch (severity) {
      case 'critical':
        return 'bg-red-100 text-red-800';
      case 'warning':
        return 'bg-yellow-100 text-yellow-800';
      default:
        return 'bg-blue-100 text-blue-800';
    }
  };

  const getStatusIcon = (status: string): string => {
    switch (status) {
      case 'triggered':
        return '🔴';
      case 'acknowledged':
        return '🟡';
      case 'resolved':
        return '🟢';
      default:
        return '⚪';
    }
  };

  const handleAcknowledge = (alertId: number) => {
    dispatch(acknowledgeAlert(alertId));
    api.acknowledgeAlert(alertId).catch((error) => {
      console.error('Error acknowledging alert:', error);
    });
  };

  const handleResolve = (alertId: number) => {
    dispatch(resolveAlert(alertId));
    api.resolveAlert(alertId).catch((error) => {
      console.error('Error resolving alert:', error);
    });
  };

  if (isLoading) {
    return (
      <div className="p-6 text-center text-gray-600">
        <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-500 mx-auto"></div>
      </div>
    );
  }

  if (alerts.length === 0) {
    return (
      <div className="p-6 text-center text-gray-600">
        No alerts at this time
      </div>
    );
  }

  return (
    <div className="overflow-hidden">
      <table className="w-full">
        <thead className="bg-gray-50">
          <tr>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-700 uppercase">
              Status
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-700 uppercase">
              Time
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-700 uppercase">
              Message
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-700 uppercase">
              Value
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-700 uppercase">
              Actions
            </th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-200">
          {alerts.map((alert) => (
            <tr key={alert.id} className="hover:bg-gray-50">
              <td className="px-6 py-4 whitespace-nowrap">
                <div className="flex items-center gap-2">
                  <span className="text-xl">{getStatusIcon(alert.status)}</span>
                  <span className="text-sm text-gray-600">{alert.status}</span>
                </div>
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">
                {new Date(alert.triggeredAt).toLocaleTimeString()}
              </td>
              <td className="px-6 py-4 text-sm text-gray-900 max-w-xs truncate">
                {alert.message || 'No message'}
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                {alert.metricValue} {alert.metricUnit}
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-sm">
                {alert.status === 'triggered' && (
                  <>
                    <button
                      onClick={() => handleAcknowledge(alert.id)}
                      className="text-blue-600 hover:text-blue-900 mr-4"
                    >
                      Acknowledge
                    </button>
                    <button
                      onClick={() => handleResolve(alert.id)}
                      className="text-green-600 hover:text-green-900"
                    >
                      Resolve
                    </button>
                  </>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

export default AlertsList;
