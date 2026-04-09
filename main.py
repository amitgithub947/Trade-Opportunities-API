import logging
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse

from config import settings
from security import AuthDependency, RateLimitDependency, validate_sector_name
from services.ai_analyzer import generate_markdown_report
from services.data_collector import collect_market_data


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    logger.info("Starting %s", settings.app_name)
    yield
    logger.info("Shutting down %s", settings.app_name)


app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description="Single-endpoint API for trade opportunity analysis by sector in India.",
    lifespan=lifespan,
)


@app.get("/", response_class=HTMLResponse)
async def root():
        return """
        <html>
            <head>
                <title>Trade Opportunities API</title>
                <style>
                    :root {
                        --bg: #f3f6fb;
                        --card: #ffffff;
                        --text: #1f2937;
                        --muted: #6b7280;
                        --primary: #0f766e;
                        --primary-dark: #0b5f59;
                    }

                    * {
                        box-sizing: border-box;
                    }

                    body {
                        margin: 0;
                        min-height: 100vh;
                        font-family: "Segoe UI", Tahoma, sans-serif;
                        background: linear-gradient(135deg, #eaf4ff 0%, var(--bg) 50%, #eefaf5 100%);
                        color: var(--text);
                        display: grid;
                        place-items: center;
                        padding: 24px;
                    }

                    .card {
                        width: min(640px, 100%);
                        background: var(--card);
                        border-radius: 16px;
                        padding: 28px;
                        box-shadow: 0 12px 30px rgba(15, 23, 42, 0.12);
                        border: 1px solid rgba(15, 118, 110, 0.15);
                    }

                    h1 {
                        margin: 0 0 10px;
                        font-size: 2rem;
                        line-height: 1.2;
                    }

                    p {
                        margin: 0 0 18px;
                        color: var(--muted);
                    }

                    .links {
                        display: flex;
                        gap: 10px;
                        flex-wrap: wrap;
                    }

                    .btn {
                        text-decoration: none;
                        background: var(--primary);
                        color: #fff;
                        padding: 10px 14px;
                        border-radius: 10px;
                        font-weight: 600;
                        transition: background 0.2s ease;
                    }

                    .btn:hover {
                        background: var(--primary-dark);
                    }
                </style>
            </head>
            <body>
                <main class="card">
                    <h1>Trade Opportunities API</h1>
                    <p>Service is running.</p>
                    <div class="links">
                        <a class="btn" href="/health">Health check</a>
                        <a class="btn" href="/docs">API docs</a>
                    </div>
                </main>
            </body>
        </html>
        """


@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response


@app.get("/health")
async def health():
    return {"status": "ok", "app": settings.app_name, "env": settings.app_env}


@app.get("/analyze/{sector}", response_class=PlainTextResponse)
async def analyze_sector(
    sector: str,
    request: Request,
    _auth: None = AuthDependency,
    session_id: str = RateLimitDependency,
):
    cleaned_sector = validate_sector_name(sector)
    try:
        market_items = await collect_market_data(cleaned_sector)
        markdown_report = generate_markdown_report(cleaned_sector, market_items)
    except httpx.HTTPError as exc:
        logger.exception("External data fetch failed")
        raise HTTPException(
            status_code=502,
            detail=f"Failed to fetch market data: {exc.__class__.__name__}",
        ) from exc
    except Exception as exc:
        logger.exception("Unexpected failure")
        raise HTTPException(status_code=500, detail="Unexpected internal error.") from exc

    response = PlainTextResponse(content=markdown_report, status_code=200)
    if not request.cookies.get("session_id"):
        response.set_cookie(
            key="session_id",
            value=session_id,
            httponly=True,
            secure=False,
            samesite="lax",
        )
    return response


@app.exception_handler(HTTPException)
async def http_exception_handler(_: Request, exc: HTTPException):
    return JSONResponse(status_code=exc.status_code, content={"error": exc.detail})
