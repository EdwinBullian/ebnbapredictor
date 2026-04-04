import unicodedata
import requests


PRIZEPICKS_API = "https://api.prizepicks.com/projections"
NBA_LEAGUE_ID = 7

# Stat types we support
SUPPORTED_STAT_TYPES = {"Points", "Rebounds", "Assists"}

# Map stat types to prediction field names
STAT_FIELD_MAP = {
    "Points": {"predicted": "predicted_pts", "avg_last5": "ppg_last_5", "season_avg": "season_ppg"},
    "Rebounds": {"predicted": "predicted_reb", "avg_last5": "rpg_last_5", "season_avg": "season_rpg"},
    "Assists": {"predicted": "predicted_ast", "avg_last5": "apg_last_5", "season_avg": "season_apg"},
}


def _normalize_name(name):
    """Normalize player name for matching: strip accents, lowercase, remove suffixes."""
    name = unicodedata.normalize("NFD", name)
    name = "".join(c for c in name if unicodedata.category(c) != "Mn")
    name = name.lower().strip()
    for suffix in [" jr.", " jr", " sr.", " sr", " iii", " ii", " iv"]:
        if name.endswith(suffix):
            name = name[: -len(suffix)].strip()
    name = name.replace(".", "").replace("'", "").replace("\u2019", "")
    return name


def fetch_player_props(stat_type="Points"):
    """Fetch player props from PrizePicks for a specific stat type.

    Args:
        stat_type: One of "Points", "Rebounds", "Assists"

    Returns list of dicts with keys: player_name, line, stat_type, odds_type
    """
    resp = requests.get(
        PRIZEPICKS_API,
        params={"league_id": NBA_LEAGUE_ID, "per_page": 250},
        headers={"Accept": "application/json", "User-Agent": "Mozilla/5.0"},
        timeout=15,
    )

    if resp.status_code != 200:
        print(f"PrizePicks API error: {resp.status_code}")
        return []

    data = resp.json()
    projs = data.get("data", [])

    included_map = {}
    for item in data.get("included", []):
        included_map[(item["type"], item["id"])] = item.get("attributes", {})

    all_props = []
    for p in projs:
        attrs = p["attributes"]
        if attrs.get("stat_type") != stat_type:
            continue

        rels = p.get("relationships", {})
        player_rel = rels.get("new_player", {}).get("data", {})
        player_id = player_rel.get("id", "")
        player_info = included_map.get(("new_player", player_id), {})
        player_name = player_info.get("display_name", player_info.get("name", "Unknown"))

        line = attrs.get("line_score")
        if line is None:
            continue

        odds_type = attrs.get("odds_type", "standard")

        all_props.append({
            "player_name": player_name,
            "line": float(line),
            "stat_type": stat_type,
            "odds_type": odds_type,
            "projection_type": attrs.get("projection_type", ""),
            "flash_line": attrs.get("flash_sale_line_score"),
            "start_time": attrs.get("start_time", ""),
            "bookmaker": "PrizePicks",
            "allowed_direction": "both" if odds_type == "standard" else ("OVER" if odds_type == "demon" else "UNDER"),
        })

    # Deduplicate: prefer standard > demon > goblin per player
    priority = {"standard": 0, "demon": 1, "goblin": 2}
    all_props.sort(key=lambda x: priority.get(x["odds_type"], 9))
    seen = set()
    deduped = []
    for prop in all_props:
        norm = _normalize_name(prop["player_name"])
        if norm not in seen:
            seen.add(norm)
            deduped.append(prop)

    print(f"PrizePicks: {len(deduped)} unique player {stat_type.lower()} projections (from {len(all_props)} total)")
    return deduped


def fetch_all_props():
    """Fetch props for all supported stat types.

    Returns dict mapping stat_type -> list of props.
    """
    result = {}
    for stat_type in SUPPORTED_STAT_TYPES:
        try:
            result[stat_type] = fetch_player_props(stat_type)
        except Exception as e:
            print(f"Failed to fetch {stat_type} props: {e}")
            result[stat_type] = []
    return result


