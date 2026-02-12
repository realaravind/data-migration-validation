/**
 * WebSocket hook for real-time batch job updates.
 *
 * Usage:
 *   const { connected, lastUpdate, reconnect } = useJobWebSocket(projectId, onJobUpdate);
 */

import { useState, useEffect, useRef, useCallback } from 'react';

interface JobUpdate {
    type: string;
    timestamp: string;
    data: {
        job_id: string;
        status?: string;
        name?: string;
        event?: string;
        progress?: {
            percent_complete: number;
            completed_operations: number;
            failed_operations: number;
        };
    };
}

interface UseJobWebSocketResult {
    connected: boolean;
    lastUpdate: JobUpdate | null;
    reconnect: () => void;
}

export function useJobWebSocket(
    projectId: string | null,
    onJobUpdate?: (update: JobUpdate) => void
): UseJobWebSocketResult {
    const [connected, setConnected] = useState(false);
    const [lastUpdate, setLastUpdate] = useState<JobUpdate | null>(null);
    const wsRef = useRef<WebSocket | null>(null);
    const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
    const reconnectAttempts = useRef(0);

    const connect = useCallback(() => {
        if (wsRef.current?.readyState === WebSocket.OPEN) {
            return; // Already connected
        }

        // Build WebSocket URL
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const host = window.location.hostname;
        const port = __API_URL__.match(/:(\d+)/)?.[1] || '8000';
        const wsPath = projectId ? `/batch/ws/${projectId}` : '/batch/ws';
        const wsUrl = `${protocol}//${host}:${port}${wsPath}`;

        console.log('[WebSocket] Connecting to:', wsUrl);

        try {
            const ws = new WebSocket(wsUrl);
            wsRef.current = ws;

            ws.onopen = () => {
                console.log('[WebSocket] Connected');
                setConnected(true);
                reconnectAttempts.current = 0;
            };

            ws.onmessage = (event) => {
                // Ignore ping/pong messages
                if (event.data === 'pong' || event.data === 'ping') {
                    return;
                }
                try {
                    const update = JSON.parse(event.data) as JobUpdate;
                    setLastUpdate(update);
                    onJobUpdate?.(update);
                } catch (e) {
                    console.warn('[WebSocket] Failed to parse message:', e);
                }
            };

            ws.onerror = (error) => {
                console.error('[WebSocket] Error:', error);
            };

            ws.onclose = (event) => {
                console.log('[WebSocket] Closed:', event.code, event.reason);
                setConnected(false);
                wsRef.current = null;

                // Auto-reconnect with exponential backoff
                if (reconnectAttempts.current < 5) {
                    const delay = Math.min(1000 * Math.pow(2, reconnectAttempts.current), 30000);
                    console.log(`[WebSocket] Reconnecting in ${delay}ms...`);
                    reconnectTimeoutRef.current = setTimeout(() => {
                        reconnectAttempts.current++;
                        connect();
                    }, delay);
                }
            };

            // Send ping every 30 seconds to keep connection alive
            const pingInterval = setInterval(() => {
                if (ws.readyState === WebSocket.OPEN) {
                    ws.send('ping');
                }
            }, 30000);

            // Store cleanup function
            ws.addEventListener('close', () => clearInterval(pingInterval));

        } catch (e) {
            console.error('[WebSocket] Failed to connect:', e);
        }
    }, [projectId, onJobUpdate]);

    const reconnect = useCallback(() => {
        // Close existing connection
        if (wsRef.current) {
            wsRef.current.close();
            wsRef.current = null;
        }
        // Clear reconnect timeout
        if (reconnectTimeoutRef.current) {
            clearTimeout(reconnectTimeoutRef.current);
        }
        // Reset attempts and connect
        reconnectAttempts.current = 0;
        connect();
    }, [connect]);

    // Connect on mount and when projectId changes
    useEffect(() => {
        connect();

        return () => {
            // Cleanup on unmount
            if (reconnectTimeoutRef.current) {
                clearTimeout(reconnectTimeoutRef.current);
            }
            if (wsRef.current) {
                wsRef.current.close();
                wsRef.current = null;
            }
        };
    }, [connect]);

    return { connected, lastUpdate, reconnect };
}

// Declare API URL for TypeScript
declare const __API_URL__: string;
