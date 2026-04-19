import React, { useEffect } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { RootState, AppDispatch } from '../store';
import { setInstances, selectInstance } from '../store/slices/instanceSlice';
import api from '../services/api';

const InstanceSelector: React.FC = () => {
  const dispatch = useDispatch<AppDispatch>();
  const { instances, selectedInstanceId } = useSelector((state: RootState) => state.instances);

  useEffect(() => {
    const fetchInstances = async () => {
      try {
        const response = await api.getInstances();
        dispatch(setInstances(response.data.instances || []));
        if (response.data.instances && response.data.instances.length > 0) {
          dispatch(selectInstance(response.data.instances[0].id));
        }
      } catch (error) {
        console.error('Error fetching instances:', error);
      }
    };

    fetchInstances();
  }, [dispatch]);

  return (
    <div className="flex items-center gap-2">
      <label className="text-sm font-medium text-gray-700">Instance:</label>
      <select
        value={selectedInstanceId || ''}
        onChange={(e) => dispatch(selectInstance(e.target.value))}
        className="px-4 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
      >
        <option value="">Select an instance</option>
        {instances.map((instance) => (
          <option key={instance.id} value={instance.id}>
            {instance.name} ({instance.host}:{instance.port})
          </option>
        ))}
      </select>
    </div>
  );
};

export default InstanceSelector;
