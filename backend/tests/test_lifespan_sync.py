"""Regression coverage for the FastAPI GitHub sync lifecycle."""

from fastapi.testclient import TestClient

from backend import main


def test_lifespan_starts_and_stops_github_sync(monkeypatch):
    calls = []
    monkeypatch.setattr(main, "_start_sync", lambda: calls.append("start"))
    monkeypatch.setattr(main, "_stop_sync", lambda: calls.append("stop"))

    with TestClient(main.app) as client:
        assert calls == ["start"]
        response = client.get("/api/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

    assert calls == ["start", "stop"]


def test_github_sync_disabled_by_default(monkeypatch):
    monkeypatch.setenv("GITHUB_AUTO_SYNC", "0")
    main._sync_stop.set()
    main._start_sync()
    assert main._sync_stop.is_set()
