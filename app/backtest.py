import pandas as pd


def run_backtest(csv_file, strategy_func):
    df = pd.read_csv(csv_file)
    results = []
    for _, row in df.iterrows():
        prob = strategy_func(row)
        ev = (prob * (row.odds - 1)) - (1 - prob)
        profit = (row.odds_american - 1) if row.outcome == "win" else -1
        results.append({"match": row.match, "ev": ev, "profit": profit})
    return pd.DataFrame(results)
