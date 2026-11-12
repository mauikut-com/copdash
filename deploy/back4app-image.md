# Back4app Containers — from a prebuilt Docker image

> As of the current Back4app Containers docs (first/BETA release), Back4app only
> supports **building from a connected GitHub repo via a Dockerfile**. There is
> no "create from a private Docker image" option, so this path is not currently
> available. **Use [back4app-repo.md](./back4app-repo.md) instead.**
>
> The steps below are kept for reference (pushing the image + a read-only pull
> credential), and in case Back4app later adds image-based deploys.

## Push the image (from your machine)

1. Create a GitHub **classic** personal access token with the `write:packages`
   scope (to push to GHCR).
2. Log in and push:
   ```bash
   echo "$TOKEN" | docker login ghcr.io -u <github-username> --password-stdin
   make push IMAGE=ghcr.io/<owner>/server-verdict
   # or: IMAGE=ghcr.io/<owner>/server-verdict ./deploy/push.sh
   ```
   This tags the image with the short commit SHA (`<sha>`, or `<sha>-dirty`
   when the tree has uncommitted changes) and with `latest`, then pushes both.

## Pull credential (least privilege)

For the target host (Back4app, or any platform pulling from GHCR), create a
**separate** classic PAT with only the `read:packages` scope. Enter it as the
registry password (username = your GitHub username) in the host's registry
settings.

## Image-based deploy (when/if supported)

- **Image**: `ghcr.io/<owner>/server-verdict:<sha tag>`
- **Registry username / password**: GitHub username + `read:packages` PAT
- **Port**: the `PORT` value (default `8080`)
- **Health path**: `/health`
- **Environment variables**: `PORT` (default `8080`), optional `API_KEY`

## Updating

Select a new `<sha>` tag (or redeploy) to pick up changes. Prefer the SHA tag
over `latest`: `latest` is mutable and can point to a broken build, whereas the
SHA tag is pinned and reproducible.
