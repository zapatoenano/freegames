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

Notes:

- Este es un prototipo que extrae datos públicamente visibles de las tiendas. Puede fallar si cambian las páginas o sus mecanismos anti-scraping.
- Usa el `FREEGAMES_TTL` para reducir la carga sobre las tiendas y mejorar la latencia.
