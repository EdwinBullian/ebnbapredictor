import os
import sys
import pandas as pd
import numpy as np
import joblib
from xgboost import XGBRegressor
from lightgbm import LGBMRegressor
from sklearn.linear_model import Ridge
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.preprocessing import StandardScaler

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


# --- Minutes prediction features (subset that doesn't leak PTS info) ---
MINUTES_FEATURE_COLS = [
    "avg_minutes_last_5", "avg_minutes_last_10", "season_avg_minutes",
    "minutes_trend", "minutes_std_last_5",
    # Minutes EWM (recency-weighted minutes context)
    "min_ewm_10", "min_ewm_5", "min_momentum",
    # Career baseline (how many minutes does this player typically get?)
    "pts_career_min_avg", "pts_career_games",
    # Game context
    "opp_pace", "game_pace", "home_away", "rest_days", "is_b2b",
    "game_number", "usage_rate", "blowout_risk", "spread_proxy",
]

# --- Scoring prediction features (includes predicted minutes) ---
FEATURE_COLS = [
    # Scoring history
    "ppg_last_5", "ppg_last_10", "ppg_last_20", "season_ppg",
    # Career baseline (Improvement #1)
    "pts_career_avg", "pts_career_games", "pts_player_tier", "pts_career_min_avg",
    # Recency / EWM (Improvement #3)
    "pts_ewm_10", "pts_ewm_5", "pts_momentum",
    # Minutes (predicted + actuals)
    "predicted_minutes",
    "avg_minutes_last_5", "avg_minutes_last_10", "season_avg_minutes",
    "minutes_trend", "minutes_std_last_5",
    "min_ewm_10", "min_ewm_5", "min_momentum",
    # Shot attempts
    "fga_last_5", "fga_trend", "fta_last_5", "fg3a_last_5",
    "fg_pct_last_5", "pts_per_min_last_5",
    # Team/opponent
    "opp_def_rating", "opp_pace", "game_pace", "usage_rate",
    "spread_proxy", "blowout_risk", "opp_pos_pts_allowed",
    # Schedule
    "home_away", "rest_days", "is_b2b", "game_number",
    # Splits & consistency
    "home_away_split", "scoring_std_last_10", "pts_vs_opp",
    # Interactions
    "pace_x_usage", "rest_x_minutes",
]
TARGET_COL = "PTS"
MINUTES_TARGET = "MIN_FLOAT"
MODEL_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "models", "xgb_scoring_model.joblib")


class EnsembleModel:
    """Weighted ensemble of XGBoost, LightGBM, and Ridge regression."""

    def __init__(self, xgb_model, lgbm_model, ridge_model, ridge_scaler,
                 minutes_model, weights, feature_cols, minutes_feature_cols):
        self.xgb_model = xgb_model
        self.lgbm_model = lgbm_model
        self.ridge_model = ridge_model
        self.ridge_scaler = ridge_scaler
        self.minutes_model = minutes_model
        self.weights = weights  # {"xgb": 0.4, "lgbm": 0.35, "ridge": 0.25}
        self.feature_cols = feature_cols
        self.minutes_feature_cols = minutes_feature_cols

    def predict_minutes(self, X):
        """Predict minutes from available features."""
        min_cols = [c for c in self.minutes_feature_cols if c in X.columns]
        if len(min_cols) < len(self.minutes_feature_cols):
            missing = set(self.minutes_feature_cols) - set(min_cols)
            for col in missing:
                X = X.copy()
                X[col] = 0
        return self.minutes_model.predict(X[self.minutes_feature_cols])

    def predict(self, X):
        """Predict points using all ensemble members."""
        X = X.copy()
        # Add predicted minutes if not already there
        if "predicted_minutes" not in X.columns:
            min_cols_available = [c for c in self.minutes_feature_cols if c in X.columns]
            if len(min_cols_available) >= 5:
                X["predicted_minutes"] = self.predict_minutes(X)
            else:
                X["predicted_minutes"] = X.get("avg_minutes_last_5", 30)

        # Ensure all feature cols exist
        for col in self.feature_cols:
            if col not in X.columns:
                X[col] = 0

        X_feat = X[self.feature_cols]

        xgb_pred = self.xgb_model.predict(X_feat)
        lgbm_pred = self.lgbm_model.predict(X_feat)
        X_scaled = self.ridge_scaler.transform(X_feat)
        ridge_pred = self.ridge_model.predict(X_scaled)

        return (
            self.weights["xgb"] * xgb_pred
            + self.weights["lgbm"] * lgbm_pred
            + self.weights["ridge"] * ridge_pred
        )


