import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import time


def _session_with_retries(retries: int = 3, backoff: float = 0.5):
    s = requests.Session()
    retry = Retry(total=retries, backoff_factor=backoff, status_forcelist=(429, 500, 502, 503, 504))
    s.mount("https://", HTTPAdapter(max_retries=retry))
    s.headers.update({"User-Agent": "Mozilla/5.0 (compatible; freegames-bot/1.0)"})
    return s


def get_free_games_steam():
    """Busca en los resultados de búsqueda de Steam elementos que aparezcan como gratuitos
    (por ejemplo "Free", "Free To Play" o descuentos -100%). Devuelve lista de dicts.
    """
    url = "https://store.steampowered.com/search/results/?query&start=0&count=50"
    s = _session_with_retries()
    try:
        r = s.get(url, timeout=10)
        r.raise_for_status()
        data = r.json()
        html = data.get('results_html', '')
        soup = BeautifulSoup(html, 'html.parser')
        rows = soup.select('.search_result_row')
        results = []
        for row in rows:
            title_el = row.select_one('.title')
            title = title_el.get_text(strip=True) if title_el else None
            href = row.get('href')
            price_el = row.select_one('.search_price')
            price_text = price_el.get_text(' ', strip=True) if price_el else ''
            if not title or not href:
                continue
            if 'free' in price_text.lower() or 'free to play' in price_text.lower() or '-100%' in price_text:
                results.append({"title": title, "url": href, "price_text": price_text})
        # For each result try to fetch the game's page to extract image/description/genre
        normalized = []
        for r in results:
            image = None
            description = None
            genre = None
            href = r.get("url")
            # try to fetch individual page (best-effort)
            try:
                time.sleep(0.1)
                g = s.get(href, timeout=8)
                g.raise_for_status()
                gsoup = BeautifulSoup(g.text, 'html.parser')
                # common meta tags
                og_image = gsoup.select_one('meta[property="og:image"]')
                if og_image and og_image.get('content'):
                    image = og_image.get('content')
                # description
                og_desc = gsoup.select_one('meta[property="og:description"]') or gsoup.select_one('meta[name="description"]')
                if og_desc and og_desc.get('content'):
                    description = og_desc.get('content')
                # genre: try glance_tags or details
                tag_block = gsoup.select_one('.glance_tags') or gsoup.select_one('.details_block')
                if tag_block:
                    # take first tag-like text
                    tags = [t.get_text(strip=True) for t in tag_block.select('a') if t.get_text(strip=True)]
                    if tags:
                        genre = tags[0]
            except Exception:
                # ignore per-game failures
                pass

            normalized.append({
                "title": r.get("title"),
                "url": href,
                "start": None,
                "end": None,
                "image": image,
                "description": description,
                "genre": genre,
            })
        return normalized
    except Exception as e:
        return {"error": str(e)}
