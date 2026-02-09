
import os

RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")
HEADERS = {
    "x-rapidapi-host": "odds.p.rapidapi.com",
    "x-rapidapi-key": RAPIDAPI_KEY,
}
