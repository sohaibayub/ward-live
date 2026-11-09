"""Vercel entry point. Vercel's Python runtime looks for an ASGI app here."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("WARD_DATA", "/tmp/ward-data")  # the only writable place on Vercel; not persistent

from app import app  # noqa: E402,F401
