import time
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from nba_api.stats.endpoints import ScoreboardV2
from nba_api.stats.static import teams as nba_teams


def get_todays_games():
    """Get list of today's NBA games."""
    today = datetime.now().strftime("%Y-%m-%d")

    time.sleep(0.6)
    scoreboard = ScoreboardV2(game_date=today)
    games_df = scoreboard.get_data_frames()[0]

    if len(games_df) == 0:
        return []

    team_map = {}
    for team in nba_teams.get_teams():
        team_map[team["id"]] = team["abbreviation"]
        team_map[team["abbreviation"]] = team["full_name"]

    games = []
    for _, row in games_df.iterrows():
        home_id = row["HOME_TEAM_ID"]
        away_id = row["VISITOR_TEAM_ID"]
        games.append({
            "game_id": row["GAME_ID"],
            "home_team": team_map.get(home_id, str(home_id)),
            "home_team_id": home_id,
            "away_team": team_map.get(away_id, str(away_id)),
            "away_team_id": away_id,
            "home_abbr": team_map.get(home_id, ""),
            "away_abbr": team_map.get(away_id, ""),
        })

    return games


def _build_key_factors(row, stat_type="Points"):
    """Generate human-readable key factors for a prediction."""
    factors = []

    if stat_type == "Points":
        avg5 = row.get("ppg_last_5", 0)
        season = row.get("season_ppg", 0)
        label = "PPG"
    elif stat_type == "Rebounds":
        avg5 = row.get("rpg_last_5", 0)
        season = row.get("season_rpg", 0)
        label = "RPG"
    else:  # Assists
        avg5 = row.get("apg_last_5", 0)
        season = row.get("season_apg", 0)
        label = "APG"

    if avg5 > 0:
        factors.append(f"Averaging {avg5:.1f} {label} over last 5 games")

    if season > 0 and abs(avg5 - season) > (2 if stat_type == "Points" else 1):
        direction = "above" if avg5 > season else "below"
        factors.append(f"Trending {direction} season average ({season:.1f})")

    opp = row.get("opp_def_rating", 0)
    if opp > 112:
        factors.append(f"Opponent allows more ({stat_type.lower()}, DEF RTG: {opp:.1f})")
    elif opp < 108:
        factors.append(f"Tough defensive opponent (DEF RTG: {opp:.1f})")

    rest = row.get("rest_days", 0)
    b2b = row.get("is_b2b", 0)
    if b2b:
        factors.append("Back-to-back game")
    elif rest >= 3:
        factors.append(f"Well-rested ({int(rest)} days off)")

    pace = row.get("game_pace", 0)
    if pace > 102:
        factors.append(f"High-pace matchup ({pace:.1f})")
    elif pace < 97:
        factors.append(f"Slow-pace matchup ({pace:.1f})")

    usg = row.get("usage_rate", 0)
    if usg > 0.28:
        factors.append(f"High usage ({usg:.1%})")

    home = row.get("home_away", 0)
    if home == 1:
        factors.append("Home game")

    min_trend = row.get("minutes_trend", 0)
    if min_trend > 2:
        factors.append(f"Minutes trending up (+{min_trend:.1f} min)")
    elif min_trend < -2:
        factors.append(f"Minutes trending down ({min_trend:.1f} min)")

    return factors[:3]


def generate_predictions(model, player_features_df, stat_type="Points", feature_cols=None):
    """Generate predictions for any stat type.

    Args:
        model: Trained ensemble model
        player_features_df: DataFrame with features
        stat_type: "Points", "Rebounds", or "Assists"
        feature_cols: List of feature column names (from the model's training module)

    Returns list of prediction dicts.
    """
    if len(player_features_df) == 0:
        return []

    if feature_cols is None:
        from lib.train import FEATURE_COLS
        feature_cols = FEATURE_COLS

    # Ensure all feature cols exist (except predicted_minutes — the model handles that)
    df = player_features_df.copy()
    for col in feature_cols:
        if col not in df.columns and col != "predicted_minutes":
            df[col] = 0

    predicted_vals = model.predict(df)

    # Determine field names
    if stat_type == "Points":
        pred_key = "predicted_pts"
        avg5_key = "ppg_last_5"
        season_key = "season_ppg"
        last5_col = "last_5_pts"
        stat_col = "PTS"
    elif stat_type == "Rebounds":
        pred_key = "predicted_reb"
        avg5_key = "rpg_last_5"
        season_key = "season_rpg"
        last5_col = "last_5_reb"
        stat_col = "REB"
    else:
        pred_key = "predicted_ast"
        avg5_key = "apg_last_5"
        season_key = "season_apg"
        last5_col = "last_5_ast"
        stat_col = "AST"

    predictions = []
    for i, (_, row) in enumerate(df.iterrows()):
        last_5_raw = row.get(last5_col, "")
        last_5_list = [int(x) for x in str(last_5_raw).split(",") if x.strip().isdigit()]

        pred = {
            "player_name": row.get("PLAYER_NAME", "Unknown"),
            "team": row.get("TEAM", ""),
            "opponent": row.get("OPPONENT", ""),
            "matchup": row.get("MATCHUP", ""),
            "stat_type": stat_type,
            pred_key: round(float(predicted_vals[i]), 1),
            "key_factors": _build_key_factors(row, stat_type),
            "last_5_games": last_5_list,
            avg5_key: round(float(row.get(avg5_key, 0)), 1),
            season_key: round(float(row.get(season_key, 0)), 1),
        }
        predictions.append(pred)

    return predictions
