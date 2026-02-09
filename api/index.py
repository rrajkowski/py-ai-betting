# /api/index.py
from mangum import Mangum

from app.main import app

# Wrap FastAPI app for AWS Lambda
handler = Mangum(app)
