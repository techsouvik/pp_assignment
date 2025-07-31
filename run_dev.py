#!/usr/bin/env python3
"""Development server runner for the PR Analyzer application."""

import uvicorn
from app.config import settings


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True,
        reload_dirs=["app"],
        log_level=settings.log_level.lower()
    )