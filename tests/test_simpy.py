"""Tests for the SimPy verdict engine.

These run through the HTTP layer so the engine is exercised end-to-end, the same
way the rules engine is tested. The fixed seed in SimPyEngine keeps every verdict
deterministic, so assertions are stable.
"""

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


def post_verdict(client: TestClient, spec: dict, load: dict, engine: str = "simpy"):
    return client.post("/verdict", json={"spec": spec, "load": load, "engine": engine})


def test_simpy_survive(client: TestClient):
    resp = post_verdict(client, BASE_SPEC, BASE_LOAD)
    assert resp.status_code == 200
    body = resp.json()
    assert body["engine"] == "simpy"
    assert body["verdict"] == "will_survive"


def test_simpy_crash_cpu(client: TestClient):
    # Offered CPU demand = 2000 * 3 / 1000 = 6 cores vs 4 -> 150%.
    load = {**BASE_LOAD, "rps": 2000, "avg_cpu_ms_per_req": 3.0}
    resp = post_verdict(client, BASE_SPEC, load)
    assert resp.status_code == 200
    body = resp.json()
    assert body["verdict"] == "will_crash"
    assert body["bottleneck"] == "cpu"
    assert body["resources"]["cpu"]["status"] == "critical"


def test_simpy_crash_ram(client: TestClient):
    # Offered RAM demand = 1000 * 10 = 10000 MB vs 2048 -> 488%.
    spec = {**BASE_SPEC, "ram": {"total_mb": 2048}}
    load = {**BASE_LOAD, "concurrent_connections": 1000, "avg_mem_mb_per_req": 10}
    resp = post_verdict(client, spec, load)
    assert resp.status_code == 200
    body = resp.json()
    assert body["verdict"] == "will_crash"
    assert body["bottleneck"] == "ram"
    assert body["resources"]["ram"]["status"] == "critical"


def test_simpy_no_load(client: TestClient):
    load = {
        "rps": 0,
        "avg_cpu_ms_per_req": 0,
        "avg_mem_mb_per_req": 0,
        "concurrent_connections": 0,
        "payload_kb": 0,
    }
    resp = post_verdict(client, BASE_SPEC, load)
    assert resp.status_code == 200
    body = resp.json()
    assert body["verdict"] == "will_survive"
    assert body["bottleneck"] is None


def test_simpy_agrees_with_rules(client: TestClient):
    """The two engines should reach the same verdict on clearly-separated loads."""
    cases = [
        BASE_LOAD,  # survive
        {**BASE_LOAD, "rps": 2000, "avg_cpu_ms_per_req": 3.0},  # crash (cpu)
        {**BASE_LOAD, "rps": 360},  # cpu = 360*10/1000/4 = 0.9 -> at_risk
    ]
    for load in cases:
        rules = client.post("/verdict", json={"spec": BASE_SPEC, "load": load, "engine": "rules"})
        simpy = client.post("/verdict", json={"spec": BASE_SPEC, "load": load, "engine": "simpy"})
        assert rules.status_code == 200
        assert simpy.status_code == 200
        assert simpy.json()["verdict"] == rules.json()["verdict"], load
