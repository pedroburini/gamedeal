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
        # Preço atual — agora vem quebrado em spans separadas (integer + decimal)
        price_container = soup.select_one(".product-price--val")
        if not price_container:
            return None

        integer_tag = price_container.select_one(".integer")
        decimal_tag = price_container.select_one(".decimal")
        if not integer_tag or not decimal_tag:
            return None

        integer_part = integer_tag.get_text(strip=True)
        decimal_part = decimal_tag.get_text(strip=True).replace(",", "").strip()
        price = float(f"{integer_part}.{decimal_part}")

        # Preço original (riscado) — agora fica ANINHADO dentro de .product-price--val,
        # não mais como elemento irmão separado
        old_tag = price_container.select_one(".product-price--old")
        if old_tag:
            original_text = (
                old_tag.get_text(strip=True)
                .replace("R$", "")
                .replace(".", "")   # remove separador de milhar
                .replace(",", ".")  # vírgula decimal -> ponto
                .strip()
            )
            original_price = float(original_text)
        else:
            original_price = price

        # A Nuuvem não expõe mais um elemento dedicado ao percentual de desconto
        # nessa estrutura — calculamos direto a partir dos dois preços.
        if original_price > price > 0:
            discount_percent = round((1 - price / original_price) * 100)
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
