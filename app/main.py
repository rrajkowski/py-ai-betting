from mangum import Mangum  # allows ASGI on serverless
from fastapi import FastAPI
import sqlite3
from fastapi import HTTPException
from pydantic import BaseModel
from typing import Optional, Dict
from app.db import DB_PATH, init_db, get_db
import sys
import os
sys.path.append(os.path.dirname(__file__))

app = FastAPI(title="AI Betting API", version="0.1.0")
handler = Mangum(app)

init_db()


@app.get("/api")
async def health():
    return {"status": "ok"}


@app.get("/bets")
def list_bets():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM bets ORDER BY date DESC")
    rows = [dict(row) for row in cur.fetchall()]
    conn.close()
    return {"bets": rows}


class Bet(BaseModel):
    team: str
    opponent: str
    market: str


@app.post("/bets")
def create_bet(bet: Bet):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO bets (team, opponent, market, date) VALUES (?, ?, ?, CURRENT_TIMESTAMP)",
        (bet.team, bet.opponent, bet.market),
    )
    conn.commit()
    conn.close()
    return {"message": "Bet saved", "bet": bet.dict()}


@app.post("/probability")
def probability(payload: dict):
    question = payload.get("question", "")
    # TODO: wire to your LLM
    return {"question": question, "probability": 0.5}


class BetRequest(BaseModel):
    match: str
    game_id: str
    sport: str
    market: str        # "h2h", "spreads", "totals"
    side: str          # e.g. "home_team", "away_team", or team name
    bet_type: str
    odds: float        # required to calculate EV
    odds_american: Optional[float] = None  # ✅ optional, American
    stake: Optional[float] = 1.0
    stats: Optional[Dict] = None  # ✅ optional, defaults to {}


class BetResult(BaseModel):
    bet_id: int
    outcome: str


class Game(BaseModel):
    sport: str
    game_id: str     # use `id` from Odds API
    home_team: str
    away_team: str
    # e.g. {"h2h": {"home": 1.8, "away": 2.0}, "spreads": ..., "totals": ...}
    odds: dict


def parse_odds(game):
    odds = {"h2h": {}, "spreads": {}, "totals": {}}
    for bm in game.get("bookmakers", []):
        for market in bm.get("markets", []):
            key = market.get("key")
            if key in odds:
                # Convert outcomes list -> {name: price}
                odds[key] = {o["name"]: o["price"]
                             for o in market.get("outcomes", [])}
    return odds


@app.post("/bets/result")
async def record_result(res: BetResult):
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT odds, stake FROM bets WHERE id=?", (res.bet_id,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Bet not found")

        odds, stake = row
        outcome = res.outcome.lower().strip()

        # --- NEW: Include 'push' handling ---
        if outcome == "win":
            profit = stake * (odds - 1)
        elif outcome == "loss":
            profit = -stake
        elif outcome == "push":
            profit = 0.0
        else:
            raise HTTPException(
                status_code=400, detail=f"Invalid outcome '{outcome}'")

        cur.execute(
            "UPDATE bets SET outcome=?, profit=? WHERE id=?",
            (outcome, profit, res.bet_id),
        )
        conn.commit()

    return {
        "bet_id": res.bet_id,
        "outcome": outcome,
        "profit": profit,
        "units": 0 if outcome == "push" else profit / stake if stake else 0,
    }
