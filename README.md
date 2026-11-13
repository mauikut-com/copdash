# server-verdict

A small FastAPI service that answers one question: **given a server spec and a
load description, will the server crash?**

Two engines answer the question behind the same interface:

- **rules** — simple deterministic rules (demand vs. capacity per resource).
- **simpy** — a minimal discrete-event simulation (SimPy) of the CPU, RAM, and
  network blocks.

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
`app/engines/rules.py`, with all of its formulas in that one file; the SimPy
engine lives in `app/engines/simpy.py`.

## Deployment targets

One codebase, three ways to deploy (no target-specific code in the app — all
differences live under `deploy/`):

| Target                              | How                                                                 | Use when                                    |
| ----------------------------------- | ------------------------------------------------------------------- | ------------------------------------------- |
| Render (native Python)              | `render.yaml` Blueprint — no Docker                                 | Simplest free host; no image to manage      |
| Back4app Containers (from image)    | Push a private image, then reference it (see `deploy/back4app-image.md`) | Not currently offered by Back4app — see note |
| Back4app Containers (from repo)     | Back4app builds the root `Dockerfile` (see `deploy/back4app-repo.md`) | Back4app's supported path                   |

> Back4app Containers currently only builds from a connected GitHub repo, so use
> `deploy/back4app-repo.md`. Full steps per target: `deploy/render.md`,
> `deploy/back4app-image.md`, `deploy/back4app-repo.md`.

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

## Docker

```bash
make build   # build the image locally
make run     # docker run --rm -p 8080:8080 <image>
make push    # build + push (set IMAGE, e.g. <dockerhub-user>/server-verdict)
```

Or with the scripts directly:

```bash
docker buildx build --platform linux/amd64 -t server-verdict:latest --load .
docker run --rm -p 8080:8080 server-verdict:latest
IMAGE=<dockerhub-user>/server-verdict ./deploy/push.sh   # or ghcr.io/<owner>/server-verdict
```

`push.sh` runs the tests, builds for `linux/amd64`, tags the image with the
short git commit SHA (plus `-dirty` when the tree is dirty) and `latest`, and
pushes both. Set `IMAGE` (required) and optionally `PLATFORM`.

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

## Examples

Each row is a self-contained request and the exact response it returns.

| Scenario | Request | Expected response |
|----------|---------|-------------------|
| Survive (default `rules`) | `curl -s -X POST http://127.0.0.1:8000/verdict -H 'Content-Type: application/json' -d '{"spec":{"cpu":{"cores":4,"clock_ghz":2.5},"ram":{"total_mb":8192},"network":{"bandwidth_mbps":1000,"max_connections":10000}},"load":{"rps":100,"avg_cpu_ms_per_req":10,"avg_mem_mb_per_req":5,"concurrent_connections":100,"payload_kb":10}}'` | `{"verdict":"will_survive","confidence":0.84,"bottleneck":"cpu","resources":{"cpu":{"utilization":0.25,"status":"ok"},"ram":{"utilization":0.061,"status":"ok"},"network":{"utilization":0.01,"status":"ok"}}}` |
| At risk — CPU ~90% (`rps: 360`) | `curl -s -X POST http://127.0.0.1:8000/verdict -H 'Content-Type: application/json' -d '{"spec":{"cpu":{"cores":4,"clock_ghz":2.5},"ram":{"total_mb":8192},"network":{"bandwidth_mbps":1000,"max_connections":10000}},"load":{"rps":360,"avg_cpu_ms_per_req":10,"avg_mem_mb_per_req":5,"concurrent_connections":100,"payload_kb":10}}'` | `{"verdict":"at_risk","confidence":1.0,"bottleneck":"cpu","resources":{"cpu":{"utilization":0.9,"status":"warning"},"ram":{"utilization":0.061,"status":"ok"},"network":{"utilization":0.0288,"status":"ok"}}}` |
| Crash — CPU-bound (`rps: 2000`, `avg_cpu_ms_per_req: 3`) | `curl -s -X POST http://127.0.0.1:8000/verdict -H 'Content-Type: application/json' -d '{"spec":{"cpu":{"cores":4,"clock_ghz":2.5},"ram":{"total_mb":8192},"network":{"bandwidth_mbps":1000,"max_connections":10000}},"load":{"rps":2000,"avg_cpu_ms_per_req":3,"avg_mem_mb_per_req":5,"concurrent_connections":100,"payload_kb":10}}'` | `{"verdict":"will_crash","confidence":1.0,"bottleneck":"cpu","resources":{"cpu":{"utilization":1.5,"status":"critical"},"ram":{"utilization":0.061,"status":"ok"},"network":{"utilization":0.16,"status":"ok"}}}` |
| SimPy engine — same load as row 1 | `curl -s -X POST http://127.0.0.1:8000/verdict -H 'Content-Type: application/json' -d '{"engine":"simpy","spec":{"cpu":{"cores":4,"clock_ghz":2.5},"ram":{"total_mb":8192},"network":{"bandwidth_mbps":1000,"max_connections":10000}},"load":{"rps":100,"avg_cpu_ms_per_req":10,"avg_mem_mb_per_req":5,"concurrent_connections":100,"payload_kb":10}}'` | `{"verdict":"will_survive","confidence":0.85,"bottleneck":"cpu","resources":{"cpu":{"utilization":0.2458,"status":"ok"},"ram":{"utilization":0.0006,"status":"ok"},"network":{"utilization":0.0079,"status":"ok"}}}` |

The full response also includes a `reasons` list (human-readable derivation steps).
For the first example above, the complete body is:

```json
{
  "verdict": "will_survive",
  "confidence": 0.84,
  "bottleneck": "cpu",
  "resources": {
    "cpu":     {"utilization": 0.25,  "status": "ok"},
    "ram":     {"utilization": 0.061, "status": "ok"},
    "network": {"utilization": 0.01,  "status": "ok"}
  },
  "reasons": [
    "CPU: 1.00 of 4.00 cores busy (25.0%).",
    "RAM: 500 of 8192 MB used (6.1%).",
    "Network: 8.0 Mbps bandwidth (0.8%), 100/10000 connections (1.0%).",
    "Peak utilization 25.0% on cpu; verdict will_survive."
  ],
  "engine": "rules"
}
```

## Deploying to Render

1. Push this repository to GitHub.
2. In the Render dashboard, go to **New > Blueprint** and point it at the repo.
   Render reads `render.yaml` and creates the web service on the free plan.
3. (Optional) Set the `API_KEY` environment variable on the service to require
   a `Bearer` token on `/verdict` and `/engines`. When it is unset, no auth is
   enforced.

For manual setup (or other hosts), see the `deploy/` directory.

## Notes

- **Free plan sleep:** Render's free web service sleeps after ~15 minutes of
  inactivity. The first request after a sleep can take 30–60 seconds while the
  service spins back up.
- **Optional API key:** send `Authorization: Bearer <key>` to authenticate.
  Leave `API_KEY` unset to skip auth entirely.
- **No persistence:** there is no database; every verdict is computed on the
  fly from the request.

## Where the SimPy engine plugs in

`app/engines/simpy.py` implements `SimPyEngine` (name `"simpy"`), registered in
`app/engines/__init__.py`. It models the CPU, RAM, and network blocks as SimPy
resources and reuses the rules engine's 80%/100% verdict thresholds. See
`docs/simpy-dataset.md` for the synthetic dataset requirements its validation
exposes.

One note: `clock_ghz` is currently validated but unused by either engine (the
rules engine keys off core count only; the SimPy engine keys off cores and
per-request cost); it's documented in `schemas.py` as reserved.
