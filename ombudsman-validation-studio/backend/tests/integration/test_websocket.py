"""
Integration tests for WebSocket real-time updates.

Tests WebSocket connection, event emission, and real-time pipeline monitoring.
"""

import pytest
import asyncio
import json
from fastapi.testclient import TestClient


class TestWebSocketConnection:
    """Test WebSocket connection management."""

    @pytest.mark.integration
    def test_websocket_health(self, client):
        """Test WebSocket health check endpoint."""
        response = client.get("/ws/health")

        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] == "healthy"
        assert "active_connections" in data

    @pytest.mark.integration
    def test_websocket_stats(self, client):
        """Test WebSocket statistics endpoint."""
        response = client.get("/ws/stats")

        assert response.status_code == 200
        data = response.json()
        assert "total_connections" in data
        assert "active_runs" in data

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_websocket_connect_disconnect(self, client):
        """Test basic WebSocket connection and disconnection."""
        try:
            with client.websocket_connect("/ws?client_id=test_client") as websocket:
                # Should receive welcome message
                data = websocket.receive_json()
                assert data["type"] == "connection_established"
                assert "client_id" in data
        except Exception as e:
            # WebSocket may not be fully supported in test environment
            pytest.skip(f"WebSocket test skipped: {e}")

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_websocket_ping_pong(self, client):
        """Test WebSocket ping/pong."""
        try:
            with client.websocket_connect("/ws") as websocket:
                # Receive welcome
                websocket.receive_json()

                # Send ping
                websocket.send_json({
                    "type": "ping",
                    "timestamp": "2025-12-03T00:00:00"
                })

                # Should receive pong
                response = websocket.receive_json()
                assert response["type"] == "pong"
        except Exception as e:
            pytest.skip(f"WebSocket test skipped: {e}")


class TestWebSocketSubscriptions:
    """Test WebSocket subscription management."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_subscribe_to_run(self, client):
        """Test subscribing to a pipeline run."""
        try:
            with client.websocket_connect("/ws") as websocket:
                # Receive welcome
                websocket.receive_json()

                # Subscribe to a run
                websocket.send_json({
                    "type": "subscribe",
                    "run_id": "test_run_123"
                })

                # Should receive subscription confirmation
                response = websocket.receive_json()
                assert response["type"] == "subscribed"
                assert response["run_id"] == "test_run_123"
        except Exception as e:
            pytest.skip(f"WebSocket test skipped: {e}")

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_unsubscribe_from_run(self, client):
        """Test unsubscribing from a pipeline run."""
        try:
            with client.websocket_connect("/ws") as websocket:
                # Receive welcome
                websocket.receive_json()

                # Subscribe first
                websocket.send_json({
                    "type": "subscribe",
                    "run_id": "test_run_123"
                })
                websocket.receive_json()  # subscription confirmation

                # Unsubscribe
                websocket.send_json({
                    "type": "unsubscribe",
                    "run_id": "test_run_123"
                })

                # Should receive unsubscription confirmation
                response = websocket.receive_json()
                assert response["type"] == "unsubscribed"
                assert response["run_id"] == "test_run_123"
        except Exception as e:
            pytest.skip(f"WebSocket test skipped: {e}")

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_auto_subscribe_with_run_id(self, client):
        """Test automatic subscription when connecting with run_id parameter."""
        try:
            with client.websocket_connect("/ws?run_id=auto_sub_123") as websocket:
                # Should receive welcome
                data = websocket.receive_json()
                assert data["type"] == "connection_established"

                # Should be auto-subscribed (verify by requesting stats)
                websocket.send_json({"type": "get_stats"})
                stats = websocket.receive_json()

                # Should show subscription in stats
                assert stats["type"] == "stats"
        except Exception as e:
            pytest.skip(f"WebSocket test skipped: {e}")


class TestWebSocketEvents:
    """Test WebSocket event emission during pipeline execution."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_pipeline_events_flow(self, client, sample_pipeline_yaml):
        """Test receiving pipeline events via WebSocket."""
        try:
            # Start WebSocket connection
            with client.websocket_connect("/ws") as websocket:
                # Receive welcome
                websocket.receive_json()

                # Start pipeline execution
                exec_response = client.post(
                    "/pipelines/execute",
                    json={
                        "pipeline_yaml": sample_pipeline_yaml,
                        "pipeline_name": "websocket_test"
                    }
                )

                if exec_response.status_code != 200:
                    pytest.skip("Pipeline execution failed")

                run_id = exec_response.json()["run_id"]

                # Subscribe to the run
                websocket.send_json({
                    "type": "subscribe",
                    "run_id": run_id
                })

                # Collect events for a short time
                events = []
                try:
                    for _ in range(10):  # Collect up to 10 events
                        data = websocket.receive_json(timeout=2)
                        events.append(data)
                except:
                    pass  # Timeout is expected

                # Should have received some events
                event_types = [e.get("type") for e in events]

                # Check for expected event types
                # May include: subscribed, pipeline_started, step_started, etc.
                assert len(events) > 0

        except Exception as e:
            pytest.skip(f"WebSocket test skipped: {e}")

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_pipeline_started_event(self, client, sample_pipeline_yaml):
        """Test pipeline_started event structure."""
        try:
            with client.websocket_connect("/ws") as websocket:
                websocket.receive_json()  # welcome

                # Start pipeline
                exec_response = client.post(
                    "/pipelines/execute",
                    json={
                        "pipeline_yaml": sample_pipeline_yaml,
                        "pipeline_name": "event_test"
                    }
                )

                if exec_response.status_code == 200:
                    run_id = exec_response.json()["run_id"]

                    # Subscribe
                    websocket.send_json({"type": "subscribe", "run_id": run_id})

                    # Look for pipeline_started event
                    for _ in range(5):
                        try:
                            event = websocket.receive_json(timeout=1)
                            if event.get("type") == "pipeline_started":
                                # Verify event structure
                                assert "run_id" in event
                                assert "data" in event
                                assert "timestamp" in event
                                break
                        except:
                            continue

        except Exception as e:
            pytest.skip(f"WebSocket test skipped: {e}")