def tune_xgb_hyperparams(X_train, y_train, X_test, y_test, n_trials=40):
    """Tune XGBoost hyperparameters with Optuna."""
    try:
        import optuna
        optuna.logging.set_verbosity(optuna.logging.WARNING)
    except ImportError:
        print("  Optuna not installed, using defaults.")
        return {"n_estimators": 500, "max_depth": 4, "learning_rate": 0.03,
                "subsample": 0.8, "colsample_bytree": 0.7, "min_child_weight": 5,
                "gamma": 0.1, "reg_alpha": 0.1, "reg_lambda": 1.0}

    def objective(trial):
        params = {
            "n_estimators": trial.suggest_int("n_estimators", 300, 900),
            "max_depth": trial.suggest_int("max_depth", 3, 7),
            "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.08, log=True),
            "subsample": trial.suggest_float("subsample", 0.6, 0.95),
            "colsample_bytree": trial.suggest_float("colsample_bytree", 0.5, 0.9),
            "min_child_weight": trial.suggest_int("min_child_weight", 1, 10),
            "gamma": trial.suggest_float("gamma", 0, 0.5),
            "reg_alpha": trial.suggest_float("reg_alpha", 0.01, 5.0, log=True),
            "reg_lambda": trial.suggest_float("reg_lambda", 0.1, 5.0, log=True),
            "random_state": 42, "verbosity": 0,
        }
        m = XGBRegressor(**params)
        m.fit(X_train, y_train)
        return mean_absolute_error(y_test, m.predict(X_test))

    study = optuna.create_study(direction="minimize")
    study.optimize(objective, n_trials=n_trials, show_progress_bar=False)
    print(f"  Best XGB MAE from tuning: {study.best_value:.3f}")
    return study.best_params


def train_minutes_model(features_df):
    """Train an Optuna-tuned model to predict minutes played."""
    available = [c for c in MINUTES_FEATURE_COLS if c in features_df.columns]
    X = features_df[available].copy()
    y = features_df[MINUTES_TARGET].copy()

    split_idx = int(len(X) * 0.8)
    X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
    y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]

    try:
        import optuna
        optuna.logging.set_verbosity(optuna.logging.WARNING)

        def objective(trial):
            params = {
                "n_estimators": trial.suggest_int("n_estimators", 200, 600),
                "max_depth": trial.suggest_int("max_depth", 3, 6),
                "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.1, log=True),
                "subsample": trial.suggest_float("subsample", 0.6, 0.95),
                "colsample_bytree": trial.suggest_float("colsample_bytree", 0.5, 0.9),
                "min_child_samples": trial.suggest_int("min_child_samples", 5, 30),
                "reg_alpha": trial.suggest_float("reg_alpha", 0.01, 3.0, log=True),
                "reg_lambda": trial.suggest_float("reg_lambda", 0.1, 3.0, log=True),
                "random_state": 42, "verbose": -1,
            }
            m = LGBMRegressor(**params)
            m.fit(X_train, y_train)
            return mean_absolute_error(y_test, m.predict(X_test))

        study = optuna.create_study(direction="minimize")
        study.optimize(objective, n_trials=25, show_progress_bar=False)
        best_params = study.best_params
        best_params.update({"random_state": 42, "verbose": -1})
        print(f"  Minutes Optuna best MAE: {study.best_value:.3f}")
    except ImportError:
        best_params = {
            "n_estimators": 400, "max_depth": 4, "learning_rate": 0.04,
            "subsample": 0.8, "colsample_bytree": 0.8,
            "min_child_samples": 10, "reg_alpha": 0.5, "reg_lambda": 1.0,
            "random_state": 42, "verbose": -1,
        }

    model = LGBMRegressor(**best_params)
    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)
    mae = mean_absolute_error(y_test, y_pred)
    r2 = r2_score(y_test, y_pred)
    print(f"  Minutes model — MAE: {mae:.2f} min, R²: {r2:.3f} ({len(available)} features)")
    return model, mae


