import React, { useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { useDispatch, useSelector } from 'react-redux';
import { RootState, AppDispatch } from './store';
import { setInstances } from './store/slices/instanceSlice';
import api from './services/api';
import LoginPage from './pages/LoginPage';
import Dashboard from './components/Dashboard';
import AlertsPage from './pages/AlertsPage';
import SettingsPage from './pages/SettingsPage';

const ProtectedRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { accessToken } = useSelector((state: RootState) => state.auth);
  return accessToken ? <>{children}</> : <Navigate to="/login" />;
};

const App: React.FC = () => {
  const dispatch = useDispatch<AppDispatch>();
  const { accessToken } = useSelector((state: RootState) => state.auth);

  useEffect(() => {
    if (accessToken) {
      const fetchInstances = async () => {
        try {
          const response = await api.getInstances();
          dispatch(setInstances(response.data.instances || []));
        } catch (error) {
          console.error('Error fetching instances:', error);
        }
      };

      fetchInstances();
    }
  }, [accessToken, dispatch]);

  return (
    <Router>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route
          path="/dashboard"
          element={
            <ProtectedRoute>
              <Dashboard />
            </ProtectedRoute>
          }
        />
        <Route
          path="/alerts"
          element={
            <ProtectedRoute>
              <AlertsPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/settings"
          element={
            <ProtectedRoute>
              <SettingsPage />
            </ProtectedRoute>
          }
        />
        <Route path="/" element={<Navigate to="/dashboard" />} />
      </Routes>
    </Router>
  );
};

export default App;