def _calculate_confidence_score(abs_edge, pred, stat_type="Points"):
    """Calculate a 1-100 confidence score based on edge size and player context.

    Rebounds and assists have lower variance than points, so edges mean more.
    """
    # Scale factor: rebounds/assists have lower totals, so edges matter more
    if stat_type == "Points":
        edge_scale = 1.0
    elif stat_type == "Rebounds":
        edge_scale = 1.8  # 2-reb edge on a 7-reb line is significant
    else:  # Assists
        edge_scale = 2.0  # 1.5-ast edge on a 5-ast line is significant

    scaled_edge = abs_edge * edge_scale

    # Base score from edge size (0-70 range)
    if scaled_edge >= 10:
        edge_score = 70
    elif scaled_edge >= 6:
        edge_score = 55 + (scaled_edge - 6) * 2.5
    elif scaled_edge >= 3:
        edge_score = 40 + (scaled_edge - 3) * 5
    elif scaled_edge >= 1:
        edge_score = 20 + (scaled_edge - 1) * 10
    else:
        edge_score = 10 + scaled_edge * 10

    # Consistency bonus (0-15 range)
    fields = STAT_FIELD_MAP.get(stat_type, STAT_FIELD_MAP["Points"])
    avg5 = pred.get(fields["avg_last5"], pred.get("ppg_last_5", 0))
    season = pred.get(fields["season_avg"], pred.get("season_ppg", 0))

    if avg5 > 0 and season > 0:
        trend_diff = abs(avg5 - season)
        if trend_diff < 1.0:
            consistency_bonus = 15
        elif trend_diff < 2:
            consistency_bonus = 10
        elif trend_diff < 3.5:
            consistency_bonus = 5
        else:
            consistency_bonus = 0
    else:
        consistency_bonus = 5

    # Last 5 games consistency bonus (0-15 range)
    last5 = pred.get("last_5_games", [])
    if len(last5) >= 5:
        import statistics
        std = statistics.stdev(last5)
        # Scale thresholds by stat type
        if stat_type == "Points":
            thresholds = (4, 7, 10)
        elif stat_type == "Rebounds":
            thresholds = (1.5, 3, 5)
        else:
            thresholds = (1.5, 2.5, 4)

        if std < thresholds[0]:
            game_bonus = 15
        elif std < thresholds[1]:
            game_bonus = 10
        elif std < thresholds[2]:
            game_bonus = 5
        else:
            game_bonus = 0
    else:
        game_bonus = 5

    raw = edge_score + consistency_bonus + game_bonus
    return max(1, min(100, round(raw)))


def compare_predictions_to_lines(predictions, props, stat_type="Points"):
    """Compare model predictions against PrizePicks lines for any stat type."""
    prop_lookup = {}
    for prop in props:
        norm = _normalize_name(prop["player_name"])
        if norm not in prop_lookup:
            prop_lookup[norm] = prop

    fields = STAT_FIELD_MAP.get(stat_type, STAT_FIELD_MAP["Points"])
    pred_field = fields["predicted"]

    results = []
    for pred in predictions:
        name = pred["player_name"]
        prop = prop_lookup.get(_normalize_name(name))

        predicted_val = pred.get(pred_field, 0)

        if prop is not None:
            line = prop["line"]
            edge = round(predicted_val - line, 1)
            abs_edge = abs(edge)

            confidence = _calculate_confidence_score(abs_edge, pred, stat_type)
            direction = "OVER" if edge > 0 else "UNDER"
            allowed = prop.get("allowed_direction", "both")
            odds_type = prop.get("odds_type", "standard")

            if allowed != "both" and direction != allowed:
                bettable = False
            else:
                bettable = True

            results.append({
                "player_name": name,
                "team": pred.get("team", ""),
                "opponent": pred.get("opponent", ""),
                "stat_type": stat_type,
                "predicted": predicted_val,
                "line": line,
                "edge": edge,
                "direction": direction,
                "confidence": confidence if bettable else 0,
                "bettable": bettable,
                "odds_type": odds_type,
                "bookmaker": "PrizePicks",
                "key_factors": pred.get("key_factors", []),
                "last_5_games": pred.get("last_5_games", []),
                "avg_last_5": pred.get(fields["avg_last5"], 0),
                "season_avg": pred.get(fields["season_avg"], 0),
            })

    # Include predictions without matching props
    matched_names = {r["player_name"] for r in results}
    for pred in predictions:
        name = pred["player_name"]
        if name not in matched_names:
            predicted_val = pred.get(pred_field, 0)
            results.append({
                "player_name": name,
                "team": pred.get("team", ""),
                "opponent": pred.get("opponent", ""),
                "stat_type": stat_type,
                "predicted": predicted_val,
                "line": None,
                "edge": None,
                "direction": None,
                "confidence": None,
                "bookmaker": None,
                "key_factors": pred.get("key_factors", []),
                "last_5_games": pred.get("last_5_games", []),
                "avg_last_5": pred.get(fields["avg_last5"], 0),
                "season_avg": pred.get(fields["season_avg"], 0),
            })

    results.sort(key=lambda x: (x["confidence"] is None, -(x["confidence"] or 0)))
    return results


# --- PrizePicks Parlay Optimizer ---

PRIZEPICKS_PAYOUTS = {
    2: {"power": 3.0, "flex": {2: 1.5}},
    3: {"power": 5.0, "flex": {3: 2.25, 2: 1.25}},
    4: {"power": 10.0, "flex": {4: 5.0, 3: 2.0, 2: 0.4}},
    5: {"power": 20.0, "flex": {5: 10.0, 4: 2.0, 3: 0.4}},
    6: {"power": 25.0, "flex": {6: 25.0, 5: 2.0, 4: 0.4}},
}


def _estimate_hit_probability(edge, confidence):
    conf = confidence if isinstance(confidence, (int, float)) else 50
    return 0.50 + (conf / 100) * 0.20


