"""Run locally to generate today's predictions and save to data/predictions.json.

Usage:
    python generate_predictions.py

This fetches NBA data, runs the ML models, and saves results as JSON.
Commit and push data/predictions.json, then Railway serves it statically.
"""
import json
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from lib.predict import get_todays_games, generate_predictions
from lib.odds import fetch_all_props, compare_predictions_to_lines, build_parlays
from lib.data_collection import get_top_scorers, get_top_rebounders, get_top_assisters


def _build_tonight_features(top_players, games, stat_type):
    from lib.data_collection import get_player_game_logs
    from lib.features import (
        build_features, add_opponent_features, add_player_advanced_features,
        add_position_defense, build_rebound_features, add_opponent_rebound_features,
        build_assist_features, add_opponent_assist_features,
    )
    from nba_api.stats.static import teams as nba_teams
    import pandas as pd

    team_id_to_abbr = {t["id"]: t["abbreviation"] for t in nba_teams.get_teams()}

    tonight_team_ids = set()
    for game in games:
        tonight_team_ids.add(game["home_team_id"])
        tonight_team_ids.add(game["away_team_id"])

    tonight_players = top_players[top_players["TEAM_ID"].isin(tonight_team_ids)]
    if len(tonight_players) == 0:
        return None

    current_season = "2025-26"
    seasons = [current_season]

    # Save player identity before feature building
    player_id_map = {}

    all_logs = []
    for _, player_row in tonight_players.iterrows():
        player_id = player_row["PLAYER_ID"]
        player_id_map[player_id] = {
            "PLAYER_NAME": player_row["PLAYER"],
            "TEAM": team_id_to_abbr.get(player_row["TEAM_ID"], player_row.get("TEAM", "")),
        }
        logs = get_player_game_logs(player_id, seasons=seasons)
        if logs is not None and len(logs) > 0:
            logs["PLAYER_ID"] = player_id
            logs["PLAYER_NAME"] = player_row["PLAYER"]
            logs["TEAM"] = team_id_to_abbr.get(player_row["TEAM_ID"], player_row.get("TEAM", ""))
            all_logs.append(logs)

    if not all_logs:
        return None

    combined_logs = pd.concat(all_logs, ignore_index=True)

    game_abbr_map = {}
    for game in games:
        game_abbr_map[game["home_abbr"]] = game["away_abbr"]
        game_abbr_map[game["away_abbr"]] = game["home_abbr"]

    def _get_opponent(row):
        matchup = str(row.get("MATCHUP", ""))
        if " vs. " in matchup:
            return matchup.split(" vs. ")[1].strip()
        elif " @ " in matchup:
            return matchup.split(" @ ")[1].strip()
        return game_abbr_map.get(str(row.get("TEAM", "")), "")

    combined_logs["OPPONENT"] = combined_logs.apply(_get_opponent, axis=1)
    combined_logs["MATCHUP"] = combined_logs.get("MATCHUP", "")

    try:
        if stat_type == "Points":
            features_df = build_features(combined_logs)
            features_df = add_opponent_features(features_df, season=current_season)
            features_df = add_player_advanced_features(features_df, season=current_season)
            try:
                features_df = add_position_defense(features_df, season=current_season)
            except Exception:
                features_df["opp_pos_pts_allowed"] = 38.0
        elif stat_type == "Rebounds":
            features_df = build_rebound_features(combined_logs)
            features_df = add_opponent_features(features_df, season=current_season)
            features_df = add_player_advanced_features(features_df, season=current_season)
            features_df = add_opponent_rebound_features(features_df, season=current_season)
            try:
                features_df = add_position_defense(features_df, season=current_season)
            except Exception:
                features_df["opp_pos_reb_allowed"] = 10.0
        elif stat_type == "Assists":
            features_df = build_assist_features(combined_logs)
            features_df = add_opponent_features(features_df, season=current_season)
            features_df = add_player_advanced_features(features_df, season=current_season)
            features_df = add_opponent_assist_features(features_df, season=current_season)
        else:
            return None
    except Exception as e:
        print(f"Feature building failed for {stat_type}: {e}")
        return None

    # Restore player names if lost
    if "PLAYER_NAME" not in features_df.columns and "PLAYER_ID" in features_df.columns:
        features_df["PLAYER_NAME"] = features_df["PLAYER_ID"].map(
            lambda pid: player_id_map.get(pid, {}).get("PLAYER_NAME", "Unknown")
        )
    if "TEAM" not in features_df.columns and "PLAYER_ID" in features_df.columns:
        features_df["TEAM"] = features_df["PLAYER_ID"].map(
            lambda pid: player_id_map.get(pid, {}).get("TEAM", "")
        )

    if len(features_df) > 0:
        if "GAME_DATE_PARSED" in features_df.columns:
            features_df = features_df.sort_values("GAME_DATE_PARSED", ascending=False)
        features_df = features_df.drop_duplicates(
            subset=["PLAYER_NAME"] if "PLAYER_NAME" in features_df.columns else features_df.columns[:1],
            keep="first",
        )

    team_to_opponent = {}
    home_teams = set()
    for game in games:
        team_to_opponent[game["home_abbr"]] = game["away_abbr"]
        team_to_opponent[game["away_abbr"]] = game["home_abbr"]
        home_teams.add(game["home_abbr"])

    if "TEAM" in features_df.columns and "OPPONENT" not in features_df.columns:
        features_df["OPPONENT"] = features_df["TEAM"].map(team_to_opponent).fillna("")
    if "TEAM" in features_df.columns and "home_away" not in features_df.columns:
        features_df["home_away"] = features_df["TEAM"].apply(lambda t: 1 if t in home_teams else 0)

    # Build last_5_<stat> column from raw game logs
    stat_col_map = {"Points": "PTS", "Rebounds": "REB", "Assists": "AST"}
    last5_col_map = {"Points": "last_5_pts", "Rebounds": "last_5_reb", "Assists": "last_5_ast"}
    game_stat_col = stat_col_map.get(stat_type)
    last5_col_name = last5_col_map.get(stat_type)
    if game_stat_col and last5_col_name and "PLAYER_ID" in features_df.columns:
        last5_map = {}
        for pid, group in combined_logs.groupby("PLAYER_ID"):
            sorted_logs = group.sort_values("GAME_DATE", ascending=False).head(5)
            vals = sorted_logs[game_stat_col].astype(int).tolist() if game_stat_col in sorted_logs.columns else []
            last5_map[pid] = ",".join(str(v) for v in vals)
        features_df[last5_col_name] = features_df["PLAYER_ID"].map(last5_map).fillna("")

    return features_df


