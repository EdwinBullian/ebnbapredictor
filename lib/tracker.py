"""Prediction tracker — saves picks to JSON and grades them after games finish.

Uses JSON file storage instead of SQLite so it works on Vercel's ephemeral filesystem.
Storage path: /tmp/ebnbapredictor/predictions.json on Vercel, data/predictions.json locally.
"""
import os
import json
import time
import unicodedata
from datetime import datetime, timedelta

# ---------------------------------------------------------------------------
# Storage path — /tmp on Vercel (ephemeral), data/ locally
# ---------------------------------------------------------------------------

def _get_storage_path():
    """Return path to predictions JSON file."""
    # Vercel sets VERCEL env var
    if os.environ.get("VERCEL") or os.environ.get("VERCEL_ENV"):
        base = "/tmp/ebnbapredictor"
    else:
        # Local: relative to project root (one level up from lib/)
        base = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
    os.makedirs(base, exist_ok=True)
    return os.path.join(base, "predictions.json")


# ---------------------------------------------------------------------------
# JSON load / save
# ---------------------------------------------------------------------------

def _load_store():
    """Load the predictions store from disk. Returns {"predictions": [...], "next_id": int}."""
    path = _get_storage_path()
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            # Ensure schema
            if "predictions" not in data:
                data["predictions"] = []
            if "next_id" not in data:
                ids = [p.get("id", 0) for p in data["predictions"]]
                data["next_id"] = (max(ids) + 1) if ids else 1
            return data
        except (json.JSONDecodeError, OSError):
            pass
    return {"predictions": [], "next_id": 1}


def _save_store(store):
    """Write the predictions store to disk."""
    path = _get_storage_path()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(store, f, indent=2, default=str)


# ---------------------------------------------------------------------------
# Name normalization (same as odds.py for consistent matching)
# ---------------------------------------------------------------------------

def _normalize(name):
    """Normalize player name for fuzzy matching."""
    name = unicodedata.normalize("NFD", name)
    name = "".join(c for c in name if unicodedata.category(c) != "Mn")
    name = name.lower().strip()
    for sfx in [" jr.", " jr", " sr.", " sr", " iii", " ii", " iv"]:
        if name.endswith(sfx):
            name = name[: -len(sfx)].strip()
    return name.replace(".", "").replace("'", "").replace("\u2019", "")


# ---------------------------------------------------------------------------
# Save
# ---------------------------------------------------------------------------

def save_predictions(all_comparisons, date=None):
    """Save today's bettable predictions (those with a PrizePicks line) to the tracker.

    Skips if picks for that date are already locked.
    all_comparisons should be a flat list mixing Points/Rebounds/Assists dicts.

    Returns dict with saved count.
    """
    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")

    store = _load_store()

    # Check if already locked for this date
    existing = [p for p in store["predictions"] if p.get("date") == date]
    if existing:
        return {
            "saved": 0,
            "already_locked": len(existing),
            "message": f"Predictions already locked for {date} ({len(existing)} picks).",
        }

    new_entries = []
    for c in all_comparisons:
        if c.get("line") is None or c.get("direction") is None:
            continue

        entry = {
            "id": store["next_id"],
            "date": date,
            "player_name": c["player_name"],
            "team": c.get("team", ""),
            "opponent": c.get("opponent", ""),
            "stat_type": c.get("stat_type", "Points"),
            "predicted": c.get("predicted"),
            "line": c.get("line"),
            "direction": c.get("direction"),
            "edge": c.get("edge"),
            "confidence": c.get("confidence"),
            "actual": None,
            "correct": None,
            "created_at": datetime.now().isoformat(),
        }
        new_entries.append(entry)
        store["next_id"] += 1

    store["predictions"].extend(new_entries)
    _save_store(store)

    return {"saved": len(new_entries), "date": date, "message": f"Locked {len(new_entries)} picks for {date}."}


# ---------------------------------------------------------------------------
# Grade
# ---------------------------------------------------------------------------

