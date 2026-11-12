# Render — native Python web service

No Docker. Render's native Python runtime builds and runs the app directly.

## Manual setup

1. Render dashboard → **New** → **Web Service** → connect the GitHub repo.
2. Settings:
   - **Runtime**: Python (native)
   - **Plan**: Free
   - **Build command**: `pip install uv && uv sync --frozen`
   - **Start command**: `uv run uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - **Health check path**: `/health`
3. Environment variables:
   - `PYTHON_VERSION` = `3.12.0` — pins the Python runtime
   - `API_KEY` (optional) — when set, `POST /verdict` and `GET /engines`
     require `Authorization: Bearer <key>`

## Blueprint (automated)

This repo ships a `render.yaml` Blueprint that encodes the settings above. To
use it: Render dashboard → **New** → **Blueprint** → point at the repo.

## Notes

- Free plan sleeps after ~15 minutes idle; the first request can take 30–60 s.
- Render injects `PORT`; the start command binds to it.
