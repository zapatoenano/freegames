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

Notes:

- Este es un prototipo que extrae datos públicamente visibles de las tiendas. Puede fallar si cambian las páginas o sus mecanismos anti-scraping.
- Usa el `FREEGAMES_TTL` para reducir la carga sobre las tiendas y mejorar la latencia.