def fetch_and_update_actuals(date=None):
    """Fetch actual box-score stats for pending predictions and grade them.

    If date is given, grades that single date.
    If date is None, grades ALL pending dates.

    Returns dict with updated/skipped counts.
    """
    if date is None:
        pending_dates = get_pending_dates()
        if not pending_dates:
            return {"updated": 0, "skipped": 0, "errors": [],
                    "message": "No pending predictions to grade."}
        combined = {"updated": 0, "skipped": 0, "errors": [], "dates_graded": []}
        for d in pending_dates:
            result = _grade_single_date(d)
            combined["updated"] += result["updated"]
            combined["skipped"] += result["skipped"]
            combined["errors"].extend(result.get("errors", []))
            if result["updated"] > 0:
                combined["dates_graded"].append(d)
        combined["message"] = (
            f"Graded {combined['updated']} picks across {len(combined['dates_graded'])} date(s). "
            f"({combined['skipped']} skipped)"
        )
        combined["errors"] = combined["errors"][:10]
        return combined
    else:
        return _grade_single_date(date)


def _grade_single_date(date):
    """Grade pending predictions for a single date against actual box scores."""
    import pandas as pd
    from nba_api.stats.endpoints import PlayerGameLog
    from nba_api.stats.static import players as nba_players

    store = _load_store()

    # Get pending entries for this date
    pending_entries = [
        p for p in store["predictions"]
        if p.get("date") == date and p.get("correct") is None and p.get("line") is not None
    ]

    if not pending_entries:
        return {"updated": 0, "skipped": 0, "date": date,
                "message": f"No pending predictions found for {date}."}

    # Get unique players to look up
    pending_players = list({p["player_name"] for p in pending_entries})

    # Build name -> id map
    all_players = nba_players.get_players()
    norm_to_id = {_normalize(p["full_name"]): p["id"] for p in all_players}

    # Determine NBA season string from date
    year = int(date[:4])
    month = int(date[5:7])
    season = f"{year}-{str(year + 1)[2:]}" if month >= 10 else f"{year - 1}-{str(year)[2:]}"

    stat_col_map = {"Points": "PTS", "Rebounds": "REB", "Assists": "AST"}

    updated = 0
    skipped = 0
    errors = []

    # Build lookup: player_name -> {stat_type -> actual_value}
    actuals_cache = {}

    for pname in pending_players:
        norm = _normalize(pname)

        player_id = norm_to_id.get(norm)
        if player_id is None:
            # Try partial match
            for key, pid in norm_to_id.items():
                if norm in key or key in norm:
                    player_id = pid
                    break
        if player_id is None:
            errors.append(f"Player not found in NBA roster: {pname}")
            skipped += 1
            continue

        try:
            time.sleep(0.6)
            log = PlayerGameLog(player_id=player_id, season=season)
            df = log.get_data_frames()[0]

            if df.empty:
                skipped += 1
                continue

            df["GAME_DATE_DT"] = pd.to_datetime(df["GAME_DATE"], format="%b %d, %Y", errors="coerce")
            target = pd.to_datetime(date).date()
            game_row = df[df["GAME_DATE_DT"].dt.date == target]

            if game_row.empty:
                skipped += 1
                continue

            game_data = game_row.iloc[0]
            actuals_cache[pname] = {
                "PTS": float(game_data.get("PTS", 0)),
                "REB": float(game_data.get("REB", 0)),
                "AST": float(game_data.get("AST", 0)),
            }

        except Exception as e:
            errors.append(f"{pname}: {e}")
            skipped += 1
            continue

    # Now update predictions in store
    for pred in store["predictions"]:
        if pred.get("date") != date or pred.get("correct") is not None:
            continue
        if pred.get("line") is None:
            continue

        pname = pred["player_name"]
        if pname not in actuals_cache:
            continue

        stat_col = stat_col_map.get(pred["stat_type"])
        if stat_col is None:
            continue

        actual = actuals_cache[pname].get(stat_col)
        if actual is None:
            continue

        line = pred["line"]
        direction = pred["direction"]

        if direction == "OVER":
            correct = 1 if actual > line else 0
        else:  # UNDER
            correct = 1 if actual < line else 0

        pred["actual"] = actual
        pred["correct"] = correct
        updated += 1

    _save_store(store)

    return {
        "updated": updated,
        "skipped": skipped,
        "date": date,
        "errors": errors[:10],
        "message": f"Graded {updated} picks for {date}. ({skipped} skipped)",
    }


