# Vercel entry point — imports the Flask app and exposes it as a WSGI handler.
# Vercel's Python runtime looks for a variable named 'app' or 'handler'.
import sys, os

# Make sure Python can find the backend package when running on Vercel
sys.path.insert(0, os.path.dirname(__file__))

from backend.app import app
