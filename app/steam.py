import requests
from bs4 import BeautifulSoup


def get_free_games_steam():
    """Busca en los resultados de búsqueda de Steam elementos que aparezcan como gratuitos
    (por ejemplo "Free", "Free To Play" o descuentos -100%). Devuelve lista de dicts.
    """
    url = "https://store.steampowered.com/search/results/?query&start=0&count=50"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        r = requests.get(url, timeout=10, headers=headers)
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
        # Normalize output
        normalized = []
        for r in results:
            normalized.append({
                "title": r.get("title"),
                "url": r.get("url"),
                "start": None,
                "end": None,
            })
        return normalized
    except Exception as e:
        return {"error": str(e)}
