Release notes (draft)

Version: v0.1.2 (draft)

Release summary
- CI hardening: retry `pip install` with backoff and verbose output to mitigate transient network or PyPI issues.
- Workflow fixes: removed direct `secrets.*` usage from `if` expressions; optional Docker Hub creds now exposed via `env`.
- Scrapers: improved stability with retries/backoff and better metadata extraction for `image`, `description`, and `genre` fields.
- Persistence: `Offer` windows (`start`/`end`) are timezone-aware and upserts were hardened to avoid duplicate entries.
- Observability: added Prometheus metrics for requests and scraper runs; metrics exposed at `/metrics`.
- Rate limiting: Redis-backed rate limiter implemented (optional); tests use `fakeredis` for CI.
- Docker & CI: multi-arch image build configured and GHCR publish in CI. Docker Hub push remains optional and gated by env secrets.

Detailed changes
- `app/epic.py`, `app/steam.py`: retry logic, backoff, and extra fields extracted (image, description, genre).
- `app/models.py`: `Offer` model stores `image`, `description`, `genre`, and timezone-aware datetimes.
- `app/service.py`: improved normalization and upsert logic for overlapping offers.
- `app/metrics.py`: Prometheus counters and histograms for endpoints and scraper durations.
- `app/rate_limit_redis.py`: Redis middleware for fixed-window rate limiting; can be enabled with `FREEGAMES_RATE_LIMIT_REDIS_URL`.

How to validate locally
1. Start Redis and the API with docker-compose (recommended for parity with CI):

```bash
docker compose up -d
docker compose logs -f
```

2. Run tests locally (from repo root):

```bash
python -m pip install --upgrade pip
pip install -r free-games-api/requirements.txt
python -m pytest free-games-api -q
```

Validation checklist (post-CI)
- Confirm `test` job passes for Python 3.11.
- If `build-and-push` runs, verify GHCR image tags:
	- `ghcr.io/<owner>/freegames:latest`
	- `ghcr.io/<owner>/freegames:<sha>`
- Optional: if Docker Hub credentials were provided via repo secrets, confirm images pushed to `docker.io/<user>/freegames:latest`.
- After release, attach these release notes and any build artifacts to the GitHub Release.

Known issues & mitigation
- Intermittent `pip install` failures: CI now retries and prints verbose pip output.
- Docker Hub: ensure `DOCKERHUB_USERNAME` and `DOCKERHUB_TOKEN` are set in repo secrets to enable optional push.

Contact
- Maintainer: @zapatoenano (isabel.rossdt@gmail.com)

Next steps
- Finalize this draft and create the GitHub Release when CI reports successful `build-and-push`.
- Collect and attach build artifacts or image references as release assets.

CI trigger: small metadata update to prompt CI run.