# ---------------------------------------------------------------------------
# Stats / record
# ---------------------------------------------------------------------------

def get_record(days=None):
    """Return overall win/loss record broken down by stat type and confidence tier.

    Returns dict with keys: overall, by_stat, by_confidence, recent_days.
    """
    store = _load_store()
    preds = store["predictions"]

    # Apply days filter
    if days:
        cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        preds = [p for p in preds if p.get("date", "") >= cutoff]

    # Only bettable (has a line)
    bettable = [p for p in preds if p.get("line") is not None]
    graded = [p for p in bettable if p.get("correct") is not None]

    # Overall
    total = len(bettable)
    wins = sum(1 for p in graded if p.get("correct") == 1)
    losses = len(graded) - wins
    pending = total - len(graded)
    win_pct = round((wins / len(graded) * 100), 1) if graded else None
    avg_conf = round(sum(p.get("confidence", 0) or 0 for p in bettable) / total, 0) if total else None
    days_tracked = len({p["date"] for p in bettable})

    overall = {
        "total": total,
        "wins": wins,
        "losses": losses,
        "win_pct": win_pct,
        "avg_confidence": avg_conf,
        "days_tracked": days_tracked,
        "pending": pending,
    }

    # By stat type
    stat_groups = {}
    for p in graded:
        st = p.get("stat_type", "Points")
        stat_groups.setdefault(st, []).append(p)

    by_stat = []
    for st in sorted(stat_groups.keys()):
        group = stat_groups[st]
        g_wins = sum(1 for p in group if p.get("correct") == 1)
        by_stat.append({
            "stat_type": st,
            "total": len(group),
            "wins": g_wins,
            "win_pct": round(g_wins / len(group) * 100, 1) if group else None,
        })

    # By confidence tier
    def _tier(conf):
        if conf is None:
            return "Under 50"
        if conf >= 80:
            return "80+"
        if conf >= 70:
            return "70-79"
        if conf >= 60:
            return "60-69"
        if conf >= 50:
            return "50-59"
        return "Under 50"

    tier_order = ["80+", "70-79", "60-69", "50-59", "Under 50"]
    tier_groups = {}
    for p in graded:
        t = _tier(p.get("confidence"))
        tier_groups.setdefault(t, []).append(p)

    by_confidence = []
    for t in tier_order:
        if t not in tier_groups:
            continue
        group = tier_groups[t]
        g_wins = sum(1 for p in group if p.get("correct") == 1)
        by_confidence.append({
            "tier": t,
            "total": len(group),
            "wins": g_wins,
            "win_pct": round(g_wins / len(group) * 100, 1) if group else None,
        })

    # Recent days (last 14 graded dates)
    date_groups = {}
    for p in graded:
        d = p.get("date", "")
        date_groups.setdefault(d, []).append(p)

    recent_days = []
    for d in sorted(date_groups.keys(), reverse=True)[:14]:
        group = date_groups[d]
        g_wins = sum(1 for p in group if p.get("correct") == 1)
        recent_days.append({
            "date": d,
            "total": len(group),
            "wins": g_wins,
            "win_pct": round(g_wins / len(group) * 100, 1) if group else None,
        })

    return {
        "overall": overall,
        "by_stat": by_stat,
        "by_confidence": by_confidence,
        "recent_days": recent_days,
    }


def get_history(limit=60, date=None):
    """Return recent predictions with graded results.

    Returns list of prediction dicts sorted by date desc, confidence desc.
    """
    store = _load_store()
    preds = [p for p in store["predictions"] if p.get("line") is not None]

    if date:
        preds = [p for p in preds if p.get("date") == date]
        preds.sort(key=lambda x: (-(x.get("confidence") or 0),))
    else:
        preds.sort(key=lambda x: (x.get("date", ""), -(x.get("confidence") or 0)), reverse=True)
        preds = preds[:limit]

    return preds


def get_pending_dates():
    """Return dates that have locked predictions but results not yet graded.

    Returns list of date strings (most recent first, up to 14).
    """
    store = _load_store()
    pending = {
        p["date"]
        for p in store["predictions"]
        if p.get("correct") is None and p.get("line") is not None
    }
    return sorted(pending, reverse=True)[:14]