def main():
    from lib.train import load_model as load_pts_model, FEATURE_COLS as PTS_FEATURE_COLS, MODEL_PATH as PTS_MODEL_PATH
    from lib.train_rebounds import load_model as load_reb_model, FEATURE_COLS as REB_FEATURE_COLS, MODEL_PATH as REB_MODEL_PATH
    from lib.train_assists import load_model as load_ast_model, FEATURE_COLS as AST_FEATURE_COLS, MODEL_PATH as AST_MODEL_PATH

    today = datetime.now().strftime("%Y-%m-%d")
    print(f"Generating predictions for {today}...")

    # Load models
    models = {}
    for name, loader, cols, path in [
        ("Points", load_pts_model, PTS_FEATURE_COLS, PTS_MODEL_PATH),
        ("Rebounds", load_reb_model, REB_FEATURE_COLS, REB_MODEL_PATH),
        ("Assists", load_ast_model, AST_FEATURE_COLS, AST_MODEL_PATH),
    ]:
        if os.path.exists(path):
            try:
                models[name] = (loader(path), cols)
                print(f"  Loaded {name} model")
            except Exception as e:
                print(f"  Failed to load {name} model: {e}")

    if not models:
        print("No trained models found!")
        return

    # Get today's games
    games = get_todays_games()
    if not games:
        result = {
            "date": today,
            "games": [], "points": [], "rebounds": [], "assists": [],
            "parlays": [], "predictions_count": 0,
            "message": "No NBA games scheduled today.",
        }
    else:
        print(f"  Found {len(games)} games today")

        all_props = fetch_all_props()
        all_comparisons = []
        points_results, rebounds_results, assists_results = [], [], []

        stat_configs = {
            "Points": (get_top_scorers, points_results),
            "Rebounds": (get_top_rebounders, rebounds_results),
            "Assists": (get_top_assisters, assists_results),
        }

        for stat_type, (get_players_fn, results_list) in stat_configs.items():
            if stat_type not in models:
                continue
            model, feature_cols = models[stat_type]
            try:
                print(f"  Generating {stat_type} predictions...")
                top_players = get_players_fn(season="2025-26", top_n=50)
                features_df = _build_tonight_features(top_players, games, stat_type)
                if features_df is None or len(features_df) == 0:
                    print(f"    No features for {stat_type}")
                    continue
                preds = generate_predictions(model, features_df, stat_type=stat_type, feature_cols=feature_cols)
                props = all_props.get(stat_type, [])
                compared = compare_predictions_to_lines(preds, props, stat_type=stat_type)
                results_list.extend(compared)
                all_comparisons.extend([c for c in compared if c.get("line") is not None])
                print(f"    {len(compared)} {stat_type} predictions")
            except Exception as e:
                print(f"    Error in {stat_type}: {e}")
                import traceback
                traceback.print_exc()

        parlays = build_parlays(all_comparisons) if all_comparisons else []

        result = {
            "date": today,
            "games": games,
            "points": points_results,
            "rebounds": rebounds_results,
            "assists": assists_results,
            "parlays": parlays,
            "predictions_count": len(all_comparisons),
        }

    # Save to data/predictions.json
    os.makedirs("data", exist_ok=True)
    output_path = os.path.join("data", "predictions.json")
    with open(output_path, "w") as f:
        json.dump(result, f, default=str, indent=2)

    print(f"\nSaved to {output_path}")
    print(f"  {len(result.get('points', []))} points, {len(result.get('rebounds', []))} rebounds, {len(result.get('assists', []))} assists")
    print(f"  {result.get('predictions_count', 0)} with PrizePicks lines")
    print(f"\nRun: git add data/predictions.json && git commit -m 'update predictions {today}' && git push")


if __name__ == "__main__":
    main()