def train_model(features_df):
    """Train ensemble model (XGBoost + LightGBM + Ridge) with minutes sub-model."""
    print("  Training minutes sub-model...")
    min_model, min_mae = train_minutes_model(features_df)

    # Add predicted minutes to features
    available_min_cols = [c for c in MINUTES_FEATURE_COLS if c in features_df.columns]
    features_df = features_df.copy()
    features_df["predicted_minutes"] = min_model.predict(features_df[available_min_cols])

    # Ensure all feature cols exist
    for col in FEATURE_COLS:
        if col not in features_df.columns:
            features_df[col] = 0

    X = features_df[FEATURE_COLS].copy()
    y = features_df[TARGET_COL].copy()

    split_idx = int(len(X) * 0.8)
    X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
    y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]

    # --- XGBoost ---
    print("  Tuning XGBoost...")
    xgb_params = tune_xgb_hyperparams(X_train, y_train, X_test, y_test, n_trials=40)
    xgb_params.update({"random_state": 42, "verbosity": 0})
    xgb_model = XGBRegressor(**xgb_params)
    xgb_model.fit(X_train, y_train)
    xgb_pred = xgb_model.predict(X_test)
    xgb_mae = mean_absolute_error(y_test, xgb_pred)
    xgb_r2 = r2_score(y_test, xgb_pred)
    print(f"  XGBoost  — MAE: {xgb_mae:.2f}, R²: {xgb_r2:.3f}")

    # --- LightGBM ---
    print("  Training LightGBM...")
    lgbm_model = LGBMRegressor(
        n_estimators=600, max_depth=4, learning_rate=0.03,
        subsample=0.75, colsample_bytree=0.7, min_child_samples=10,
        reg_alpha=0.5, reg_lambda=1.0, random_state=42, verbose=-1,
    )
    lgbm_model.fit(X_train, y_train)
    lgbm_pred = lgbm_model.predict(X_test)
    lgbm_mae = mean_absolute_error(y_test, lgbm_pred)
    lgbm_r2 = r2_score(y_test, lgbm_pred)
    print(f"  LightGBM — MAE: {lgbm_mae:.2f}, R²: {lgbm_r2:.3f}")

    # --- Ridge ---
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    ridge = Ridge(alpha=1.0)
    ridge.fit(X_train_scaled, y_train)
    ridge_pred = ridge.predict(X_test_scaled)
    ridge_mae = mean_absolute_error(y_test, ridge_pred)
    ridge_r2 = r2_score(y_test, ridge_pred)
    print(f"  Ridge    — MAE: {ridge_mae:.2f}, R²: {ridge_r2:.3f}")

    # --- Find optimal ensemble weights ---
    print("  Optimizing ensemble weights...")
    best_mae = float("inf")
    best_weights = {"xgb": 0.4, "lgbm": 0.35, "ridge": 0.25}
    for xw in np.arange(0.2, 0.7, 0.05):
        for lw in np.arange(0.1, 0.6, 0.05):
            rw = 1.0 - xw - lw
            if rw < 0.05:
                continue
            ens = xw * xgb_pred + lw * lgbm_pred + rw * ridge_pred
            mae = mean_absolute_error(y_test, ens)
            if mae < best_mae:
                best_mae = mae
                best_weights = {"xgb": round(xw, 2), "lgbm": round(lw, 2), "ridge": round(rw, 2)}

    ens_pred = best_weights["xgb"] * xgb_pred + best_weights["lgbm"] * lgbm_pred + best_weights["ridge"] * ridge_pred
    ens_mae = mean_absolute_error(y_test, ens_pred)
    ens_r2 = r2_score(y_test, ens_pred)
    print(f"  Ensemble (XGB {best_weights['xgb']:.0%} + LGBM {best_weights['lgbm']:.0%} + Ridge {best_weights['ridge']:.0%})")
    print(f"           — MAE: {ens_mae:.2f}, R²: {ens_r2:.3f}")

    # --- Time-series CV ---
    print("  Running time-series CV...")
    tscv = TimeSeriesSplit(n_splits=5)
    cv_maes = []
    for train_idx, test_idx in tscv.split(X):
        Xtr, Xte = X.iloc[train_idx], X.iloc[test_idx]
        ytr, yte = y.iloc[train_idx], y.iloc[test_idx]
        m = XGBRegressor(**xgb_params)
        m.fit(Xtr, ytr)
        cv_maes.append(mean_absolute_error(yte, m.predict(Xte)))
    ts_cv_mae = np.mean(cv_maes)
    print(f"  Time-series CV MAE: {ts_cv_mae:.2f}")

    model = EnsembleModel(
        xgb_model=xgb_model, lgbm_model=lgbm_model,
        ridge_model=ridge, ridge_scaler=scaler,
        minutes_model=min_model, weights=best_weights,
        feature_cols=FEATURE_COLS,
        minutes_feature_cols=[c for c in MINUTES_FEATURE_COLS if c in features_df.columns],
    )

    importance = dict(zip(FEATURE_COLS, xgb_model.feature_importances_.tolist()))

    metrics = {
        "mae": float(ens_mae), "r2": float(ens_r2),
        "xgb_mae": float(xgb_mae), "lgbm_mae": float(lgbm_mae), "ridge_mae": float(ridge_mae),
        "minutes_mae": float(min_mae), "ts_cv_mae": float(ts_cv_mae),
        "weights": best_weights,
        "train_size": len(X_train), "test_size": len(X_test),
        "n_features": len(FEATURE_COLS),
        "feature_importance": importance,
        "best_xgb_params": {k: v for k, v in xgb_params.items() if k not in ("random_state", "verbosity")},
    }
    return model, metrics


