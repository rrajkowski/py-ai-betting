# /api/index.py
from app.main import app
from mangum import Mangum

# Wrap FastAPI app for AWS Lambda / Vercel
handler = Mangum(app)
