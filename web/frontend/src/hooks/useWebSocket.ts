import { useEffect, useState, useCallback } from 'react';

interface WebSocketMessage {
  type: string;
  [key: string]: any;
}

export const useWebSocket = (url: string, token: string) => {
  const [isConnected, setIsConnected] = useState(false);
  const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null);
  const [error, setError] = useState<Error | null>(null);

  const ws = useCallback(() => {
    const wsUrl = `${url}?token=${token}`;
    const socket = new WebSocket(wsUrl);

    socket.onopen = () => {
      setIsConnected(true);
      setError(null);
    };

    socket.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data);
        setLastMessage(message);
      } catch (e) {
        console.error('Failed to parse WebSocket message:', e);
      }
    };

    socket.onerror = (event) => {
      setError(new Error('WebSocket error'));
      setIsConnected(false);
    };

    socket.onclose = () => {
      setIsConnected(false);
    };

    return socket;
  }, [url, token]);

  useEffect(() => {
    const socket = ws();
    return () => {
      socket.close();
    };
  }, [ws]);

  return { isConnected, lastMessage, error };
};

export const useMetricUpdates = (instanceId: string, token: string) => {
  const wsUrl = `${process.env.REACT_APP_WS_URL || 'ws://localhost:8000'}/api/ws/metrics/${instanceId}`;
  return useWebSocket(wsUrl, token);
};