def save_model(model, path=MODEL_PATH):
    """Save ensemble model components."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    data = {
        "type": "ensemble_v2",
        "xgb_model": model.xgb_model,
        "lgbm_model": model.lgbm_model,
        "ridge_model": model.ridge_model,
        "ridge_scaler": model.ridge_scaler,
        "minutes_model": model.minutes_model,
        "weights": model.weights,
        "feature_cols": model.feature_cols,
        "minutes_feature_cols": model.minutes_feature_cols,
    }
    joblib.dump(data, path)
    print(f"Model saved to {path}")


def load_model(path=MODEL_PATH):
    """Load ensemble model from disk."""
    data = joblib.load(path)
    if isinstance(data, dict) and data.get("type") == "ensemble_v2":
        return EnsembleModel(
            xgb_model=data["xgb_model"], lgbm_model=data["lgbm_model"],
            ridge_model=data["ridge_model"], ridge_scaler=data["ridge_scaler"],
            minutes_model=data["minutes_model"], weights=data["weights"],
            feature_cols=data["feature_cols"],
            minutes_feature_cols=data["minutes_feature_cols"],
        )
    if isinstance(data, dict) and data.get("type") == "ensemble":
        # Backwards compat with v1 ensemble
        class SimpleEnsemble:
            def __init__(self, xgb, ridge, scaler, xw, rw):
                self.xgb = xgb; self.ridge = ridge; self.scaler = scaler; self.xw = xw; self.rw = rw
            def predict(self, X):
                return self.xw * self.xgb.predict(X) + self.rw * self.ridge.predict(self.scaler.transform(X))
        return SimpleEnsemble(data["xgb_model"], data["ridge_model"], data["ridge_scaler"],
                              data["xgb_weight"], data["ridge_weight"])
    return data


if __name__ == "__main__":
    from lib.data_collection import get_top_scorers, collect_all_game_logs
    from lib.features import build_features, add_opponent_features, add_player_advanced_features, add_position_defense

    print("=== NBA Scoring Predictor — Training (v4) ===\n")

    print("Step 1: Getting top 100 scorers...")
    scorers = get_top_scorers(season="2025-26", top_n=100)
    print(f"Found {len(scorers)} players\n")

    print("Step 2: Collecting game logs (5 seasons)...")
    seasons = ["2025-26", "2024-25", "2023-24", "2022-23", "2021-22"]
    logs = collect_all_game_logs(scorers, seasons=seasons)
    print(f"Collected {len(logs)} game log entries\n")

    print("Step 3: Engineering features...")
    features = build_features(logs)
    print(f"  Base features: {len(features)} rows, {len(features.columns)} cols")
    features = add_opponent_features(features, season="2025-26")
    print("  + Opponent features (def rating, pace, spread, blowout risk)")
    features = add_player_advanced_features(features, season="2025-26")
    print("  + Player advanced (usage rate, interactions)")

    print("  + Position defense matchup (fetching rosters — ~30 sec)...")
    try:
        features = add_position_defense(features, season="2025-26")
        print("  + Position defense added")
    except Exception as e:
        print(f"  ! Position defense skipped: {e}")
        features["opp_pos_pts_allowed"] = 38.0

    print(f"  Final: {len(features)} rows, {len(FEATURE_COLS)} scoring features\n")

    print("Step 4: Training model...")
    model, metrics = train_model(features)

    print(f"\n  ========== RESULTS ==========")
    print(f"  Ensemble MAE:     {metrics['mae']:.2f} points")
    print(f"  Ensemble R²:      {metrics['r2']:.3f}")
    print(f"  Minutes sub-model: {metrics['minutes_mae']:.2f} min MAE")
    print(f"  Time-series CV:   {metrics['ts_cv_mae']:.2f}")
    print(f"  XGB: {metrics['xgb_mae']:.2f} | LGBM: {metrics['lgbm_mae']:.2f} | Ridge: {metrics['ridge_mae']:.2f}")
    print(f"  Weights: {metrics['weights']}")
    print(f"  Features: {metrics['n_features']}")
    print(f"  Train: {metrics['train_size']}, Test: {metrics['test_size']}")

    print(f"\n  Top features (XGBoost):")
    for feat, imp in sorted(metrics["feature_importance"].items(), key=lambda x: -x[1])[:15]:
        print(f"    {feat}: {imp:.3f}")

    print("\nStep 5: Saving model...")
    save_model(model)
    print("\n=== Training complete! ===")
