import httpx
from bs4 import BeautifulSoup


NUUVEM_BASE = "https://www.nuuvem.com/br-en/item"


async def get_nuuvem_price(slug: str) -> dict | None:
    url = f"{NUUVEM_BASE}/{slug}"
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        )
    }

    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(url, headers=headers, timeout=10.0, follow_redirects=True)
            resp.raise_for_status()
        except Exception:
            return None

    soup = BeautifulSoup(resp.text, "html.parser")

    try:
        # Preço atual
        price_tag = soup.select_one(".product-price--val")
        if not price_tag:
            return None
        price_text = price_tag.get_text(strip=True).replace("R$", "").replace(",", ".").strip()
        price = float(price_text)

        # Preço original (se houver desconto)
        original_tag = soup.select_one(".product-price--original")
        if original_tag:
            original_text = original_tag.get_text(strip=True).replace("R$", "").replace(",", ".").strip()
            original_price = float(original_text)
        else:
            original_price = price

        # Percentual de desconto
        discount_tag = soup.select_one(".product-price--discount")
        if discount_tag:
            discount_text = discount_tag.get_text(strip=True).replace("-", "").replace("%", "").strip()
            discount_percent = int(discount_text)
        else:
            discount_percent = 0

        # Cover
        cover_tag = soup.select_one(".product-card--image img")
        cover_url = cover_tag["src"] if cover_tag else None

        return {
            "price": price,
            "original_price": original_price,
            "discount_percent": discount_percent,
            "is_free": price == 0.0,
            "cover_url": cover_url
        }

    except Exception:
        return None
    