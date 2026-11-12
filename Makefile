# Local build / run / push for server-verdict.
#
# For `push`, set IMAGE to a full registry reference, e.g.:
#   make push IMAGE=<dockerhub-user>/server-verdict
#   make push IMAGE=ghcr.io/<owner>/server-verdict

IMAGE ?= server-verdict
PLATFORM ?= linux/amd64

.PHONY: test build run push

test:
	uv run pytest

build:
	docker buildx build --platform $(PLATFORM) -t $(IMAGE):latest --load .

run:
	docker run --rm -p 8080:8080 $(IMAGE):latest

push:
	IMAGE="$(IMAGE)" PLATFORM="$(PLATFORM)" ./deploy/push.sh
