import { useEffect, useRef, useState } from 'react';
import { WebSocketEvent } from '@/types/events';

export function useWebSocket(url: string) {
  const [isConnected, setIsConnected] = useState(false);
  const [events, setEvents] = useState<WebSocketEvent[]>([]);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    // Connect to WebSocket
    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => {
      console.log('WebSocket connected');
      setIsConnected(true);
    };

    ws.onmessage = (event) => {
      console.log('Received from backend:', event.data);
      try {
        const data = JSON.parse(event.data) as WebSocketEvent;
        setEvents((prev) => [...prev, data]);
      } catch (error) {
        console.error('Failed to parse WebSocket message:', error);
      }
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };

    ws.onclose = () => {
      console.log('WebSocket disconnected');
      setIsConnected(false);
    };

    // Cleanup on unmount
    return () => {
      ws.close();
    };
  }, [url]);

  const sendQuery = (query: string) => {
    if (wsRef.current && isConnected) {
      wsRef.current.send(JSON.stringify({ query }));
    }
  };

  return { isConnected, events, sendQuery };
}
