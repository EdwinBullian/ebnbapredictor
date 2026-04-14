"""Train playoff-specific models for Points, Rebounds, and Assists.

Uses the same ensemble architecture (XGBoost + LightGBM + Ridge) as regular season
models, but trained exclusively on playoff game log data.

Usage:
    python -m lib.train_playoffs          # from ebnbapredictor/
    python lib/train_playoffs.py          # from ebnbapredictor/

Models are saved to models/xgb_*_model_playoffs.joblib
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lib.data_collection import (
    get_top_scorers, get_top_rebounders, get_top_assisters,
    collect_all_game_logs,
)
from lib.features import (
    build_features, add_opponent_features, add_player_advanced_features, add_position_defense,
    build_rebound_features, add_opponent_rebound_features,
    build_assist_features, add_opponent_assist_features,
)
from lib.train import (
    train_model as train_pts_model, save_model as save_pts_model,
    FEATURE_COLS as PTS_FEATURE_COLS,
)
from lib.train_rebounds import (
    train_model as train_reb_model, save_model as save_reb_model,
    FEATURE_COLS as REB_FEATURE_COLS,
)
from lib.train_assists import (
    train_model as train_ast_model, save_model as save_ast_model,
    FEATURE_COLS as AST_FEATURE_COLS,
)

MODELS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "models")

# Playoff model paths
PTS_PLAYOFF_PATH = os.path.join(MODELS_DIR, "xgb_scoring_model_playoffs.joblib")
REB_PLAYOFF_PATH = os.path.join(MODELS_DIR, "xgb_rebounds_model_playoffs.joblib")
AST_PLAYOFF_PATH = os.path.join(MODELS_DIR, "xgb_assists_model_playoffs.joblib")

# Playoff seasons — 5 seasons gives enough data without hammering the API
PLAYOFF_SEASONS = ["2025-26", "2024-25", "2023-24", "2022-23", "2021-22"]
CURRENT_SEASON = "2025-26"
SEASON_TYPE = "Playoffs"


def train_points_playoffs():
    """Train playoff points model."""
    print("\n" + "=" * 60)
    print("  POINTS — Playoff Model")
    print("=" * 60)

    print("\nStep 1: Getting top scorers (regular season leaders who play in playoffs)...")
    # Use regular season leaders to identify the player pool,
    # then fetch their playoff game logs
    scorers = get_top_scorers(season=CURRENT_SEASON, top_n=50)
    print(f"  Found {len(scorers)} players")

    print("\nStep 2: Collecting PLAYOFF game logs...")
    logs = collect_all_game_logs(
        scorers,
        cache_path="data/game_logs/all_logs_pts_playoffs.csv",
        seasons=PLAYOFF_SEASONS,
        force_refresh=True,
        season_type=SEASON_TYPE,
    )
    if len(logs) == 0:
        print("  No playoff game logs found! Skipping points model.")
        return None, None
    print(f"  Collected {len(logs)} playoff game log entries")

    print("\nStep 3: Engineering features...")
    features = build_features(logs)
    print(f"  Base features: {len(features)} rows, {len(features.columns)} cols")
    features = add_opponent_features(features, season=CURRENT_SEASON)
    print("  + Opponent features")
    features = add_player_advanced_features(features, season=CURRENT_SEASON)
    print("  + Player advanced features")
    try:
        features = add_position_defense(features, season=CURRENT_SEASON)
        print("  + Position defense")
    except Exception as e:
        print(f"  ! Position defense skipped: {e}")
        features["opp_pos_pts_allowed"] = 38.0
    print(f"  Final: {len(features)} rows, {len(PTS_FEATURE_COLS)} scoring features")

    print("\nStep 4: Training model...")
    model, metrics = train_pts_model(features)
    print(f"\n  Playoff PTS — MAE: {metrics['mae']:.2f}, R²: {metrics['r2']:.3f}")

    print("\nStep 5: Saving playoff points model...")
    save_pts_model(model, path=PTS_PLAYOFF_PATH)
    return model, metrics


def train_rebounds_playoffs():
    """Train playoff rebounds model."""
    print("\n" + "=" * 60)
    print("  REBOUNDS — Playoff Model")
    print("=" * 60)

    print("\nStep 1: Getting top rebounders...")
    rebounders = get_top_rebounders(season=CURRENT_SEASON, top_n=50)
    print(f"  Found {len(rebounders)} players")

    print("\nStep 2: Collecting PLAYOFF game logs...")
    logs = collect_all_game_logs(
        rebounders,
        cache_path="data/game_logs/all_logs_reb_playoffs.csv",
        seasons=PLAYOFF_SEASONS,
        force_refresh=True,
        season_type=SEASON_TYPE,
    )
    if len(logs) == 0:
        print("  No playoff game logs found! Skipping rebounds model.")
        return None, None
    print(f"  Collected {len(logs)} playoff game log entries")

    print("\nStep 3: Engineering features...")
    features = build_rebound_features(logs)
    print(f"  Base features: {len(features)} rows, {len(features.columns)} cols")
    features = add_opponent_rebound_features(features, season=CURRENT_SEASON)
    print("  + Opponent rebound features")
    features = add_player_advanced_features(features, season=CURRENT_SEASON)
    print("  + Player advanced features")
    try:
        features = add_position_defense(features, season=CURRENT_SEASON)
        if "opp_pos_pts_allowed" in features.columns:
            features["opp_pos_reb_allowed"] = features["opp_pos_pts_allowed"] * 0.35
            features.drop(columns=["opp_pos_pts_allowed"], inplace=True)
        print("  + Position rebound defense")
    except Exception as e:
        print(f"  ! Position defense skipped: {e}")
        features["opp_pos_reb_allowed"] = 13.0
    print(f"  Final: {len(features)} rows, {len(REB_FEATURE_COLS)} rebound features")

    print("\nStep 4: Training model...")
    model, metrics = train_reb_model(features)
    print(f"\n  Playoff REB — MAE: {metrics['mae']:.2f}, R²: {metrics['r2']:.3f}")

    print("\nStep 5: Saving playoff rebounds model...")
    save_reb_model(model, path=REB_PLAYOFF_PATH)
    return model, metrics


def train_assists_playoffs():
    """Train playoff assists model."""
    print("\n" + "=" * 60)
    print("  ASSISTS — Playoff Model")
    print("=" * 60)

    print("\nStep 1: Getting top assist leaders...")
    assisters = get_top_assisters(season=CURRENT_SEASON, top_n=50)
    print(f"  Found {len(assisters)} players")

    print("\nStep 2: Collecting PLAYOFF game logs...")
    logs = collect_all_game_logs(
        assisters,
        cache_path="data/game_logs/all_logs_ast_playoffs.csv",
        seasons=PLAYOFF_SEASONS,
        force_refresh=True,
        season_type=SEASON_TYPE,
    )
    if len(logs) == 0:
        print("  No playoff game logs found! Skipping assists model.")
        return None, None
    print(f"  Collected {len(logs)} playoff game log entries")

    print("\nStep 3: Engineering features...")
    features = build_assist_features(logs)
    print(f"  Base features: {len(features)} rows, {len(features.columns)} cols")
    features = add_opponent_assist_features(features, season=CURRENT_SEASON)
    print("  + Opponent assist features")
    features = add_player_advanced_features(features, season=CURRENT_SEASON)
    print("  + Player advanced features")
    print(f"  Final: {len(features)} rows, {len(AST_FEATURE_COLS)} assist features")

    print("\nStep 4: Training model...")
    model, metrics = train_ast_model(features)
    print(f"\n  Playoff AST — MAE: {metrics['mae']:.2f}, R²: {metrics['r2']:.3f}")

    print("\nStep 5: Saving playoff assists model...")
    save_ast_model(model, path=AST_PLAYOFF_PATH)
    return model, metrics


if __name__ == "__main__":
    print("=" * 60)
    print("  NBA Playoff Predictor — Training All Models")
    print(f"  Seasons: {', '.join(PLAYOFF_SEASONS)}")
    print(f"  Season type: {SEASON_TYPE}")
    print("=" * 60)

    results = {}

    pts_model, pts_metrics = train_points_playoffs()
    if pts_metrics:
        results["Points"] = pts_metrics

    reb_model, reb_metrics = train_rebounds_playoffs()
    if reb_metrics:
        results["Rebounds"] = reb_metrics

    ast_model, ast_metrics = train_assists_playoffs()
    if ast_metrics:
        results["Assists"] = ast_metrics

    print("\n" + "=" * 60)
    print("  PLAYOFF TRAINING SUMMARY")
    print("=" * 60)
    for stat, m in results.items():
        print(f"  {stat:10s} — MAE: {m['mae']:.2f}, R²: {m['r2']:.3f}, "
              f"Train: {m['train_size']}, Test: {m['test_size']}")
    print(f"\n  Models saved to: {MODELS_DIR}/")
    print("  - xgb_scoring_model_playoffs.joblib")
    print("  - xgb_rebounds_model_playoffs.joblib")
    print("  - xgb_assists_model_playoffs.joblib")
    print("\n=== Playoff training complete! ===")
