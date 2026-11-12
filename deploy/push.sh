#!/usr/bin/env bash
set -euo pipefail

# Build and push the server-verdict image.
#
# Configuration (all via environment variables — nothing is hardcoded):
#   IMAGE      (required) full image reference, e.g.:
#                ghcr.io/<owner>/server-verdict   (GHCR)
#                <dockerhub-user>/server-verdict  (Docker Hub)
#   PLATFORM   (optional) build platform, default linux/amd64

if [[ -z "${IMAGE:-}" ]]; then
  echo "error: IMAGE is not set. Set it to e.g. ghcr.io/<owner>/server-verdict" >&2
  exit 1
fi

PLATFORM="${PLATFORM:-linux/amd64}"

# Registry host, for the login pre-check below. Docker Hub images are written
# as `owner/repo` (no host), so only treat the first component as a registry
# host when it actually looks like one (contains a `.` or `:`).
FIRST="${IMAGE%%/*}"
if [[ "${IMAGE}" == *"/"* && ( "${FIRST}" == *"."* || "${FIRST}" == *":"* ) ]]; then
  REGISTRY="${FIRST}"    # e.g. ghcr.io, docker.io, registry.example.com, localhost:5000
else
  REGISTRY="docker.io"   # owner/repo or bare repo -> Docker Hub
fi

# 1. Pre-flight: fail clearly before doing any work.
if ! command -v docker >/dev/null 2>&1; then
  echo "error: docker is not installed or not on PATH" >&2
  exit 1
fi
# NOTE: this checks the standard `docker login` credential file. If you use a
# credential helper, adjust the check to match your setup. The match is a plain
# substring (no surrounding quotes) so it also matches Docker Hub's auth key
# `https://index.docker.io/v1/`, not just a bare hostname.
if [[ ! -f "${HOME}/.docker/config.json" ]] || ! grep -qs "${REGISTRY}" "${HOME}/.docker/config.json"; then
  echo "error: not logged in to ${REGISTRY}. Run: docker login ${REGISTRY}" >&2
  exit 1
fi

# 2. Never push an untested image.
uv run pytest

# 3. Tag with the short commit SHA, marked "-dirty" when the tree has changes.
SHA="$(git rev-parse --short HEAD)"
if [[ -n "$(git status --porcelain)" ]]; then
  SHA="${SHA}-dirty"
fi

REF="${IMAGE}:${SHA}"

# 4. Build once for linux/amd64 and push both the SHA tag and :latest.
echo "Building and pushing ${REF} (and ${IMAGE}:latest) for ${PLATFORM}..."
docker buildx build \
  --platform "${PLATFORM}" \
  --tag "${REF}" \
  --tag "${IMAGE}:latest" \
  --push \
  .

echo "Pushed ${REF} (and ${IMAGE}:latest)"
