"""
Gunicorn 配置文件
用于 PMRS 生产环境部署
"""
import multiprocessing
import os

# Server socket
bind = "0.0.0.0:8000"
backlog = 2048

# Worker processes
workers = int(os.getenv("GUNICORN_WORKERS", multiprocessing.cpu_count() * 2 + 1))
worker_class = "uvicorn.workers.UvicornWorker"
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 100
timeout = 120
keepalive = 5

# Logging
accesslog = "-"
errorlog = "-"
loglevel = os.getenv("LOG_LEVEL", "info").lower()
access_log_format = '{"remote_ip":"%(h)s","request_id":"%({X-Request-ID}i)s","response_code":"%(s)s","request_method":"%(m)s","request_path":"%(U)s","request_querystring":"%(q)s","request_time":"%(D)s","response_length":"%(B)s"}'

# Process naming
proc_name = "pmrs-backend"

# Server mechanics
daemon = False
pidfile = None
umask = 0
user = None
group = None
tmp_upload_dir = None

# SSL (if needed)
# keyfile = "/path/to/key.pem"
# certfile = "/path/to/cert.pem"

# Preload app for memory efficiency
preload_app = True

# Graceful timeout
graceful_timeout = 30

# Worker lifecycle
worker_tmp_dir = "/dev/shm"
