import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useDispatch } from 'react-redux';
import { AppDispatch } from '../store';
import { logout } from '../store/slices/authSlice';
import api from '../services/api';

const SettingsPage: React.FC = () => {
  const navigate = useNavigate();
  const dispatch = useDispatch<AppDispatch>();
  const [instances, setInstances] = useState<any[]>([]);
  const [showAddInstance, setShowAddInstance] = useState(false);
  const [newInstance, setNewInstance] = useState({
    name: '',
    host: '',
    port: 1521,
    service_name: '',
    username: '',
    password: '',
  });
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');

  useEffect(() => {
    fetchInstances();
  }, []);

  const fetchInstances = async () => {
    try {
      const response = await api.getInstances();
      setInstances(response.data.instances || []);
    } catch (error) {
      console.error('Error fetching instances:', error);
    }
  };

  const handleAddInstance = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setMessage('');

    try {
      await api.createInstance(newInstance);
      setMessage('Instance added successfully');
      setNewInstance({
        name: '',
        host: '',
        port: 1521,
        service_name: '',
        username: '',
        password: '',
      });
      setShowAddInstance(false);
      fetchInstances();
    } catch (error: any) {
      setMessage(error.response?.data?.detail || 'Error adding instance');
    } finally {
      setLoading(false);
    }
  };

  const handleTestConnection = async (instanceId: string) => {
    try {
      await api.testConnection(instanceId);
      setMessage('Connection successful');
    } catch (error: any) {
      setMessage(error.response?.data?.detail || 'Connection failed');
    }
  };

  const handleDeleteInstance = async (instanceId: string) => {
    if (window.confirm('Are you sure you want to delete this instance?')) {
      try {
        await api.deleteInstance(instanceId);
        setMessage('Instance deleted successfully');
        fetchInstances();
      } catch (error: any) {
        setMessage(error.response?.data?.detail || 'Error deleting instance');
      }
    }
  };

  const handleLogout = async () => {
    try {
      await api.logout();
    } catch (error) {
      console.error('Logout error:', error);
    }
    dispatch(logout());
    navigate('/login');
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="bg-white shadow">
        <div className="max-w-7xl mx-auto px-4 py-6">
          <h1 className="text-3xl font-bold text-gray-900">Settings</h1>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 py-8">
        {message && (
          <div className="mb-6 p-4 bg-blue-50 border border-blue-200 rounded text-blue-700">
            {message}
          </div>
        )}

        {/* Instances Management */}
        <div className="bg-white rounded-lg shadow mb-8">
          <div className="p-6 border-b border-gray-200">
            <div className="flex justify-between items-center">
              <h2 className="text-lg font-semibold text-gray-900">Database Instances</h2>
              <button
                onClick={() => setShowAddInstance(!showAddInstance)}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
              >
                {showAddInstance ? 'Cancel' : 'Add Instance'}
              </button>
            </div>
          </div>

          {showAddInstance && (
            <form onSubmit={handleAddInstance} className="p-6 border-b border-gray-200">
              <div className="grid grid-cols-2 gap-4">
                <input
                  type="text"
                  placeholder="Instance Name"
                  value={newInstance.name}
                  onChange={(e) => setNewInstance({ ...newInstance, name: e.target.value })}
                  className="col-span-2 px-4 py-2 border border-gray-300 rounded-lg"
                  required
                />
                <input
                  type="text"
                  placeholder="Host"
                  value={newInstance.host}
                  onChange={(e) => setNewInstance({ ...newInstance, host: e.target.value })}
                  className="px-4 py-2 border border-gray-300 rounded-lg"
                  required
                />
                <input
                  type="number"
                  placeholder="Port"
                  value={newInstance.port}
                  onChange={(e) => setNewInstance({ ...newInstance, port: parseInt(e.target.value) })}
                  className="px-4 py-2 border border-gray-300 rounded-lg"
                  required
                />
                <input
                  type="text"
                  placeholder="Service Name"
                  value={newInstance.service_name}
                  onChange={(e) => setNewInstance({ ...newInstance, service_name: e.target.value })}
                  className="col-span-2 px-4 py-2 border border-gray-300 rounded-lg"
                  required
                />
                <input
                  type="text"
                  placeholder="Username"
                  value={newInstance.username}
                  onChange={(e) => setNewInstance({ ...newInstance, username: e.target.value })}
                  className="px-4 py-2 border border-gray-300 rounded-lg"
                  required
                />
                <input
                  type="password"
                  placeholder="Password"
                  value={newInstance.password}
                  onChange={(e) => setNewInstance({ ...newInstance, password: e.target.value })}
                  className="px-4 py-2 border border-gray-300 rounded-lg"
                  required
                />
              </div>
              <button
                type="submit"
                disabled={loading}
                className="mt-4 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50"
              >
                {loading ? 'Adding...' : 'Add Instance'}
              </button>
            </form>
          )}

          <div className="overflow-hidden">
            <table className="w-full">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-700 uppercase">
                    Name
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-700 uppercase">
                    Host
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-700 uppercase">
                    Status
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-700 uppercase">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {instances.map((instance) => (
                  <tr key={instance.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap font-medium text-gray-900">
                      {instance.name}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-gray-600">
                      {instance.host}:{instance.port}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span
                        className={`px-3 py-1 rounded-full text-xs font-medium ${
                          instance.connection_status === 'connected'
                            ? 'bg-green-100 text-green-800'
                            : 'bg-gray-100 text-gray-800'
                        }`}
                      >
                        {instance.connection_status || 'Unknown'}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm">
                      <button
                        onClick={() => handleTestConnection(instance.id)}
                        className="text-blue-600 hover:text-blue-900 mr-4"
                      >
                        Test
                      </button>
                      <button
                        onClick={() => handleDeleteInstance(instance.id)}
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
        </div>

        {/* Account Settings */}
        <div className="bg-white rounded-lg shadow">
          <div className="p-6 border-b border-gray-200">
            <h2 className="text-lg font-semibold text-gray-900">Account</h2>
          </div>
          <div className="p-6">
            <button
              onClick={handleLogout}
              className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700"
            >
              Logout
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default SettingsPage;
