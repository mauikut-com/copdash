from fastapi.testclient import TestClient

BASE_SPEC = {
    "cpu": {"cores": 4, "clock_ghz": 2.5},
    "ram": {"total_mb": 8192},
    "network": {"bandwidth_mbps": 1000, "max_connections": 10000},
}

BASE_LOAD = {
    "rps": 100,
    "avg_cpu_ms_per_req": 10,
    "avg_mem_mb_per_req": 5,
    "concurrent_connections": 100,
    "payload_kb": 10,
}


def post_verdict(client: TestClient, spec: dict, load: dict, engine: str | None = None):
    body = {"spec": spec, "load": load}
    if engine is not None:
        body["engine"] = engine
    return client.post("/verdict", json=body)


def test_health(client: TestClient):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_openapi_json(client: TestClient):
    resp = client.get("/openapi.json")
    assert resp.status_code == 200
    assert resp.json()["info"]["title"] == "server-verdict"


def test_engines(client: TestClient):
    resp = client.get("/engines")
    assert resp.status_code == 200
    assert resp.json() == {"engines": ["rules", "simpy"]}


def test_survive(client: TestClient):
    resp = post_verdict(client, BASE_SPEC, BASE_LOAD)
    assert resp.status_code == 200
    body = resp.json()
    assert body["verdict"] == "will_survive"
    assert body["bottleneck"] == "cpu"
    assert body["engine"] == "rules"


def test_crash_cpu(client: TestClient):
    # CPU demand = 2000 * 3 / 1000 = 6 cores vs 4 -> 150%.
    load = {**BASE_LOAD, "rps": 2000, "avg_cpu_ms_per_req": 3.0}
    resp = post_verdict(client, BASE_SPEC, load)
    assert resp.status_code == 200
    body = resp.json()
    assert body["verdict"] == "will_crash"
    assert body["bottleneck"] == "cpu"
    assert body["resources"]["cpu"]["status"] == "critical"


def test_crash_ram(client: TestClient):
    # RAM demand = 1000 * 10 = 10000 MB vs 2048 -> 488%.
    spec = {**BASE_SPEC, "ram": {"total_mb": 2048}}
    load = {**BASE_LOAD, "concurrent_connections": 1000, "avg_mem_mb_per_req": 10}
    resp = post_verdict(client, spec, load)
    assert resp.status_code == 200
    body = resp.json()
    assert body["verdict"] == "will_crash"
    assert body["bottleneck"] == "ram"
    assert body["resources"]["ram"]["status"] == "critical"


def test_crash_network(client: TestClient):
    # Bandwidth demand = 1000 * 100 * 8 / 1000 = 800 Mbps vs 100 -> 800%.
    spec = {**BASE_SPEC, "network": {"bandwidth_mbps": 100, "max_connections": 10000}}
    load = {**BASE_LOAD, "rps": 1000, "avg_cpu_ms_per_req": 1.0, "payload_kb": 100}
    resp = post_verdict(client, spec, load)
    assert resp.status_code == 200
    body = resp.json()
    assert body["verdict"] == "will_crash"
    assert body["bottleneck"] == "network"
    assert body["resources"]["network"]["status"] == "critical"


def test_validation_error(client: TestClient):
    # cores must be > 0 -> 422 in FastAPI's default validation shape.
    spec = {**BASE_SPEC, "cpu": {"cores": 0, "clock_ghz": 2.5}}
    resp = post_verdict(client, spec, BASE_LOAD)
    assert resp.status_code == 422


def test_unknown_engine(client: TestClient):
    resp = post_verdict(client, BASE_SPEC, BASE_LOAD, engine="nonsense")
    assert resp.status_code == 422


def test_unknown_route_404(client: TestClient):
    resp = client.get("/nope")
    assert resp.status_code == 404
    assert "detail" in resp.json()


def test_api_key_optional(client: TestClient, monkeypatch):
    # With API_KEY unset, no auth is required.
    monkeypatch.delenv("API_KEY", raising=False)
    assert post_verdict(client, BASE_SPEC, BASE_LOAD).status_code == 200

    # With API_KEY set, a missing/invalid key is rejected and a valid one passes.
    monkeypatch.setenv("API_KEY", "secret")
    assert post_verdict(client, BASE_SPEC, BASE_LOAD).status_code == 401
    ok = client.post(
        "/verdict",
        json={"spec": BASE_SPEC, "load": BASE_LOAD},
        headers={"Authorization": "Bearer secret"},
    )
    assert ok.status_code == 200
