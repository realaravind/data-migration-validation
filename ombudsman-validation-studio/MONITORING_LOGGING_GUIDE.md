# Ombudsman Validation Studio - Monitoring & Logging Guide

**Version:** 1.0
**Date:** December 4, 2025
**Status:** Production Ready

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Monitoring Tools](#monitoring-tools)
3. [Logging Configuration](#logging-configuration)
4. [Health Checks](#health-checks)
5. [Performance Monitoring](#performance-monitoring)
6. [Alert Configuration](#alert-configuration)
7. [Troubleshooting](#troubleshooting)

---

## Quick Start

### Instant System Check

```bash
# Run monitoring script
./monitor.sh

# Continuous monitoring (updates every 5 seconds)
./monitor.sh --watch
```

### Quick Health Check

```bash
curl http://localhost:8000/health
# Expected: {"status":"ok"}
```

---

## Monitoring Tools

### 1. Built-in Monitoring Script

**monitor.sh** provides comprehensive system monitoring:

```bash
# Single check
./monitor.sh

# Output includes:
# - Backend health status
# - Container status and ports
# - CPU and memory usage
# - Recent logs (last 20 lines)
# - Data directory disk usage
# - API endpoint accessibility
```

**Continuous Monitoring:**
```bash
./monitor.sh --watch
# Updates every 5 seconds
# Press Ctrl+C to stop
```

### 2. Docker Native Tools

#### Container Status
```bash
# View running containers
docker-compose ps

# Expected output:
# NAME                                        STATUS
# ombudsman-validation-studio-studio-backend-1   Up X minutes
```

#### Resource Usage
```bash
# Live resource monitoring
docker stats

# View specific container
docker stats ombudsman-validation-studio-studio-backend-1

# One-time check
docker stats --no-stream
```

#### Container Inspection
```bash
# Detailed container info
docker inspect ombudsman-validation-studio-studio-backend-1

# Check health status
docker inspect --format='{{.State.Health.Status}}' \
    ombudsman-validation-studio-studio-backend-1
```

### 3. System Health Endpoints

#### Health Check Endpoint
```bash
# Simple health check
curl http://localhost:8000/health

# Verbose health check
curl -v http://localhost:8000/health

# With timing
curl -w "\nTime: %{time_total}s\n" http://localhost:8000/health
```

#### Feature Status
```bash
# Check all features
curl http://localhost:8000/features | python3 -m json.tool

# Count endpoints
curl -s http://localhost:8000/openapi.json | \
    python3 -c "import sys, json; print(len(json.load(sys.stdin)['paths']))"
```

---

## Logging Configuration

### 1. View Logs

#### Real-time Logs (Follow Mode)
```bash
# Follow all logs
docker-compose logs -f

# Follow backend only
docker-compose logs -f studio-backend

# Follow with timestamps
docker-compose logs -f -t studio-backend
```

#### Recent Logs
```bash
# Last 50 lines
docker-compose logs --tail=50 studio-backend

# Last 100 lines
docker logs --tail=100 ombudsman-validation-studio-studio-backend-1

# Since specific time
docker-compose logs --since 10m studio-backend  # Last 10 minutes
docker-compose logs --since 1h studio-backend   # Last 1 hour
docker-compose logs --since 2025-12-04T10:00:00 studio-backend
```

#### Search Logs
```bash
# Search for errors
docker-compose logs studio-backend | grep -i error

# Search for specific endpoint
docker-compose logs studio-backend | grep "/health"

# Count errors
docker-compose logs studio-backend | grep -c "ERROR"
```

### 2. Log Levels

The application uses Python's logging with these levels:
- **DEBUG:** Detailed information for diagnosing problems
- **INFO:** General informational messages
- **WARNING:** Warning messages for potential issues
- **ERROR:** Error messages for serious problems
- **CRITICAL:** Critical errors that may cause system failure

#### Current Log Configuration

Logs are configured in the FastAPI application:
- Console output (stdout/stderr)
- Captured by Docker
- Accessible via `docker logs`

### 3. Export Logs

#### Save Logs to File
```bash
# Export all logs
docker-compose logs > logs_$(date +%Y%m%d_%H%M%S).txt

# Export last 1000 lines
docker-compose logs --tail=1000 > recent_logs.txt

# Export with timestamps
docker-compose logs -t > logs_with_timestamps.txt
```

#### Compressed Log Archive
```bash
# Create compressed log archive
docker-compose logs | gzip > logs_$(date +%Y%m%d).log.gz

# View compressed logs
gunzip -c logs_20251204.log.gz | less
```

### 4. Log Rotation

For production deployments, configure log rotation:

**Create logrotate config (`/etc/logrotate.d/ombudsman`):**
```
/var/log/ombudsman/*.log {
    daily
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 root root
    sharedscripts
    postrotate
        docker-compose restart studio-backend > /dev/null
    endscript
}
```

**Manual log cleanup:**
```bash
# Remove logs older than 7 days
find backend/data/ -name "*.log" -mtime +7 -delete

# Archive old logs
find backend/data/ -name "*.log" -mtime +7 -exec gzip {} \;
```

---

## Health Checks

### 1. Application Health

#### HTTP Health Check
```bash
#!/bin/bash
# health_check.sh

HEALTH_URL="http://localhost:8000/health"
RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" $HEALTH_URL)

if [ "$RESPONSE" = "200" ]; then
    echo "✓ Backend is healthy"
    exit 0
else
    echo "✗ Backend health check failed (HTTP $RESPONSE)"
    exit 1
fi
```

#### Docker Health Check

Already configured in Dockerfile (if added):
```dockerfile
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1
```

### 2. Automated Health Monitoring

#### Cron Job for Health Checks
```bash
# Add to crontab (crontab -e)
*/5 * * * * /path/to/ombudsman-validation-studio/health_check.sh || \
    echo "Health check failed" | mail -s "Alert: Backend Down" admin@example.com
```

#### Systemd Service Monitor
```ini
# /etc/systemd/system/ombudsman-monitor.service
[Unit]
Description=Ombudsman Health Monitor
After=docker.service

[Service]
Type=simple
ExecStart=/usr/bin/watch -n 60 /path/to/health_check.sh
Restart=always

[Install]
WantedBy=multi-user.target
```

### 3. Performance Health Checks

#### Response Time Monitoring
```bash
# Check response time
curl -w "Response time: %{time_total}s\n" -o /dev/null -s http://localhost:8000/health

# Set threshold and alert
response_time=$(curl -w "%{time_total}" -o /dev/null -s http://localhost:8000/health)
threshold=2.0

if (( $(echo "$response_time > $threshold" | bc -l) )); then
    echo "⚠ Slow response: ${response_time}s (threshold: ${threshold}s)"
fi
```

---

## Performance Monitoring

### 1. Resource Metrics

#### CPU Usage
```bash
# Check CPU usage
docker stats --no-stream --format "{{.Container}}: {{.CPUPerc}}" \
    ombudsman-validation-studio-studio-backend-1

# Alert on high CPU
cpu_usage=$(docker stats --no-stream --format "{{.CPUPerc}}" \
    ombudsman-validation-studio-studio-backend-1 | sed 's/%//')
if (( $(echo "$cpu_usage > 80" | bc -l) )); then
    echo "⚠ High CPU usage: ${cpu_usage}%"
fi
```

#### Memory Usage
```bash
# Check memory usage
docker stats --no-stream --format "{{.Container}}: {{.MemUsage}}" \
    ombudsman-validation-studio-studio-backend-1

# Memory percentage
docker stats --no-stream --format "{{.MemPerc}}" \
    ombudsman-validation-studio-studio-backend-1
```

#### Network I/O
```bash
# Check network traffic
docker stats --no-stream --format "{{.Container}}: {{.NetIO}}" \
    ombudsman-validation-studio-studio-backend-1
```

#### Disk Usage
```bash
# Check data directory size
du -sh backend/data/

# Check by subdirectory
du -sh backend/data/*

# Alert on disk usage
usage=$(df -h backend/data/ | tail -1 | awk '{print $5}' | sed 's/%//')
if [ "$usage" -gt 80 ]; then
    echo "⚠ High disk usage: ${usage}%"
fi
```

### 2. Application Metrics

#### Request Metrics
```bash
# Count total requests (from logs)
docker-compose logs studio-backend | grep "GET\|POST\|PUT\|DELETE" | wc -l

# Requests by endpoint
docker-compose logs studio-backend | grep "GET /health" | wc -l

# Error rate
total=$(docker-compose logs studio-backend | grep -c "HTTP/")
errors=$(docker-compose logs studio-backend | grep -c "HTTP/[45]")
echo "Error rate: $((errors * 100 / total))%"
```

#### Response Time Analysis
```bash
# Extract response times from logs (if logged)
docker-compose logs studio-backend | \
    grep -oP 'completed in \K[0-9.]+(?=s)' | \
    awk '{sum+=$1; count++} END {print "Avg:", sum/count, "s"}'
```

### 3. Database Connection Monitoring

#### Check Active Connections
```bash
# Test SQL Server connection
curl -X POST http://localhost:8000/connections/sqlserver \
    -H "Content-Type: application/json"

# Test Snowflake connection
curl -X POST http://localhost:8000/connections/snowflake \
    -H "Content-Type: application/json"

# Get connection status
curl http://localhost:8000/connections/status
```

---

## Alert Configuration

### 1. Simple Email Alerts

```bash
#!/bin/bash
# alert.sh - Simple alerting script

ALERT_EMAIL="admin@example.com"

# Check health
if ! curl -s http://localhost:8000/health > /dev/null; then
    echo "Backend is down!" | mail -s "ALERT: Ombudsman Backend Down" $ALERT_EMAIL
fi

# Check CPU
cpu=$(docker stats --no-stream --format "{{.CPUPerc}}" \
    ombudsman-validation-studio-studio-backend-1 | sed 's/%//')
if (( $(echo "$cpu > 80" | bc -l) )); then
    echo "CPU usage is ${cpu}%" | mail -s "ALERT: High CPU Usage" $ALERT_EMAIL
fi

# Check memory
mem=$(docker stats --no-stream --format "{{.MemPerc}}" \
    ombudsman-validation-studio-studio-backend-1 | sed 's/%//')
if (( $(echo "$mem > 80" | bc -l) )); then
    echo "Memory usage is ${mem}%" | mail -s "ALERT: High Memory Usage" $ALERT_EMAIL
fi
```

### 2. Slack Alerts

```bash
#!/bin/bash
# slack_alert.sh

SLACK_WEBHOOK="https://hooks.slack.com/services/YOUR/WEBHOOK/URL"

send_alert() {
    local message="$1"
    curl -X POST -H 'Content-type: application/json' \
        --data "{\"text\":\"🚨 Ombudsman Alert: $message\"}" \
        $SLACK_WEBHOOK
}

# Check health and alert
if ! curl -s http://localhost:8000/health > /dev/null; then
    send_alert "Backend is down!"
fi
```

### 3. Alert Rules

Create alert rules based on thresholds:

```bash
# alert_rules.conf
CPU_THRESHOLD=80
MEMORY_THRESHOLD=80
DISK_THRESHOLD=85
RESPONSE_TIME_THRESHOLD=2.0
ERROR_RATE_THRESHOLD=5
```

---

## Troubleshooting

### 1. Backend Not Responding

**Check container status:**
```bash
docker-compose ps
```

**View recent logs:**
```bash
docker-compose logs --tail=50 studio-backend
```

**Restart backend:**
```bash
docker-compose restart studio-backend
```

### 2. High Resource Usage

**Identify resource-intensive processes:**
```bash
docker stats

# Check container processes
docker top ombudsman-validation-studio-studio-backend-1
```

**Limit resources:**
```yaml
# Add to docker-compose.yml
deploy:
  resources:
    limits:
      cpus: '2'
      memory: 4G
```

### 3. Log Analysis

**Find errors in logs:**
```bash
docker-compose logs studio-backend | grep -i "error\|exception\|failed"
```

**Analyze startup issues:**
```bash
docker logs ombudsman-validation-studio-studio-backend-1 --since 5m
```

### 4. Connection Issues

**Test from container:**
```bash
docker exec ombudsman-validation-studio-studio-backend-1 \
    curl http://localhost:8000/health
```

**Check network:**
```bash
docker network inspect ombudsman-validation-studio_ovs-net
```

---

## Advanced Monitoring

### 1. Prometheus + Grafana (Optional)

For production environments, consider integrating Prometheus and Grafana:

**Add prometheus exporter:**
```python
# In FastAPI app
from prometheus_fastapi_instrumentator import Instrumentator

Instrumentator().instrument(app).expose(app)
```

**docker-compose-monitoring.yml:**
```yaml
services:
  prometheus:
    image: prom/prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml

  grafana:
    image: grafana/grafana
    ports:
      - "3001:3000"
```

### 2. ELK Stack (Optional)

For centralized logging:

```yaml
services:
  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.11.0
    environment:
      - discovery.type=single-node

  logstash:
    image: docker.elastic.co/logstash/logstash:8.11.0

  kibana:
    image: docker.elastic.co/kibana/kibana:8.11.0
    ports:
      - "5601:5601"
```

---

## Monitoring Checklist

### Daily Checks
- [ ] Health endpoint responding
- [ ] No error spikes in logs
- [ ] Resource usage within limits
- [ ] Response times acceptable

### Weekly Checks
- [ ] Review error logs
- [ ] Check disk usage trends
- [ ] Analyze performance metrics
- [ ] Review security logs

### Monthly Checks
- [ ] Archive old logs
- [ ] Review and update alert thresholds
- [ ] Performance optimization review
- [ ] Capacity planning

---

## Quick Reference

### Monitoring Commands
```bash
# Quick health check
curl http://localhost:8000/health

# Run monitoring script
./monitor.sh

# Continuous monitoring
./monitor.sh --watch

# View live logs
docker-compose logs -f studio-backend

# Check resource usage
docker stats

# Export logs
docker-compose logs > logs.txt
```

### Log Locations
- **Container Logs:** `docker logs <container>`
- **Data Directories:** `backend/data/`
- **Query History:** `backend/data/query_history/`
- **Pipeline Runs:** `backend/data/pipeline_runs/`

### Key Metrics
- **Health:** http://localhost:8000/health
- **CPU:** `docker stats --format "{{.CPUPerc}}"`
- **Memory:** `docker stats --format "{{.MemUsage}}"`
- **Disk:** `du -sh backend/data/`

---

## Support

For monitoring issues:
1. Check `./monitor.sh` output
2. Review logs: `docker-compose logs studio-backend`
3. Verify health: `curl http://localhost:8000/health`
4. Check resources: `docker stats`

---

**Monitoring Guide Version:** 1.0
**Last Updated:** December 4, 2025
**Status:** ✅ Production Ready
