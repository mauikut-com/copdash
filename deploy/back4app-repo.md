# Back4app Containers — build from the GitHub repo

This is the supported path: Back4app builds the root `Dockerfile` from a
connected GitHub repo.

1. Back4app → **Containers** → **Integrate with GitHub** and connect the repo.
2. Create a new app and configure:
   - **App Name**: `server-verdict`
   - **Branch**: the branch to deploy (e.g. `main`)
   - **Root**: the repo root (`.` — where the `Dockerfile` lives)
   - **Auto Deployment**: enable to redeploy on every commit to the branch
   - **Environment Variables**:
     - `PORT` (optional, default `8080`)
     - `API_KEY` (optional) — when set, `POST /verdict` and `GET /engines`
       require `Authorization: Bearer <key>`
3. Click **Create App** and wait for the first deploy.

## Port and health check

- Back4app routes traffic to the TCP port `EXPOSE`d in the `Dockerfile`
  (`8080`). The app binds `0.0.0.0:$PORT` with a default of `8080`, so keep the
  `PORT` env var consistent with `EXPOSE` (leave it unset, or set `8080`).
- The app exposes `/health` for health checks (also used by the image's
  `HEALTHCHECK`).

## Notes

- A `Dockerfile` at the repo root is mandatory.
- Environment variable names must start with an underscore or uppercase letter
  and use only uppercase letters and numbers.
- Back4app Containers is in BETA; features may change.