def build_parlays(all_comparisons, max_parlay_size=6, min_confidence=40):
    """Build optimal PrizePicks parlays from predictions across all stat types.

    Args:
        all_comparisons: list of comparison dicts (can mix stat types)
        max_parlay_size: maximum picks per parlay
        min_confidence: minimum confidence threshold

    Returns list of parlay suggestions.
    """
    # Filter to bettable picks — one pick per (player, stat_type) combo
    seen = set()
    eligible = []
    for c in all_comparisons:
        conf = c.get("confidence")
        key = (c["player_name"], c.get("stat_type", "Points"))
        if (c.get("line") is not None
                and c.get("bettable", True)
                and conf is not None
                and isinstance(conf, (int, float))
                and conf >= min_confidence
                and key not in seen):
            eligible.append(c)
            seen.add(key)

    if not eligible:
        return []

    eligible.sort(key=lambda x: x.get("confidence", 0), reverse=True)

    parlays = []

    # --- Strategy 1: "Safe Doubles" ---
    if len(eligible) >= 2:
        for i in range(0, min(len(eligible) - 1, 6), 2):
            picks = eligible[i: i + 2]
            parlay = _build_parlay_entry(picks, "Safe Double")
            parlays.append(parlay)

    # --- Strategy 2: "Power Trio" ---
    if len(eligible) >= 3:
        picks = eligible[:3]
        parlay = _build_parlay_entry(picks, "Power Trio")
        parlays.append(parlay)

    # --- Strategy 3: "Full Send" ---
    if len(eligible) >= 4:
        picks = eligible[:4]
        parlay = _build_parlay_entry(picks, "Full Send (4)")
        parlays.append(parlay)

    if len(eligible) >= 5:
        picks = eligible[:5]
        parlay = _build_parlay_entry(picks, "Full Send (5)")
        parlays.append(parlay)

    # --- Strategy 4: "Max Payout" ---
    if len(eligible) >= 6:
        picks = eligible[:6]
        parlay = _build_parlay_entry(picks, "Max Payout (6)")
        parlays.append(parlay)

    # --- Strategy 5: "Game Stack" ---
    games = {}
    for pick in eligible:
        game_key = f"{pick['team']}v{pick['opponent']}"
        games.setdefault(game_key, []).append(pick)

    for game_key, game_picks in games.items():
        if len(game_picks) >= 2:
            picks = game_picks[:3] if len(game_picks) >= 3 else game_picks[:2]
            parlay = _build_parlay_entry(picks, f"Game Stack: {game_key}")
            parlays.append(parlay)

    # --- Strategy 6: "Multi-Stat Stack" — same player, multiple stat types ---
    player_picks = {}
    for pick in eligible:
        player_picks.setdefault(pick["player_name"], []).append(pick)

    for player, picks in player_picks.items():
        if len(picks) >= 2:
            parlay = _build_parlay_entry(picks[:3], f"Player Stack: {player}")
            parlays.append(parlay)

    parlays.sort(key=lambda x: x["expected_value"], reverse=True)
    return parlays


def _build_parlay_entry(picks, strategy_name):
    """Build a single parlay entry with EV calculations."""
    size = len(picks)
    payout_info = PRIZEPICKS_PAYOUTS.get(size, {})
    power_mult = payout_info.get("power", 1.0)
    flex_payouts = payout_info.get("flex", {})

    probs = [_estimate_hit_probability(p["edge"], p["confidence"]) for p in picks]
    all_hit_prob = 1.0
    for prob in probs:
        all_hit_prob *= prob

    power_ev = (all_hit_prob * power_mult) - 1.0

    flex_ev = 0.0
    if flex_payouts:
        from itertools import combinations
        n = len(picks)
        for hits_needed, mult in flex_payouts.items():
            if hits_needed > n:
                continue
            prob_at_least = 0.0
            for k in range(hits_needed, n + 1):
                for combo in combinations(range(n), k):
                    p = 1.0
                    for j in range(n):
                        if j in combo:
                            p *= probs[j]
                        else:
                            p *= (1 - probs[j])
                    prob_at_least += p
            flex_ev += prob_at_least * mult
        flex_ev -= 1.0

    # Stat type abbreviation for display
    stat_abbr = {"Points": "PTS", "Rebounds": "REB", "Assists": "AST"}

    return {
        "strategy": strategy_name,
        "size": size,
        "picks": [
            {
                "player_name": p["player_name"],
                "team": p["team"],
                "opponent": p["opponent"],
                "stat_type": p.get("stat_type", "Points"),
                "stat_abbr": stat_abbr.get(p.get("stat_type", "Points"), "PTS"),
                "direction": p["direction"],
                "line": p["line"],
                "predicted": p["predicted"],
                "edge": p["edge"],
                "confidence": p["confidence"],
            }
            for p in picks
        ],
        "all_hit_probability": round(all_hit_prob * 100, 1),
        "power_payout": f"{power_mult}x",
        "flex_payouts": {f"{k}/{size}": f"{v}x" for k, v in flex_payouts.items()},
        "expected_value": round(max(power_ev, flex_ev) * 100, 1),
        "power_ev": round(power_ev * 100, 1),
        "flex_ev": round(flex_ev * 100, 1),
        "recommended_play": "Flex" if flex_ev > power_ev else "Power",
    }
