"""Flask API server for ebnbapredictor — deployed on Railway."""

from flask import Flask, jsonify, request
from flask_cors import CORS
from datetime import datetime
import os
import sys

# Ensure lib/ is importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

app = Flask(__name__)
CORS(app)

# In-memory cache keyed by date string
_cache = {}


def _build_tonight_features(top_players, games, stat_type):
    """Build a feature DataFrame for tonight's players for a given stat type."""
    from lib.data_collection import get_player_game_logs
    from lib.features import (
        build_features,
        add_opponent_features,
        add_player_advanced_features,
        add_position_defense,
        build_rebound_features,
        add_opponent_rebound_features,
        build_assist_features,
        add_opponent_assist_features,
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
    seasons = [current_season, "2024-25", "2023-24"]

    all_logs = []
    for _, player_row in tonight_players.iterrows():
        player_id = player_row["PLAYER_ID"]
        logs = get_player_game_logs(player_id, seasons=seasons)
        if logs is not None and len(logs) > 0:
            logs["PLAYER_ID"] = player_id
            logs["PLAYER_NAME"] = player_row["PLAYER"]
            team_abbr = team_id_to_abbr.get(player_row["TEAM_ID"], player_row.get("TEAM", ""))
            logs["TEAM"] = team_abbr
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
        team = str(row.get("TEAM", ""))
        if " vs. " in matchup:
            parts = matchup.split(" vs. ")
            return parts[1].strip() if len(parts) > 1 else ""
        elif " @ " in matchup:
            parts = matchup.split(" @ ")
            return parts[1].strip() if len(parts) > 1 else ""
        return game_abbr_map.get(team, "")

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

    if len(features_df) > 0:
        features_df = (
            features_df.sort_values("GAME_DATE_PARSED", ascending=False)
            if "GAME_DATE_PARSED" in features_df.columns
            else features_df
        )
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

    return features_df


@app.route("/api/predictions", methods=["GET"])
def predictions():
    today = datetime.now().strftime("%Y-%m-%d")

    if today in _cache:
        return jsonify(_cache[today])

    try:
        from lib.train import load_model as load_pts_model, FEATURE_COLS as PTS_FEATURE_COLS, MODEL_PATH as PTS_MODEL_PATH
        from lib.train_rebounds import load_model as load_reb_model, FEATURE_COLS as REB_FEATURE_COLS, MODEL_PATH as REB_MODEL_PATH
        from lib.train_assists import load_model as load_ast_model, FEATURE_COLS as AST_FEATURE_COLS, MODEL_PATH as AST_MODEL_PATH
        from lib.predict import get_todays_games, generate_predictions
        from lib.odds import fetch_all_props, compare_predictions_to_lines, build_parlays
        from lib.data_collection import get_top_scorers, get_top_rebounders, get_top_assisters

        models = {}
        for name, loader, cols, path in [
            ("Points", load_pts_model, PTS_FEATURE_COLS, PTS_MODEL_PATH),
            ("Rebounds", load_reb_model, REB_FEATURE_COLS, REB_MODEL_PATH),
            ("Assists", load_ast_model, AST_FEATURE_COLS, AST_MODEL_PATH),
        ]:
            if os.path.exists(path):
                try:
                    models[name] = (loader(path), cols)
                except Exception as e:
                    print(f"Failed to load {name} model: {e}")

        if not models:
            return jsonify({"error": "No trained models found."}), 503

        games = get_todays_games()
        if not games:
            result = {
                "games": [], "points": [], "rebounds": [], "assists": [],
                "parlays": [], "predictions_count": 0,
                "message": "No NBA games scheduled today.",
            }
            _cache[today] = result
            return jsonify(result)

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
                top_players = get_players_fn(season="2025-26", top_n=100)
                features_df = _build_tonight_features(top_players, games, stat_type)
                if features_df is None or len(features_df) == 0:
                    continue
                preds = generate_predictions(model, features_df, stat_type=stat_type, feature_cols=feature_cols)
                props = all_props.get(stat_type, [])
                compared = compare_predictions_to_lines(preds, props, stat_type=stat_type)
                results_list.extend(compared)
                all_comparisons.extend([c for c in compared if c.get("line") is not None])
            except Exception as e:
                print(f"Error generating {stat_type} predictions: {e}")

        parlays = build_parlays(all_comparisons) if all_comparisons else []

        result = {
            "games": games, "points": points_results, "rebounds": rebounds_results,
            "assists": assists_results, "parlays": parlays,
            "predictions_count": len(all_comparisons),
        }
        _cache[today] = result
        return jsonify(result)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/record", methods=["GET"])
def record():
    try:
        from lib.tracker import get_record, get_pending_dates

        days = request.args.get("days", type=int)
        rec = get_record(days=days)
        pending = get_pending_dates()
        return jsonify({"record": rec, "pending_dates": pending})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/history", methods=["GET"])
def history():
    try:
        from lib.tracker import get_history

        limit = request.args.get("limit", 60, type=int)
        date = request.args.get("date")
        hist = get_history(limit=limit, date=date)
        return jsonify({"history": hist, "count": len(hist)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/lock", methods=["POST"])
def lock():
    try:
        from lib.tracker import save_predictions

        payload = request.get_json(force=True, silent=True) or {}
        preds = payload.get("predictions", [])
        if not preds:
            return jsonify({"error": "No predictions provided."}), 400
        result = save_predictions(preds)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/update_results", methods=["POST"])
def update_results():
    try:
        from lib.tracker import fetch_and_update_actuals

        payload = request.get_json(force=True, silent=True) or {}
        date = payload.get("date")
        result = fetch_and_update_actuals(date=date)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/refresh_odds", methods=["GET"])
def refresh_odds():
    try:
        from lib.odds import fetch_all_props

        props = fetch_all_props()
        counts = {stat_type: len(prop_list) for stat_type, prop_list in props.items()}
        return jsonify({"counts": counts, "props": props})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)
