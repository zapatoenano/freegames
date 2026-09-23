import requests
import json
from bs4 import BeautifulSoup


def get_free_games_epic():
    """Extrae (mejor esfuerzo) las ofertas gratuitas desde la página de Epic Store.
    Devuelve lista de dicts: {title, url, start, end} cuando sea posible.
    """
    url = "https://store.epicgames.com/en-US/free-games"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        r = requests.get(url, timeout=10, headers=headers)
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
                        results.append({"title": title, "url": link, "start": start, "end": end})
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
                if href and title and href not in seen:
                    seen.add(href)
                    results.append({"title": title, "url": href})

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
