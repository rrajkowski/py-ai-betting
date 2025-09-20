# api/index.py
from fastapi import FastAPI
from app.main import app as fastapi_app
from mangum import Mangum

# Wrap FastAPI with Mangum (for serverless)
handler = Mangum(fastapi_app)
