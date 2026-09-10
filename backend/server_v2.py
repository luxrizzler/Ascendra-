"""Additive server entrypoint for Virex's Ascendra Version 2.0.

Run with:
    uvicorn server_v2:app --host 0.0.0.0 --port 8001

The existing server.py remains unchanged so mainline Ascendra behavior is preserved.
"""
from server import app, current_user
from learning_v2 import build_router

app.title = "Virex's Ascendra Version 2.0 API"
app.include_router(build_router(current_user))
