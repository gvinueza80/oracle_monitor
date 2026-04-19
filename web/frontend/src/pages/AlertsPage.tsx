import React, { useState, useEffect } from 'react';
import { useSelector } from 'react-redux';
import { RootState } from '../store';
import api from '../services/api';

const AlertsPage: React.FC = () => {
  const { selectedInstanceId } = useSelector((state: RootState) => state.instances);
  const [alerts, setAlerts] = useState<any[]>([]);
  const [rules, setRules] = useState<any[]>([]);
  const [activeTab, setActiveTab] = useState<'alerts' | 'rules'>('alerts');
  const [loading, setLoading] = useState(false);
  const [showNewRule, setShowNewRule] = useState(false);
  const [newRule, setNewRule] = useState({
    name: '',
    metric_type: 'cpu_usage',
    threshold: 85,
    condition: 'gt',
    severity: 'warning',
  });

  useEffect(() => {
    if (!selectedInstanceId) return;

    const fetchData = async () => {
      setLoading(true);
      try {
        const [alertsResp, rulesResp] = await Promise.all([
          api.getAlerts(selectedInstanceId),
          api.getAlertRules(selectedInstanceId),
        ]);
        setAlerts(alertsResp.data.alerts || []);
        setRules(rulesResp.data.rules || []);
      } catch (error) {
        console.error('Error fetching data:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [selectedInstanceId]);

  const handleCreateRule = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedInstanceId) return;

    try {
      await api.createAlertRule(selectedInstanceId, newRule);
      setNewRule({
        name: '',
        metric_type: 'cpu_usage',
        threshold: 85,
        condition: 'gt',
        severity: 'warning',
      });
      setShowNewRule(false);
      // Refetch rules
      const rulesResp = await api.getAlertRules(selectedInstanceId);
      setRules(rulesResp.data.rules || []);
    } catch (error) {
      console.error('Error creating rule:', error);
    }
  };

  const handleDeleteRule = async (ruleId: string) => {
    if (window.confirm('Are you sure you want to delete this rule?')) {
      try {
        await api.deleteAlertRule(ruleId);
        setRules(rules.filter((r) => r.id !== ruleId));
      } catch (error) {
        console.error('Error deleting rule:', error);
      }
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="bg-white shadow">
        <div className="max-w-7xl mx-auto px-4 py-6">
          <h1 className="text-3xl font-bold text-gray-900">Alerts</h1>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 py-8">
        {!selectedInstanceId ? (
          <div className="bg-white rounded-lg shadow p-12 text-center">
            <p className="text-gray-600">Select an instance to view alerts</p>
          </div>
        ) : (
          <>
            {/* Tabs */}
            <div className="mb-6 border-b border-gray-200">
              <button
                onClick={() => setActiveTab('alerts')}
                className={`mr-8 py-4 font-medium ${
                  activeTab === 'alerts'
                    ? 'text-blue-600 border-b-2 border-blue-600'
                    : 'text-gray-600 hover:text-gray-900'
                }`}
              >
                Alert History
              </button>
              <button
                onClick={() => setActiveTab('rules')}
                className={`py-4 font-medium ${
                  activeTab === 'rules'
                    ? 'text-blue-600 border-b-2 border-blue-600'
                    : 'text-gray-600 hover:text-gray-900'
                }`}
              >
                Rules ({rules.length})
              </button>
            </div>

            {/* Alerts Tab */}
            {activeTab === 'alerts' && (
              <div className="bg-white rounded-lg shadow">
                {loading ? (
                  <div className="p-6 text-center">
                    <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-500 mx-auto"></div>
                  </div>
                ) : alerts.length === 0 ? (
                  <div className="p-6 text-center text-gray-600">No alerts</div>
                ) : (
                  <div className="overflow-hidden">
                    <table className="w-full">
                      <thead className="bg-gray-50">
                        <tr>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-700 uppercase">
                            Time
                          </th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-700 uppercase">
                            Message
                          </th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-700 uppercase">
                            Status
                          </th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-700 uppercase">
                            Value
                          </th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-gray-200">
                        {alerts.map((alert) => (
                          <tr key={alert.id} className="hover:bg-gray-50">
                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                              {new Date(alert.triggered_at).toLocaleString()}
                            </td>
                            <td className="px-6 py-4 text-sm text-gray-600">
                              {alert.message}
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap">
                              <span
                                className={`px-3 py-1 rounded-full text-xs font-medium ${
                                  alert.status === 'triggered'
                                    ? 'bg-red-100 text-red-800'
                                    : alert.status === 'acknowledged'
                                    ? 'bg-yellow-100 text-yellow-800'
                                    : 'bg-green-100 text-green-800'
                                }`}
                              >
                                {alert.status}
                              </span>
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                              {alert.metric_value} {alert.metric_unit}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            )}

            {/* Rules Tab */}
            {activeTab === 'rules' && (
              <div className="bg-white rounded-lg shadow">
                <div className="p-6 border-b border-gray-200">
                  <button
                    onClick={() => setShowNewRule(!showNewRule)}
                    className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
                  >
                    {showNewRule ? 'Cancel' : 'New Rule'}
                  </button>
                </div>

                {showNewRule && (
                  <form onSubmit={handleCreateRule} className="p-6 border-b border-gray-200">
                    <div className="grid grid-cols-2 gap-4">
                      <input
                        type="text"
                        placeholder="Rule Name"
                        value={newRule.name}
                        onChange={(e) => setNewRule({ ...newRule, name: e.target.value })}
                        className="col-span-2 px-4 py-2 border border-gray-300 rounded-lg"
                        required
                      />
                      <select
                        value={newRule.metric_type}
                        onChange={(e) => setNewRule({ ...newRule, metric_type: e.target.value })}
                        className="px-4 py-2 border border-gray-300 rounded-lg"
                      >
                        <option value="cpu_usage">CPU Usage</option>
                        <option value="memory_shared_pool_mb">Memory</option>
                        <option value="tablespace_usage">Tablespace</option>
                        <option value="sessions">Active Sessions</option>
                      </select>
                      <input
                        type="number"
                        placeholder="Threshold"
                        value={newRule.threshold}
                        onChange={(e) =>
                          setNewRule({ ...newRule, threshold: parseFloat(e.target.value) })
                        }
                        className="px-4 py-2 border border-gray-300 rounded-lg"
                        required
                      />
                      <select
                        value={newRule.condition}
                        onChange={(e) => setNewRule({ ...newRule, condition: e.target.value })}
                        className="px-4 py-2 border border-gray-300 rounded-lg"
                      >
                        <option value="gt">Greater Than</option>
                        <option value="lt">Less Than</option>
                        <option value="eq">Equal To</option>
                      </select>
                      <select
                        value={newRule.severity}
                        onChange={(e) => setNewRule({ ...newRule, severity: e.target.value })}
                        className="col-span-2 px-4 py-2 border border-gray-300 rounded-lg"
                      >
                        <option value="info">Info</option>
                        <option value="warning">Warning</option>
                        <option value="critical">Critical</option>
                      </select>
                    </div>
                    <button
                      type="submit"
                      className="mt-4 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700"
                    >
                      Create Rule
                    </button>
                  </form>
                )}

                {rules.length === 0 ? (
                  <div className="p-6 text-center text-gray-600">No rules configured</div>
                ) : (
                  <div className="overflow-hidden">
                    <table className="w-full">
                      <thead className="bg-gray-50">
                        <tr>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-700 uppercase">
                            Name
                          </th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-700 uppercase">
                            Metric
                          </th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-700 uppercase">
                            Condition
                          </th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-700 uppercase">
                            Severity
                          </th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-700 uppercase">
                            Actions
                          </th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-gray-200">
                        {rules.map((rule) => (
                          <tr key={rule.id} className="hover:bg-gray-50">
                            <td className="px-6 py-4 whitespace-nowrap font-medium text-gray-900">
                              {rule.name}
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-gray-600">
                              {rule.metric_type}
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-gray-600">
                              {rule.condition} {rule.threshold}
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap">
                              <span
                                className={`px-3 py-1 rounded-full text-xs font-medium ${
                                  rule.severity === 'critical'
                                    ? 'bg-red-100 text-red-800'
                                    : rule.severity === 'warning'
                                    ? 'bg-yellow-100 text-yellow-800'
                                    : 'bg-blue-100 text-blue-800'
                                }`}
                              >
                                {rule.severity}
                              </span>
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm">
                              <button
                                onClick={() => handleDeleteRule(rule.id)}
                                className="text-red-600 hover:text-red-900"
                              >
                                Delete
                              </button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
};

export default AlertsPage;
