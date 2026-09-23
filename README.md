# Free Games API

API mínima en FastAPI que devuelve juegos que actualmente están gratis en Epic y Steam.


Run locally:

```bash
python -m pip install -r requirements.txt
# desde la raíz del repo
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000 --app-dir free-games-api
```

Environment variables:

- `FREEGAMES_TTL` (optional): cache TTL in seconds for store scrapes. Default `300` (5 minutes).
- `FREEGAMES_DB_URL` (optional): SQLAlchemy DB URL. Default `sqlite:///./data/offers.db`.
- `FREEGAMES_FETCH_MINUTES` (optional): scheduler polling interval in minutes. Default `15`.

Endpoints:

- `GET /free-now` — lista de juegos gratis actualmente (origen: `epic`, `steam`).
- `GET /free-now/epic` — solo ofertas de Epic.
- `GET /free-now/steam` — solo ofertas de Steam.
- `GET /health` — estado del servicio.

Testing:

```bash
# desde la carpeta free-games-api
python -m pytest -q
```

Docker (opcional):

```bash
# construir imagen desde la raíz del proyecto
docker build -t free-games-api -f free-games-api/Dockerfile .
# ejecutar el contenedor
docker run -p 8000:8000 -e FREEGAMES_TTL=300 free-games-api
```

Container image (GHCR):

If the CI runs on `main` or when creating tags it will publish the built image to GitHub Container Registry (GHCR) under your user/org. Example pull commands:

```bash
# pull the latest image
docker pull ghcr.io/<OWNER>/freegames:latest

# pull the specific commit image
docker pull ghcr.io/<OWNER>/freegames:<COMMIT_SHA>
```

Replace `<OWNER>` with your GitHub username or organization. If you prefer Docker Hub instead, provide the repo name and I can add a second push step and README examples.

Docker Hub (optional):

If you want to publish to Docker Hub, set GitHub Actions secrets `DOCKERHUB_USERNAME` and `DOCKERHUB_TOKEN` (or a Personal Access Token). The workflow will push `DOCKERHUB_USERNAME/freegames:latest` and `DOCKERHUB_USERNAME/freegames:<COMMIT_SHA>`.

Docker Compose example:

```yaml
version: '3.8'
services:
	freegames:
		image: ghcr.io/<OWNER>/freegames:latest
		ports:
			- "8000:8000"
		environment:
			- FREEGAMES_TTL=300
			- FREEGAMES_FETCH_MINUTES=15
			- FREEGAMES_DB_URL=sqlite:///./data/offers.db
		volumes:
			- ./data:/app/data
		restart: unless-stopped
```

Development (Docker Compose override):

If you want to run the API locally with Redis for the rate-limiter, there's a `docker-compose.override.yml` that builds the local `freegames` image and starts `redis`.

Start the stack:

```bash
docker compose up -d
```

Environment variables set in the override:

- `FREEGAMES_RATE_LIMIT_REDIS_URL=redis://redis:6379`
- `FREEGAMES_RATE_LIMIT_PER_MIN=60`

Smoke tests after startup:

```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/metrics
```

If you don't have Docker here, run the same commands on your machine with Docker installed.

Notes:

- Este es un prototipo que extrae datos públicamente visibles de las tiendas. Puede fallar si cambian las páginas o sus mecanismos anti-scraping.
- Usa el `FREEGAMES_TTL` para reducir la carga sobre las tiendas y mejorar la latencia.
