#!/usr/bin/env python3
"""Celery worker runner for development."""

import sys
from celery import Celery
from app.celery_app import celery_app


if __name__ == "__main__":
    # Run celery worker with development settings
    sys.argv = [
        "celery",
        "-A", "app.celery_app",
        "worker",
        "--loglevel=info",
        "--concurrency=2",
        "--pool=solo" if sys.platform == "win32" else "--pool=prefork"
    ]
    
    celery_app.start()