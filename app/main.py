# Compatibility entrypoint for platforms configured with `uvicorn app.main:app`.
from main import app

__all__ = ["app"]
