import xml.etree.ElementTree as ET
from urllib.parse import quote_plus

import httpx

from config import settings
from models import NewsItem


async def collect_market_data(sector: str, max_items: int = 8) -> list[NewsItem]:
    query = quote_plus(f"{sector} sector India")
    rss_url = f"https://news.google.com/rss/search?q={query}"

    timeout = httpx.Timeout(settings.request_timeout_seconds)
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        response = await client.get(rss_url)
        response.raise_for_status()

    root = ET.fromstring(response.text)
    items = []
    for item in root.findall("./channel/item")[:max_items]:
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        pub_date = (item.findtext("pubDate") or "").strip()
        source = (item.findtext("source") or "Google News").strip()
        description = (item.findtext("description") or "").strip()
        if not title or not link:
            continue
        items.append(
            NewsItem(
                title=title,
                link=link,
                published=pub_date,
                source=source,
                summary=description,
            )
        )
    return items
