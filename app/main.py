from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import datetime
from app.db import init_db, get_db
from app.llm import get_probability
from app.odds_api import fetch_sports, fetch_odds

app = FastAPI(title="AI Betting API", version="0.1.0")
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


@app.get("/games/{sport}")
async def list_games(sport: str, region: str = "us", markets: str = "h2h,spreads,totals"):
    try:
        odds_data = await fetch_odds(sport=sport, region=region, markets=markets)

        normalized_games = []
        for game in odds_data:
            normalized_games.append({
                "sport": sport,
                "game_id": game.get("id"),
                "home_team": game.get("home_team"),
                "away_team": game.get("away_team"),
                "commence_time": game.get("commence_time"),
                "odds": {
                    "h2h": game.get("odds", {}).get("h2h", {}) or {},
                    "spreads": game.get("odds", {}).get("spreads", {}) or {},
                    "totals": game.get("odds", {}).get("totals", {}) or {}
                }
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
            """INSERT INTO bets
               (date, match, bet_type, odds, stake, probability, raw_output, outcome, profit)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (datetime.date.today().isoformat(),
             f"{matching['home_team']} vs {matching['away_team']}",
             req.market,
             odds_value,
             1.0,
             prob,
             raw_output,
             None,
             None)
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
