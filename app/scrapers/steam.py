import httpx


STEAM_API = "https://store.steampowered.com/api/appdetails"


async def get_steam_price(app_id: str) -> dict | None:
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(
                STEAM_API,
                params={"appids": app_id, "cc": "br", "l": "portuguese"},
                timeout=10.0
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception:
            return None

    game_data = data.get(str(app_id), {})
    if not game_data.get("success"):
        return None

    details = game_data.get("data", {})
    price_overview = details.get("price_overview")

    if not price_overview:
        # Jogo gratuito
        if details.get("is_free"):
            return {
                "price": 0.0,
                "original_price": 0.0,
                "discount_percent": 0,
                "is_free": True,
                "cover_url": details.get("header_image")
            }
        return None

    return {
        "price": price_overview["final"] / 100,
        "original_price": price_overview["initial"] / 100,
        "discount_percent": price_overview["discount_percent"],
        "is_free": False,
        "cover_url": details.get("header_image")
    }
