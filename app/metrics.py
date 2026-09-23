from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
import time
from fastapi import Response

# Metrics
REQUEST_COUNT = Counter('freegames_requests_total', 'Total HTTP requests', ['method', 'endpoint', 'http_status'])
REQUEST_LATENCY = Histogram('freegames_request_latency_seconds', 'Request latency seconds', ['endpoint'])


def metrics_response() -> Response:
    data = generate_latest()
    return Response(content=data, media_type=CONTENT_TYPE_LATEST)


def observe_request(endpoint: str, method: str, status: int, duration: float):
    try:
        REQUEST_COUNT.labels(method, endpoint, str(status)).inc()
        REQUEST_LATENCY.labels(endpoint).observe(duration)
    except Exception:
        # noop on metrics errors
        pass
