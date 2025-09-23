# api/index.py
from app.main import app as fastapi_app
from mangum import Mangum

# Wrap FastAPI with Mangum (for serverless)
handler = Mangum(fastapi_app)
