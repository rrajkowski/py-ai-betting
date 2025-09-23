# api/index.py
from app.main import app  # FastAPI instance defined in main.py
from mangum import Mangum

# Create the Vercel-compatible handler
handler = Mangum(app)
