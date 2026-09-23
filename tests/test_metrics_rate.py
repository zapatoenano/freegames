from fastapi.testclient import TestClient
import time

from app import main as app_main
from app.main import app


def test_metrics_endpoint():
    client = TestClient(app)
    r = client.get("/metrics")
    assert r.status_code == 200
    # prometheus content type
    assert "text/plain" in r.headers.get("content-type", "")
    body = r.text
    # should expose our metric names
    assert "freegames_requests_total" in body


def test_rate_limit(monkeypatch):
    client = TestClient(app)
    # patch globals to low limit and reset store
    monkeypatch.setattr(app_main, 'RATE_LIMIT_ENABLED', True)
    monkeypatch.setattr(app_main, 'RATE_LIMIT_PER_MIN', 2)
    with app_main._rate_lock:
        app_main._rate_store.clear()

    # two allowed
    r1 = client.get("/health")
    assert r1.status_code == 200
    r2 = client.get("/health")
    assert r2.status_code == 200
    # third should be rate limited
    r3 = client.get("/health")
    assert r3.status_code == 429
    assert r3.json().get("detail") == "rate limit exceeded"
