"""API endpoints for viewing application logs."""

import os
import json
from pathlib import Path
from typing import Optional, List
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from .config import LOG_FILE, LOG_DIR

router = APIRouter()


class LogEntry(BaseModel):
    """Log entry model."""
    timestamp: str
    level: str
    logger: str
    message: str
    module: Optional[str] = None
    function: Optional[str] = None
    line: Optional[int] = None
    exception: Optional[str] = None
    user_id: Optional[str] = None
    project_id: Optional[str] = None
    action: Optional[str] = None


class LogResponse(BaseModel):
    """Response model for log queries."""
    logs: List[LogEntry]
    total: int
    page: int
    page_size: int
    has_more: bool


@router.get("/")
async def get_logs(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(100, ge=1, le=1000, description="Logs per page"),
    level: Optional[str] = Query(None, description="Filter by log level"),
    logger: Optional[str] = Query(None, description="Filter by logger name"),
    search: Optional[str] = Query(None, description="Search in message"),
    since: Optional[str] = Query(None, description="ISO timestamp - logs after this time"),
    until: Optional[str] = Query(None, description="ISO timestamp - logs before this time"),
):
    """Get application logs with pagination and filtering."""

    if not LOG_FILE.exists():
        return LogResponse(logs=[], total=0, page=page, page_size=page_size, has_more=False)

    logs = []
    try:
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)

                    # Apply filters
                    if level and entry.get("level", "").upper() != level.upper():
                        continue
                    if logger and logger.lower() not in entry.get("logger", "").lower():
                        continue
                    if search and search.lower() not in entry.get("message", "").lower():
                        continue
                    if since:
                        log_time = entry.get("timestamp", "")
                        if log_time < since:
                            continue
                    if until:
                        log_time = entry.get("timestamp", "")
                        if log_time > until:
                            continue

                    logs.append(LogEntry(**entry))
                except json.JSONDecodeError:
                    # Skip non-JSON lines
                    continue
                except Exception:
                    continue

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read logs: {str(e)}")

    # Sort by timestamp descending (newest first)
    logs.sort(key=lambda x: x.timestamp, reverse=True)

    # Paginate
    total = len(logs)
    start = (page - 1) * page_size
    end = start + page_size
    page_logs = logs[start:end]
    has_more = end < total

    return LogResponse(
        logs=page_logs,
        total=total,
        page=page,
        page_size=page_size,
        has_more=has_more
    )


@router.get("/levels")
async def get_log_levels():
    """Get available log levels and their counts."""

    if not LOG_FILE.exists():
        return {"levels": {}}

    levels = {}
    try:
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    entry = json.loads(line.strip())
                    level = entry.get("level", "UNKNOWN")
                    levels[level] = levels.get(level, 0) + 1
                except:
                    continue
    except:
        pass

    return {"levels": levels}


@router.get("/loggers")
async def get_loggers():
    """Get list of unique logger names."""

    if not LOG_FILE.exists():
        return {"loggers": []}

    loggers = set()
    try:
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    entry = json.loads(line.strip())
                    logger = entry.get("logger", "")
                    if logger:
                        loggers.add(logger)
                except:
                    continue
    except:
        pass

    return {"loggers": sorted(loggers)}


@router.delete("/clear")
async def clear_logs():
    """Clear all logs (admin only)."""

    try:
        if LOG_FILE.exists():
            LOG_FILE.unlink()
            # Recreate empty file
            LOG_FILE.touch()
        return {"status": "success", "message": "Logs cleared"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to clear logs: {str(e)}")


@router.get("/files")
async def list_log_files():
    """List available log files including rotated ones."""

    files = []
    try:
        for f in LOG_DIR.glob("ombudsman.log*"):
            stat = f.stat()
            files.append({
                "name": f.name,
                "size": stat.st_size,
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
            })
        files.sort(key=lambda x: x["modified"], reverse=True)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list log files: {str(e)}")

    return {"files": files}


@router.get("/stream")
async def stream_logs(
    lines: int = Query(100, ge=1, le=1000, description="Number of lines to return")
):
    """Get the last N lines from the log file (tail-like)."""

    if not LOG_FILE.exists():
        return {"logs": [], "count": 0}

    logs = []
    try:
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            # Read all lines and get last N
            all_lines = f.readlines()
            tail_lines = all_lines[-lines:]

            for line in tail_lines:
                try:
                    entry = json.loads(line.strip())
                    logs.append(LogEntry(**entry))
                except:
                    continue
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read logs: {str(e)}")

    return {"logs": logs, "count": len(logs)}
