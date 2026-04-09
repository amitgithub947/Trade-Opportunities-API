import datetime as dt
import logging

from google import genai

from app.config import settings
from app.models import NewsItem


logger = logging.getLogger(__name__)


def _build_prompt(sector: str, items: list[NewsItem]) -> str:
    bullets = []
    for item in items:
        bullets.append(
            f"- Title: {item.title}\n"
            f"  Source: {item.source}\n"
            f"  Date: {item.published}\n"
            f"  Link: {item.link}"
        )
    joined = "\n".join(bullets)
    return f"""
You are a market analyst focused on Indian sectors.
Analyze this data and return ONLY markdown.

Sector: {sector}
Date: {dt.datetime.utcnow().strftime("%Y-%m-%d")}

News Data:
{joined}

Output structure:
# Trade Opportunities Report: <sector title>
## Market Pulse
## Key Signals
## Trade Opportunities (Short-term)
## Risks
## Suggested Watchlist
## Sources
"""


def _fallback_report(sector: str, items: list[NewsItem]) -> str:
    lines = [
        f"# Trade Opportunities Report: {sector.title()}",
        "",
        "## Market Pulse",
        "Recent headlines indicate active movement in this sector in India.",
        "",
        "## Key Signals",
    ]
    for item in items[:5]:
        lines.append(f"- {item.title} ({item.source})")
    lines += [
        "",
        "## Trade Opportunities (Short-term)",
        "- Momentum opportunities around news-driven stocks in this sector.",
        "- Watch for companies with strong order books, policy tailwinds, or earnings upgrades.",
        "",
        "## Risks",
        "- Headline volatility and macroeconomic uncertainty.",
        "- Policy delays, commodity price spikes, and global market spillovers.",
        "",
        "## Suggested Watchlist",
        "- Top listed players in the sector by market cap and volume.",
        "- Mid-cap stocks with improving earnings guidance.",
        "",
        "## Sources",
    ]
    for item in items:
        lines.append(f"- [{item.title}]({item.link})")
    return "\n".join(lines)


def generate_markdown_report(sector: str, items: list[NewsItem]) -> str:
    if not items:
        return (
            f"# Trade Opportunities Report: {sector.title()}\n\n"
            "No recent market data found for this sector. Try a different sector name."
        )

    if not settings.gemini_api_key:
        return _fallback_report(sector, items)

    try:
        client = genai.Client(api_key=settings.gemini_api_key)
        prompt = _build_prompt(sector, items)
        response = client.models.generate_content(
            model=settings.gemini_model,
            contents=prompt,
        )
        text = (response.text or "").strip()
        if not text:
            return _fallback_report(sector, items)
        return text
    except Exception:
        logger.exception("Gemini generation failed, returning fallback report")
        return _fallback_report(sector, items)
