from __future__ import annotations


def test_health_returns_ok(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "product_provider" in data
    assert data["product_provider"] == "mock"


def test_health_has_model_fields(client):
    resp = client.get("/health")
    data = resp.json()
    assert "models" in data
    assert "chat" in data["models"]
    assert "vision" in data["models"]
    assert "embedding" in data["models"]
