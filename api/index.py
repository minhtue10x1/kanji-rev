# -*- coding: utf-8 -*-
"""
Vercel Serverless Function Entrypoint for Kanji Master FastAPI backend.
"""

import sys
import os

# Ensure root directory is on sys.path for local module imports
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from server import app

# Automatically initialize database schema on startup / serverless cold start
try:
    from database import init_database
    init_database()
except Exception as e:
    print(f"Serverless database initialization warning: {e}")
