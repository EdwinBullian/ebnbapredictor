"""Flask API server for ebnbapredictor — deployed on Railway.

Generates live predictions using ML models. Predictions are cached daily,
PrizePicks odds are refreshed every 15 minutes.
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
from datetime import datetime
import threading
import time
import os
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

app = Flask(__name__)
CORS(app)

# ---------------------------------------------------------------------------
# Model loading (once at startup)
# ---------------------------------------------------------------------------

_models = {}


def _load_models():
    global _models
    from lib.train import (
        load_model as load_pts,
        FEATURE_COLS as PTS_COLS,
        MODEL_PATH as PTS_PATH,
    )
    from lib.train_rebounds import (
        load_model as load_reb,
        FEATURE_COLS as REB_COLS,
        MODEL_PATH as REB_PATH,
    )
    from lib.train_assists import (
        load_model as load_ast,
        FEATURE_COLS as AST_COLS,
        MODEL_PATH as AST_PATH,
    )

    for name, loader, cols, path in [
        ("Points", load_pts, PTS_COLS, PTS_PATH),
        ("Rebounds", load_reb, REB_COLS, REB_PATH),
        ("Assists", load_ast, AST_COLS, AST_PATH),
    ]:
        if os.path.exists(path):
            try:
                _models[name] = {"model": loader(path), "feature_cols": cols}
                print(f"  Loaded {name} model")
            except Exception as e:
                print(f"  Failed to load {name} model: {e}")


# ---------------------------------------------------------------------------
# Prediction cache
# ---------------------------------------------------------------------------

_cache = {
    "date": None,
    "games": [],
    "raw_preds": {"Points": [], "Rebounds": [], "Assists": []},
    "generating": False,
    "error": None,
    "odds": {},
    "odds_ts": None,
    "locked_today": False,
}
_lock = threading.Lock()

ODDS_TTL = 900  # seconds (15 min)


def _generate_predictions():
    """Generate model predictions for today.  Runs in a background thread."""
    today = datetime.now().strftime("%Y-%m-%d")
    print(f"[{today}] Generating predictions …")

    max_retries = 3
    for attempt in range(max_retries):
        try:
            return _generate_predictions_inner()
        except Exception as e:
            if attempt < max_retries - 1:
                wait = 15 * (attempt + 1)
                print(f"  Attempt {attempt+1} failed: {e}. Retrying in {wait}s …")
                time.sleep(wait)
            else:
                print(f"  All {max_retries} attempts failed: {e}")
                traceback.print_exc()
                with _lock:
                    _cache["generating"] = False
                    _cache["error"] = str(e)


def _generate_predictions_inner():
    """Inner prediction logic — called by _generate_predictions with retries."""
    from lib.predict import get_todays_games, generate_predictions
    from lib.data_collection import (
        get_top_scorers,
        get_top_rebounders,
        get_top_assisters,
    )
    from generate_predictions import _build_tonight_features

    today = datetime.now().strftime("%Y-%m-%d")

    try:
        games = get_todays_games()
        print(f"  Found {len(games)} games")

        raw = {"Points": [], "Rebounds": [], "Assists": []}

        if not games:
            with _lock:
                _cache.update(
                    date=today, games=[], raw_preds=raw,
                    generating=False, error=None,
                )
            print("  No games today.")
            return

        player_fns = {
            "Points": get_top_scorers,
            "Rebounds": get_top_rebounders,
            "Assists": get_top_assisters,
        }

        for stat_type in ["Points", "Rebounds", "Assists"]:
            if stat_type not in _models:
                continue
            try:
                print(f"  Generating {stat_type} …")
                info = _models[stat_type]
                top_players = player_fns[stat_type](season="2025-26", top_n=50)
                features = _build_tonight_features(top_players, games, stat_type)
                if features is None or len(features) == 0:
                    print(f"    No features built for {stat_type}")
                    continue
                preds = generate_predictions(
                    info["model"], features,
                    stat_type=stat_type,
                    feature_cols=info["feature_cols"],
                )
                raw[stat_type] = preds
                print(f"    {len(preds)} predictions")
            except Exception as e:
                print(f"    Error ({stat_type}): {e}")
                traceback.print_exc()

        with _lock:
            _cache.update(
                date=today, games=games, raw_preds=raw,
                generating=False, error=None, locked_today=False,
            )
        print("  Predictions ready.")

        # Auto-grade any pending dates from previous days
        try:
            from lib.tracker import fetch_and_update_actuals, get_pending_dates
            pending = get_pending_dates()
            if pending:
                print(f"  Auto-grading {len(pending)} pending date(s): {pending}")
                result = fetch_and_update_actuals()
                print(f"  Graded: {result.get('message', '')}")
        except Exception as e:
            print(f"  Auto-grade failed (non-fatal): {e}")

    except Exception as e:
        print(f"  Generation failed: {e}")
        traceback.print_exc()
        with _lock:
            _cache["generating"] = False
            _cache["error"] = str(e)


def _ensure_predictions():
    """Return True if today's predictions are cached; otherwise kick off generation."""
    today = datetime.now().strftime("%Y-%m-%d")
    with _lock:
        if _cache["date"] == today:
            return True
        if _cache["generating"]:
            return False
        _cache["generating"] = True

    threading.Thread(target=_generate_predictions, daemon=True).start()
    return False