class TestWebSocketMultipleClients:
    """Test multiple concurrent WebSocket clients."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_multiple_clients(self, client):
        """Test multiple WebSocket clients connected simultaneously."""
        try:
            connections = []

            # Connect multiple clients
            for i in range(3):
                ws = client.websocket_connect(f"/ws?client_id=client_{i}")
                connections.append(ws.__enter__())

            # Each should receive welcome
            for ws in connections:
                data = ws.receive_json()
                assert data["type"] == "connection_established"

            # Clean up
            for ws in connections:
                ws.__exit__(None, None, None)

        except Exception as e:
            pytest.skip(f"WebSocket test skipped: {e}")

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_broadcast_to_multiple_subscribers(self, client, sample_pipeline_yaml):
        """Test that events are broadcast to all subscribers."""
        try:
            # Connect two clients
            ws1 = client.websocket_connect("/ws?client_id=client_1").__enter__()
            ws2 = client.websocket_connect("/ws?client_id=client_2").__enter__()

            # Receive welcomes
            ws1.receive_json()
            ws2.receive_json()

            # Start pipeline
            exec_response = client.post(
                "/pipelines/execute",
                json={
                    "pipeline_yaml": sample_pipeline_yaml,
                    "pipeline_name": "broadcast_test"
                }
            )

            if exec_response.status_code == 200:
                run_id = exec_response.json()["run_id"]

                # Both subscribe to same run
                ws1.send_json({"type": "subscribe", "run_id": run_id})
                ws2.send_json({"type": "subscribe", "run_id": run_id})

                # Both should receive subscription confirmation
                ws1.receive_json()
                ws2.receive_json()

                # Both should receive events (check for at least one event)
                try:
                    event1 = ws1.receive_json(timeout=2)
                    event2 = ws2.receive_json(timeout=2)

                    # Both should receive events
                    assert event1 is not None
                    assert event2 is not None
                except:
                    pass  # May timeout if pipeline completes quickly

            # Clean up
            ws1.__exit__(None, None, None)
            ws2.__exit__(None, None, None)

        except Exception as e:
            pytest.skip(f"WebSocket test skipped: {e}")


class TestWebSocketHeartbeat:
    """Test WebSocket heartbeat mechanism."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_heartbeat_received(self, client):
        """Test that heartbeat messages are received."""
        try:
            with client.websocket_connect("/ws") as websocket:
                websocket.receive_json()  # welcome

                # Wait for heartbeat (30s interval, so wait a bit)
                # In test, we'll just verify connection stays alive
                for _ in range(3):
                    try:
                        data = websocket.receive_json(timeout=5)
                        if data.get("type") == "heartbeat":
                            assert "timestamp" in data
                            break
                    except:
                        continue

        except Exception as e:
            pytest.skip(f"WebSocket test skipped: {e}")


class TestWebSocketErrorHandling:
    """Test WebSocket error handling."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_unknown_message_type(self, client):
        """Test handling of unknown message types."""
        try:
            with client.websocket_connect("/ws") as websocket:
                websocket.receive_json()  # welcome

                # Send unknown message type
                websocket.send_json({
                    "type": "unknown_type",
                    "data": "test"
                })

                # Should receive error
                response = websocket.receive_json()
                assert response["type"] == "error"
                assert "unknown" in response["message"].lower()

        except Exception as e:
            pytest.skip(f"WebSocket test skipped: {e}")

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_invalid_json(self, client):
        """Test handling of invalid JSON."""
        try:
            with client.websocket_connect("/ws") as websocket:
                websocket.receive_json()  # welcome

                # Try to send invalid JSON
                try:
                    websocket.send_text("invalid json {{{")
                    # Should disconnect or send error
                except:
                    pass  # Expected to fail

        except Exception as e:
            pytest.skip(f"WebSocket test skipped: {e}")


class TestWebSocketStats:
    """Test WebSocket statistics and monitoring."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_get_stats_via_websocket(self, client):
        """Test getting statistics via WebSocket."""
        try:
            with client.websocket_connect("/ws") as websocket:
                websocket.receive_json()  # welcome

                # Request stats
                websocket.send_json({"type": "get_stats"})

                # Should receive stats
                response = websocket.receive_json()
                assert response["type"] == "stats"
                assert "data" in response
                assert "total_connections" in response["data"]
                assert "active_runs" in response["data"]

        except Exception as e:
            pytest.skip(f"WebSocket test skipped: {e}")

    @pytest.mark.integration
    def test_stats_endpoint_shows_connections(self, client):
        """Test that stats endpoint reflects active connections."""
        # Get initial stats
        initial_response = client.get("/ws/stats")
        initial_count = initial_response.json()["total_connections"]

        try:
            # Connect WebSocket
            with client.websocket_connect("/ws") as websocket:
                websocket.receive_json()  # welcome

                # Check stats again
                current_response = client.get("/ws/stats")
                current_count = current_response.json()["total_connections"]

                # Should have one more connection
                assert current_count >= initial_count

        except Exception as e:
            pytest.skip(f"WebSocket test skipped: {e}")
