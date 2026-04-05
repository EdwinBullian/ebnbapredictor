"""Flask API server for ebnbapredictor — deployed on Railway.

Serves pre-computed predictions from data/predictions.json.
Run generate_predictions.py locally to update predictions.
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
from datetime import datetime
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

app = Flask(__name__)
CORS(app)

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")


def _load_predictions():
    """Load predictions from data/predictions.json."""
    path = os.path.join(DATA_DIR, "predictions.json")
    if not os.path.exists(path):
        return None
    with open(path, "r") as f:
        return json.load(f)


@app.route("/api/predictions", methods=["GET"])
def predictions():
    data = _load_predictions()
    if data is None:
        return jsonify({
            "games": [], "points": [], "rebounds": [], "assists": [],
            "parlays": [], "predictions_count": 0,
            "message": "No predictions available. Run generate_predictions.py locally.",
        })
    return jsonify(data)


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