def _get_odds():
    """Fetch PrizePicks odds, cached for ODDS_TTL seconds."""
    from lib.odds import fetch_all_props

    now = datetime.now()
    with _lock:
        if (
            _cache["odds_ts"]
            and (now - _cache["odds_ts"]).total_seconds() < ODDS_TTL
            and _cache["odds"]
        ):
            return dict(_cache["odds"])

    try:
        odds = fetch_all_props()
        with _lock:
            _cache["odds"] = odds
            _cache["odds_ts"] = now
        return odds
    except Exception as e:
        print(f"  Failed to fetch odds: {e}")
        with _lock:
            return dict(_cache["odds"]) if _cache["odds"] else {}


def _build_response():
    """Combine cached predictions with fresh PrizePicks odds."""
    from lib.odds import compare_predictions_to_lines, build_parlays

    with _lock:
        raw = {k: list(v) for k, v in _cache["raw_preds"].items()}
        games = list(_cache["games"])
        date = _cache["date"]

    odds = _get_odds()

    all_comparisons = []
    results = {}

    for stat_type in ["Points", "Rebounds", "Assists"]:
        preds = raw.get(stat_type, [])
        props = odds.get(stat_type, [])
        if preds:
            compared = compare_predictions_to_lines(preds, props, stat_type=stat_type)
            results[stat_type] = compared
            all_comparisons.extend(
                c for c in compared if c.get("line") is not None
            )
        else:
            results[stat_type] = []

    parlays = build_parlays(all_comparisons) if all_comparisons else []

    # Auto-lock predictions once per day (first time odds are matched)
    with _lock:
        already_locked = _cache["locked_today"]
    if not already_locked and all_comparisons:
        try:
            from lib.tracker import save_predictions
            result = save_predictions(all_comparisons, date=date)
            with _lock:
                _cache["locked_today"] = True
            print(f"  Auto-locked: {result.get('message', '')}")
        except Exception as e:
            print(f"  Auto-lock failed (non-fatal): {e}")

    return {
        "date": date,
        "games": games,
        "points": results.get("Points", []),
        "rebounds": results.get("Rebounds", []),
        "assists": results.get("Assists", []),
        "parlays": parlays,
        "predictions_count": len(all_comparisons),
    }


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/api/predictions", methods=["GET"])
def predictions():
    ready = _ensure_predictions()

    if not ready:
        return jsonify({
            "loading": True,
            "games": [],
            "points": [],
            "rebounds": [],
            "assists": [],
            "parlays": [],
            "predictions_count": 0,
            "message": "Generating today's predictions… refresh in ~2 minutes.",
        })

    return jsonify(_build_response())


@app.route("/api/predictions/refresh", methods=["POST"])
def refresh_predictions():
    """Force-regenerate predictions (e.g. after model update)."""
    with _lock:
        _cache["date"] = None
        _cache["odds"] = {}
        _cache["odds_ts"] = None
    _ensure_predictions()
    return jsonify({"status": "regenerating"})


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
        with _lock:
            _cache["odds"] = {}
            _cache["odds_ts"] = None
        odds = _get_odds()
        counts = {st: len(pl) for st, pl in odds.items()}
        return jsonify({"counts": counts, "props": odds})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/health", methods=["GET"])
def health():
    with _lock:
        return jsonify({
            "status": "ok",
            "predictions_date": _cache["date"],
            "generating": _cache["generating"],
            "models_loaded": list(_models.keys()),
        })


# ---------------------------------------------------------------------------
# Startup
# ---------------------------------------------------------------------------

print("Loading models …")
_load_models()
print(f"Models ready: {list(_models.keys())}")

# Kick off prediction generation immediately
threading.Thread(target=_ensure_predictions, daemon=True).start()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)
