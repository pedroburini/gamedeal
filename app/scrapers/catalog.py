import re
import httpx
from bs4 import BeautifulSoup


STEAM_SEARCH_URL = "https://store.steampowered.com/search/results"


def slugify(name: str) -> str:
    """Converte nome do jogo para slug estilo Nuuvem."""
    name = name.lower()
    name = re.sub(r"[™®©]", "", name)
    name = re.sub(r"[^a-z0-9\s-]", "", name)
    name = re.sub(r"\s+", "-", name.strip())
    name = re.sub(r"-+", "-", name)
    return name


async def fetch_on_sale(count: int = 200) -> list[dict]:
    """Retorna jogos atualmente em promoção na Steam."""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "pt-BR,pt;q=0.9"
    }

    params = {
        "filter": "specials",
        "cc": "br",
        "l": "portuguese",
        "count": count,
        "json": 1
    }

    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(
                STEAM_SEARCH_URL,
                params=params,
                headers=headers,
                timeout=15.0
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            print(f"[catalog] Erro ao buscar promoções Steam: {e}")
            return []

    games = []
    for item in data.get("items", []):
        try:
            soup = BeautifulSoup(item.get("name", ""), "html.parser")
            title = soup.get_text(strip=True) or item.get("name", "")

            logo = item.get("logo", "")
            match = re.search(r"/apps/(\d+)/", logo)
            if not match:
                continue
            steam_app_id = match.group(1)

            nuuvem_slug = slugify(title)

            games.append({
                "title": title,
                "steam_app_id": steam_app_id,
                "nuuvem_slug": nuuvem_slug
            })
        except Exception:
            continue

    return games


async def fetch_top_sellers(count: int = 50) -> list[dict]:
    """Retorna top sellers da Steam (complementar)."""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "pt-BR,pt;q=0.9"
    }

    params = {
        "filter": "topsellers",
        "cc": "br",
        "l": "portuguese",
        "count": count,
        "json": 1
    }

    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(
                STEAM_SEARCH_URL,
                params=params,
                headers=headers,
                timeout=15.0
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            print(f"[catalog] Erro ao buscar top sellers: {e}")
            return []

    games = []
    for item in data.get("items", []):
        try:
            soup = BeautifulSoup(item.get("name", ""), "html.parser")
            title = soup.get_text(strip=True) or item.get("name", "")

            logo = item.get("logo", "")
            match = re.search(r"/apps/(\d+)/", logo)
            if not match:
                continue
            steam_app_id = match.group(1)

            games.append({
                "title": title,
                "steam_app_id": steam_app_id,
                "nuuvem_slug": slugify(title)
            })
        except Exception:
            continue

    return games
