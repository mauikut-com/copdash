# server-verdict

A small FastAPI service that answers one question: **given a server spec and a
load description, will the server crash?**

The current engine uses simple deterministic rules (demand vs. capacity per
resource). A SimPy-based simulation engine will be added later, behind the same
engine interface.

> The API is unstable and may change without notice. Breaking changes are
> expected.

## Endpoints

| Method | Path            | Description                                  |
| ------ | --------------- | -------------------------------------------- |
| GET    | `/health`       | Liveness check.                              |
| GET    | `/openapi.json` | Auto-generated OpenAPI spec.                 |
| GET    | `/docs`         | Swagger UI.                                  |
| POST   | `/verdict`      | Evaluate a spec + load and return a verdict. |
| GET    | `/engines`      | List available engines.                      |

## Engines

Each engine implements the `VerdictEngine` protocol (`name` plus `evaluate`) and
is registered in `app/engines/__init__.py`. The rules engine lives in
`app/engines/rules.py`, with all of its formulas in that one file. To add the
future SimPy engine, drop in a `SimPyEngine` module and register it in that
registry — it becomes available automatically through `/engines` and
`/verdict` with `"engine": "simpy"`. A commented stub marks the exact spot.

## Local development

Requires [uv](https://docs.astral.sh/uv/).

```bash
uv sync                # create the venv and install dependencies
uv run uvicorn app.main:app --reload
```

The API is served at <http://127.0.0.1:8000>, with docs at
<http://127.0.0.1:8000/docs>.

## Tests

```bash
uv run pytest
```

## curl examples

```bash
curl -s http://127.0.0.1:8000/health

curl -s http://127.0.0.1:8000/engines

curl -s -X POST http://127.0.0.1:8000/verdict \
  -H 'Content-Type: application/json' \
  -d '{
    "spec": {
      "cpu": { "cores": 4, "clock_ghz": 2.5 },
      "ram": { "total_mb": 8192 },
      "network": { "bandwidth_mbps": 1000, "max_connections": 10000 }
    },
    "load": {
      "rps": 100,
      "avg_cpu_ms_per_req": 10,
      "avg_mem_mb_per_req": 5,
      "concurrent_connections": 100,
      "payload_kb": 10
    }
  }'
```

## Deploying to Render

1. Push this repository to GitHub.
2. In the Render dashboard, go to **New > Blueprint** and point it at the repo.
   Render reads `render.yaml` and creates the web service on the free plan.
3. (Optional) Set the `API_KEY` environment variable on the service to require
   a `Bearer` token on `/verdict` and `/engines`. When it is unset, no auth is
   enforced.

## Notes

- **Free plan sleep:** Render's free web service sleeps after ~15 minutes of
  inactivity. The first request after a sleep can take 30–60 seconds while the
  service spins back up.
- **Optional API key:** send `Authorization: Bearer <key>` to authenticate.
  Leave `API_KEY` unset to skip auth entirely.
- **No persistence:** there is no database; every verdict is computed on the
  fly from the request.

## Where the SimPy engine plugs in

app/engines/__init__.py has a commented stub at the ENGINES registry:

```
# from app.engines.simpy import SimPyEngine
# ENGINES["simpy"] = SimPyEngine()
```

Drop in a SimPyEngine implementing the same VerdictEngine Protocol (name "simpy", evaluate(EvaluationInput) -> VerdictResult) and
uncomment those two lines. It's immediately available via GET /engines and POST /verdict with "engine": "simpy" — no changes
needed to main.py, the schemas, or the HTTP layer.

One note: clock_ghz is currently validated but unused by the rules engine (it only keys off core count); it's documented in
schemas.py as reserved for the future simulation engine.
