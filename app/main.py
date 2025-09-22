from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import datetime
from app.db import init_db, get_db
from app.llm import get_probability
from app.odds_api import fetch_sports, fetch_odds
import os
import requests

app = FastAPI(title="AI Betting API", version="0.1.0")

# Load Odds API key from environment
ODDS_API_KEY = os.getenv("ODDS_API_KEY")
if not ODDS_API_KEY:
    raise ValueError("ODDS_API_KEY environment variable not set")

init_db()


class BetRequest(BaseModel):
    game_id: str
    sport: str
    market: str        # e.g. "h2h", "spreads", "totals"
    side: str          # e.g. “home_team” or “away_team” or other label in outcomes
    stats: dict        # additional stats if desired


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


@app.get("/games/{sport}")
async def list_games(sport: str, region: str = "us", markets: str = "h2h,spreads,totals"):
    try:
        url = f"https://api.the-odds-api.com/v4/sports/{sport}/odds"
        params = {
            "apiKey": ODDS_API_KEY,
            "regions": region,
            "markets": markets,
            "oddsFormat": "decimal",
        }
        resp = requests.get(url, params=params)
        if resp.status_code != 200:
            raise HTTPException(status_code=resp.status_code, detail=resp.text)

        odds_data = resp.json()

        normalized_games = []
        for game in odds_data:
            normalized_games.append({
                "sport": sport,
                "game_id": game.get("id"),
                "home_team": game.get("home_team"),
                "away_team": game.get("away_team"),
                "commence_time": game.get("commence_time"),
                "odds": parse_odds(game)  # ✅ consistent schema
            })

        return {"games": normalized_games}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/sports")
async def list_sports():
    return await fetch_sports()


@app.get("/odds")
async def get_odds(sport: str = "soccer_epl", region: str = "us", markets: str = "h2h,spreads,totals"):
    markets_list = [m.strip() for m in markets.split(",")]
    return await fetch_odds(sport, region, markets_list)


@app.post("/bets/suggest")
async def suggest_bet(req: BetRequest):
    # fetch the games list for that sport + markets
    odds_data = await fetch_odds(sport=req.sport, region="us", markets=[req.market])
    # find matching game
    matching = next(
        (ev for ev in odds_data if ev.get("id") == req.game_id), None)
    if not matching:
        raise HTTPException(status_code=404, detail="Game not found")
    # find a bookmaker and outcome price
    # pick first bookmaker
    bm = matching["bookmakers"][0]
    market_obj = next(
        (m for m in bm["markets"] if m["key"] == req.market), None)
    if not market_obj:
        raise HTTPException(
            status_code=404, detail=f"Market {req.market} not available for this game")
    outcome = next(
        (o for o in market_obj["outcomes"] if o["name"] == req.side), None)
    if not outcome:
        raise HTTPException(
            status_code=404, detail=f"Side '{req.side}' not found among outcomes")
    odds_value = outcome["price"]

    prob_data = await get_probability(matching["home_team"] + " vs " + matching["away_team"],
                                      odds_value, req.market, req.stats)
    prob, raw_output = prob_data["parsed"], prob_data["raw_output"]
    ev = (prob * (odds_value - 1)) - (1 - prob)
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute(
            """
    INSERT INTO bets (date, match, bet_type, odds, stake, probability, raw_output, outcome, profit, expected_value)
    VALUES (?,?,?,?,?,?,?,?,?,?)
    """,
            (
                datetime.date.today().isoformat(),
                req.match,
                req.bet_type,
                req.odds,
                1.0,
                prob,
                raw_output,
                None,  # outcome
                None,  # profit
                ev     # expected value
            ),
        )
        bet_id = cur.lastrowid
    return {"bet_id": bet_id, "probability": prob, "expected_value": ev, "raw_output": raw_output}


@app.post("/bets/result")
async def record_result(res: BetResult):
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT odds, stake FROM bets WHERE id=?", (res.bet_id,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Bet not found")
        odds, stake = row
        profit = (stake * (odds - 1)) if res.outcome == "win" else -stake
        cur.execute("UPDATE bets SET outcome=?, profit=? WHERE id=?",
                    (res.outcome, profit, res.bet_id))
    return {"bet_id": res.bet_id, "profit": profit}
