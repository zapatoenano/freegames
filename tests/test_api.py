from fastapi.testclient import TestClient

from app.main import app


def test_health():
    client = TestClient(app)
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_free_endpoints(monkeypatch):
    client = TestClient(app)

    # Parchear las funciones cacheadas para devolver resultados deterministas
    monkeypatch.setattr('app.main.cached_epic', lambda: [{"title": "Epic Free", "url": "https://epic"}])
    monkeypatch.setattr('app.main.cached_steam', lambda: [{"title": "Steam Free", "url": "https://store"}])

    r = client.get("/free-now")
    assert r.status_code == 200
    data = r.json()
    assert "epic" in data and "steam" in data
    assert data["epic"][0]["title"] == "Epic Free"

    r2 = client.get("/free-now/epic")
    assert r2.status_code == 200
    assert r2.json() == {"epic": [{"title": "Epic Free", "url": "https://epic"}]}

    r3 = client.get("/free-now/steam")
    assert r3.status_code == 200
    assert r3.json() == {"steam": [{"title": "Steam Free", "url": "https://store"}]}
