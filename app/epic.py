import requests
import json
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


def _session_with_retries(retries: int = 3, backoff: float = 0.5):
    s = requests.Session()
    retry = Retry(total=retries, backoff_factor=backoff, status_forcelist=(429, 500, 502, 503, 504))
    s.mount("https://", HTTPAdapter(max_retries=retry))
    s.headers.update({"User-Agent": "Mozilla/5.0 (compatible; freegames-bot/1.0)"})
    return s


def get_free_games_epic():
    """Extrae (mejor esfuerzo) las ofertas gratuitas desde la página de Epic Store.
    Devuelve lista de dicts: {title, url, start, end} cuando sea posible.
    """
    url = "https://store.epicgames.com/en-US/free-games"
    s = _session_with_retries()
    try:
        r = s.get(url, timeout=10)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")

        results = []

        # Intento 1: buscar __NEXT_DATA__ (Next.js) con información estructurada
        script = soup.find("script", id="__NEXT_DATA__")
        if script and script.string:
            try:
                data = json.loads(script.string)

                def find_offers(obj):
                    if isinstance(obj, dict):
                        for k, v in obj.items():
                            if k and 'free' in k.lower() and isinstance(v, (list, dict)):
                                return v
                            found = find_offers(v)
                            if found:
                                return found
                    if isinstance(obj, list):
                        for item in obj:
                            found = find_offers(item)
                            if found:
                                return found
                    return None

                offers = find_offers(data)
                if isinstance(offers, list):
                    for offer in offers:
                        title = offer.get('title') or offer.get('productName') or offer.get('titleText')
                        slug = offer.get('productSlug') or offer.get('url')
                        link = None
                        if slug:
                            link = slug if slug.startswith('http') else ('https://store.epicgames.com' + slug)
                        start = offer.get('startDate') or offer.get('effectiveDate')
                        end = offer.get('endDate') or offer.get('expiryDate')
                        # Try to extract image/description/genre from structured data
                        image = None
                        description = offer.get('description') or offer.get('longDescription') or offer.get('shortDescription')
                        # keyImages often contains image urls
                        ki = offer.get('keyImages') or []
                        if isinstance(ki, list) and ki:
                            for item in ki:
                                if isinstance(item, dict) and item.get('url'):
                                    image = item.get('url')
                                    break

                        # genres/categories may be present
                        genre = None
                        categories = offer.get('categories') or offer.get('tags') or offer.get('genres')
                        if isinstance(categories, list) and categories:
                            # pick first category name if available
                            first = categories[0]
                            if isinstance(first, dict):
                                genre = first.get('name')
                            elif isinstance(first, str):
                                genre = first

                        results.append({
                            "title": title,
                            "url": link,
                            "start": start,
                            "end": end,
                            "image": image,
                            "description": description,
                            "genre": genre,
                        })
            except Exception:
                pass

        # Intento 2: fallback parseando tarjetas visibles
        if not results:
            cards = soup.select("a[data-testid='offer-card-clickable'], a[href*='/p/']")
            seen = set()
            for a in cards:
                title = None
                title_el = a.select_one("h3") or a.select_one(".Card-title")
                if title_el:
                    title = title_el.get_text(strip=True)
                href = a.get('href')
                # attempt to find image and short description inside card
                image = None
                img_el = a.select_one('img')
                if img_el:
                    image = img_el.get('src') or img_el.get('data-src')
                desc = None
                desc_el = a.select_one('p') or a.select_one('.Card-body')
                if desc_el:
                    desc = desc_el.get_text(strip=True)
                if href and title and href not in seen:
                    seen.add(href)
                    results.append({"title": title, "url": href, "image": image, "description": desc, "genre": None})

        # Normalize output to dicts with title/url/start/end
        normalized = []
        for r in results:
            normalized.append({
                "title": r.get("title"),
                "url": r.get("url"),
                "start": r.get("start"),
                "end": r.get("end"),
            })
        return normalized
    except Exception as e:
        return {"error": str(e)}
