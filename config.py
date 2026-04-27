"""
CarbonIQ – Configuration
All sensitive values are read from environment variables (.env via python-dotenv).
"""

import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    # ── Security ──────────────────────────────────────────────────────────────
    SECRET_KEY = os.environ.get("SECRET_KEY")

    # ── Database ──────────────────────────────────────────────────────────────
    MONGO_URI = os.environ.get("MONGO_URI")

    # ── App settings ──────────────────────────────────────────────────────────
    DEBUG = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
