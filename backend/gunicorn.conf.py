"""
Gunicorn configuration for Intelli-Credit production deployment.

Usage:
    gunicorn -c gunicorn.conf.py app.main:app

This configuration uses Uvicorn workers to serve the FastAPI application
with proper async support. Each worker runs its own event loop, and
shared state is managed via Redis (not in-process memory).
"""

import os
import multiprocessing

# ─── Server Socket ────────────────────────────────────────────────────────────

bind = f"{os.getenv('HOST', '0.0.0.0')}:{os.getenv('PORT', '8000')}"

# ─── Worker Processes ─────────────────────────────────────────────────────────
# Use Uvicorn's async worker class for FastAPI compatibility.
# Formula: 2 × CPU cores + 1 (capped by WORKERS env var for containers).

worker_class = "uvicorn.workers.UvicornWorker"
workers = int(os.getenv("WORKERS", min(multiprocessing.cpu_count() * 2 + 1, 4)))
preload_app = True  # Load app once before forking workers to save RAM and startup time

# ─── Worker Lifecycle ─────────────────────────────────────────────────────────

# Restart workers after this many requests to avoid memory leaks
max_requests = 1000
max_requests_jitter = 50

# Timeout for worker response (seconds). Credit appraisal workflows
# can take several minutes, so we set a generous timeout. The actual
# analysis runs in a background task; this timeout covers API responses.
timeout = 120

# Graceful shutdown timeout
graceful_timeout = 30

# Time to wait for worker to handle existing connections before force-kill
keepalive = 5

# ─── Logging ──────────────────────────────────────────────────────────────────

accesslog = "-"  # stdout
errorlog = "-"   # stderr
loglevel = os.getenv("LOG_LEVEL", "info")

# Use a structured log format matching the app's format
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)sμs'

# ─── Pre-fork Hooks ──────────────────────────────────────────────────────────

def on_starting(server):
    """Called just before the master process is initialized."""
    server.log.info("Intelli-Credit Gunicorn server starting...")


def post_fork(server, worker):
    """Called just after a worker has been forked."""
    server.log.info(f"Worker spawned (pid: {worker.pid})")
