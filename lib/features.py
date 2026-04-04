import time
import pandas as pd
import numpy as np


def _parse_minutes(min_str):
    """Convert 'MM:SS' string to float minutes."""
    if pd.isna(min_str) or min_str == "" or min_str is None:
        return 0.0
    parts = str(min_str).split(":")
    if len(parts) == 2:
        return int(parts[0]) + int(parts[1]) / 60
    try:
        return float(parts[0])
    except ValueError:
        return 0.0


def _add_career_baseline(df, stat_col, prefix):
    """Add career baseline features: career average, total games, player tier.

    Args:
        df: DataFrame sorted by PLAYER_ID + GAME_DATE_PARSED with stat_col present
        stat_col: Column name for the stat (PTS, REB, AST)
        prefix: Feature name prefix (e.g., "pts", "reb", "ast")
    """
    grouped = df.groupby("PLAYER_ID")

    # Career average (expanding mean of ALL data available for the player, shifted)
    df[f"{prefix}_career_avg"] = grouped[stat_col].transform(
        lambda x: x.shift(1).expanding(min_periods=1).mean()
    )

    # Total games played so far (proxy for experience/reliability)
    df[f"{prefix}_career_games"] = grouped.cumcount()

    # Player tier bucket based on career average
    # Tiers: 0=low (<25th pctile), 1=mid (25-75), 2=high (75-90), 3=elite (90+)
    def _assign_tier(career_avg_series):
        # Compute tier based on the player's career average at each point
        result = pd.Series(1, index=career_avg_series.index)  # default mid
        result[career_avg_series <= career_avg_series.quantile(0.25)] = 0
        result[career_avg_series >= career_avg_series.quantile(0.75)] = 2
        result[career_avg_series >= career_avg_series.quantile(0.90)] = 3
        return result

    # Use season_avg or career_avg to assign tier (computed globally, not per-player)
    career_avgs = df[f"{prefix}_career_avg"].fillna(0)
    df[f"{prefix}_player_tier"] = 1  # default mid
    q25 = career_avgs.quantile(0.25)
    q75 = career_avgs.quantile(0.75)
    q90 = career_avgs.quantile(0.90)
    df.loc[career_avgs <= q25, f"{prefix}_player_tier"] = 0
    df.loc[career_avgs >= q75, f"{prefix}_player_tier"] = 2
    df.loc[career_avgs >= q90, f"{prefix}_player_tier"] = 3

    # Career minutes average (important context for all stats)
    if "MIN_FLOAT" in df.columns:
        df[f"{prefix}_career_min_avg"] = grouped["MIN_FLOAT"].transform(
            lambda x: x.shift(1).expanding(min_periods=1).mean()
        )

    return df


def _add_ewm_features(df, stat_col, prefix):
    """Add exponentially weighted moving average features (recency weighting).

    EWM naturally gives more weight to recent games — a 3-game slump matters
    more than what happened 15 games ago.
    """
    grouped = df.groupby("PLAYER_ID")

    # EWM with span=10 (half-life ~5 games) — shifted to prevent leakage
    df[f"{prefix}_ewm_10"] = grouped[stat_col].transform(
        lambda x: x.shift(1).ewm(span=10, min_periods=5).mean()
    )

    # EWM with span=5 (more reactive to recent form)
    df[f"{prefix}_ewm_5"] = grouped[stat_col].transform(
        lambda x: x.shift(1).ewm(span=5, min_periods=3).mean()
    )

    # Momentum: difference between fast EWM and slow EWM
    # Positive = player trending up recently, negative = cooling off
    df[f"{prefix}_momentum"] = df[f"{prefix}_ewm_5"] - df[f"{prefix}_ewm_10"]

    return df


def build_features(game_logs):
    """Engineer features from raw game log data.

    Returns DataFrame with feature columns and PTS/MIN_FLOAT as targets.
    """
    df = game_logs.copy()

    df["GAME_DATE_PARSED"] = pd.to_datetime(df["GAME_DATE"], format="mixed")
    df = df.sort_values(["PLAYER_ID", "GAME_DATE_PARSED"]).reset_index(drop=True)
    df["MIN_FLOAT"] = df["MIN"].apply(_parse_minutes)
    df["home_away"] = df["MATCHUP"].apply(lambda x: 1 if "vs." in str(x) else 0)
    df["OPPONENT"] = df["MATCHUP"].apply(lambda x: str(x).split(" ")[-1] if pd.notna(x) else "")

    grouped = df.groupby("PLAYER_ID")

    # --- Scoring rolling averages (shifted to prevent leakage) ---
    df["ppg_last_5"] = grouped["PTS"].transform(lambda x: x.shift(1).rolling(5, min_periods=5).mean())
    df["ppg_last_10"] = grouped["PTS"].transform(lambda x: x.shift(1).rolling(10, min_periods=10).mean())
    df["ppg_last_20"] = grouped["PTS"].transform(lambda x: x.shift(1).rolling(20, min_periods=20).mean())
    df["season_ppg"] = grouped["PTS"].transform(lambda x: x.shift(1).expanding(min_periods=5).mean())

    # --- Minutes features ---
    df["avg_minutes_last_5"] = grouped["MIN_FLOAT"].transform(lambda x: x.shift(1).rolling(5, min_periods=5).mean())
    df["avg_minutes_last_10"] = grouped["MIN_FLOAT"].transform(lambda x: x.shift(1).rolling(10, min_periods=10).mean())
    season_avg_min = grouped["MIN_FLOAT"].transform(lambda x: x.shift(1).expanding(min_periods=5).mean())
    df["minutes_trend"] = df["avg_minutes_last_5"] - season_avg_min
    df["minutes_std_last_5"] = grouped["MIN_FLOAT"].transform(lambda x: x.shift(1).rolling(5, min_periods=5).std())
    df["minutes_std_last_5"] = df["minutes_std_last_5"].fillna(0)
    df["season_avg_minutes"] = season_avg_min

    # --- Shot attempt trends (NEW) ---
    if "FGA" in df.columns:
        df["fga_last_5"] = grouped["FGA"].transform(lambda x: x.shift(1).rolling(5, min_periods=5).mean())
        df["fga_trend"] = df["fga_last_5"] - grouped["FGA"].transform(lambda x: x.shift(1).expanding(min_periods=5).mean())
    else:
        df["fga_last_5"] = 0.0
        df["fga_trend"] = 0.0

    if "FTA" in df.columns:
        df["fta_last_5"] = grouped["FTA"].transform(lambda x: x.shift(1).rolling(5, min_periods=5).mean())
    else:
        df["fta_last_5"] = 0.0

    if "FG3A" in df.columns:
        df["fg3a_last_5"] = grouped["FG3A"].transform(lambda x: x.shift(1).rolling(5, min_periods=5).mean())
    else:
        df["fg3a_last_5"] = 0.0

    # Shooting efficiency trends
    if "FGM" in df.columns and "FGA" in df.columns:
        df["_fg_pct"] = df["FGM"] / df["FGA"].replace(0, np.nan)
        df["fg_pct_last_5"] = grouped["_fg_pct"].transform(lambda x: x.shift(1).rolling(5, min_periods=5).mean())
        df["fg_pct_last_5"] = df["fg_pct_last_5"].fillna(0.45)
        df.drop(columns=["_fg_pct"], inplace=True)
    else:
        df["fg_pct_last_5"] = 0.45

    # Points per minute (scoring efficiency relative to time)
    df["_ppm"] = df["PTS"] / df["MIN_FLOAT"].replace(0, np.nan)
    df["pts_per_min_last_5"] = grouped["_ppm"].transform(lambda x: x.shift(1).rolling(5, min_periods=5).mean())
    df["pts_per_min_last_5"] = df["pts_per_min_last_5"].fillna(0.5)
    df.drop(columns=["_ppm"], inplace=True)

    # --- Rest / schedule ---
    df["rest_days"] = grouped["GAME_DATE_PARSED"].transform(lambda x: x.diff().dt.days)
    df["rest_days"] = df["rest_days"].fillna(2).clip(upper=7)
    df["is_b2b"] = (df["rest_days"] <= 1).astype(int)

    # Game number in season
    df["game_number"] = grouped.cumcount() + 1

    # --- Home/away split ---
    pts_shifted = grouped["PTS"].shift(1)
    df["_home_pts"] = np.where(df["home_away"] == 1, pts_shifted, np.nan)
    df["_away_pts"] = np.where(df["home_away"] == 0, pts_shifted, np.nan)
    df["player_home_ppg"] = grouped["_home_pts"].transform(lambda x: x.expanding(min_periods=3).mean())
    df["player_away_ppg"] = grouped["_away_pts"].transform(lambda x: x.expanding(min_periods=3).mean())
    df["player_home_ppg"] = df["player_home_ppg"].fillna(df["season_ppg"])
    df["player_away_ppg"] = df["player_away_ppg"].fillna(df["season_ppg"])
    df["home_away_split"] = np.where(
        df["home_away"] == 1,
        df["player_home_ppg"] - df["season_ppg"],
        df["player_away_ppg"] - df["season_ppg"],
    )
    df.drop(columns=["_home_pts", "_away_pts"], inplace=True)

    # --- Scoring consistency ---
    df["scoring_std_last_10"] = grouped["PTS"].transform(lambda x: x.shift(1).rolling(10, min_periods=10).std())
    df["scoring_std_last_10"] = df["scoring_std_last_10"].fillna(
        grouped["PTS"].transform(lambda x: x.shift(1).expanding(min_periods=3).std())
    )
    df["scoring_std_last_10"] = df["scoring_std_last_10"].fillna(0)

    # --- Opponent target encoding ---
    df["pts_vs_opp"] = np.nan
    for pid, group_df in df.groupby("PLAYER_ID"):
        for opp, opp_group in group_df.groupby("OPPONENT"):
            idx = opp_group.index
            shifted = opp_group["PTS"].shift(1).expanding(min_periods=1).mean()
            df.loc[idx, "pts_vs_opp"] = shifted
    df["pts_vs_opp"] = df["pts_vs_opp"].fillna(df["season_ppg"])

    # --- Career baseline features (Improvement #1) ---
    df = _add_career_baseline(df, "PTS", "pts")

    # --- Exponentially weighted recency features (Improvement #3) ---
    df = _add_ewm_features(df, "PTS", "pts")

    # --- EWM for minutes too (Improvement #4 — better minutes context) ---
    df = _add_ewm_features(df, "MIN_FLOAT", "min")

    # Drop rows where we don't have enough history
    df = df.dropna(subset=["ppg_last_20"]).reset_index(drop=True)

    feature_cols = [
        "PLAYER_ID", "GAME_DATE_PARSED", "OPPONENT", "MATCHUP",
        "PTS", "MIN_FLOAT",
        # Scoring
        "ppg_last_5", "ppg_last_10", "ppg_last_20", "season_ppg",
        # Career baseline
        "pts_career_avg", "pts_career_games", "pts_player_tier", "pts_career_min_avg",
        # Recency (EWM)
        "pts_ewm_10", "pts_ewm_5", "pts_momentum",
        # Minutes
        "avg_minutes_last_5", "avg_minutes_last_10", "season_avg_minutes",
        "minutes_trend", "minutes_std_last_5",
        # Minutes EWM
        "min_ewm_10", "min_ewm_5", "min_momentum",
        # Shot attempts
        "fga_last_5", "fga_trend", "fta_last_5", "fg3a_last_5",
        "fg_pct_last_5", "pts_per_min_last_5",
        # Schedule
        "home_away", "rest_days", "is_b2b", "game_number",
        # Splits & consistency
        "home_away_split", "scoring_std_last_10", "pts_vs_opp",
    ]
    return df[feature_cols]


# ============================================================
#  Team & Player Advanced Stats
# ============================================================

def _get_team_advanced_stats(season="2025-26"):
    """Fetch team advanced stats: def_rating, pace, off_rating, pts_allowed."""
    from nba_api.stats.endpoints import LeagueDashTeamStats
    from nba_api.stats.static import teams as nba_teams

    time.sleep(0.6)
    adv = LeagueDashTeamStats(
        season=season, measure_type_detailed_defense="Advanced",
        per_mode_detailed="PerGame", season_type_all_star="Regular Season",
    )
    adv_df = adv.get_data_frames()[0]

    # Also get base stats for opponent PTS allowed
    time.sleep(0.6)
    base = LeagueDashTeamStats(
        season=season, per_mode_detailed="PerGame",
        season_type_all_star="Regular Season",
    )
    base_df = base.get_data_frames()[0]

    team_map = {t["id"]: t["abbreviation"] for t in nba_teams.get_teams()}

    # Compute opponent PTS allowed per game from base stats
    # OPP_PTS isn't directly available; use league average adjusted by DEF_RATING
    league_avg_pts = base_df["PTS"].mean() if "PTS" in base_df.columns else 110.0

    result = {}
    for _, row in adv_df.iterrows():
        abbr = team_map.get(row["TEAM_ID"], "")
        if not abbr:
            continue
        def_rating = float(row.get("DEF_RATING", 110.0)) if pd.notna(row.get("DEF_RATING")) else 110.0
        pace = float(row.get("PACE", 100.0)) if pd.notna(row.get("PACE")) else 100.0
        off_rating = float(row.get("OFF_RATING", 110.0)) if pd.notna(row.get("OFF_RATING")) else 110.0

        # Estimate opponent PTS allowed: (def_rating / 100) * pace
        opp_pts_allowed = (def_rating / 100.0) * pace

        result[abbr] = {
            "def_rating": def_rating,
            "pace": pace,
            "off_rating": off_rating,
            "opp_pts_allowed": opp_pts_allowed,
        }

    return result


def _get_team_opponent_stats(season="2025-26"):
    """Fetch actual opponent stats: rebounds, assists, points allowed per game.

    Uses LeagueDashTeamStats with MeasureType=Opponent to get real data
    instead of heuristic approximations.
    Returns dict mapping team_abbr -> {opp_reb, opp_ast, opp_pts, opp_fg_pct, ...}.
    """
    from nba_api.stats.endpoints import LeagueDashTeamStats
    from nba_api.stats.static import teams as nba_teams

    time.sleep(0.6)
    # Opponent stats = what other teams score AGAINST this team
    opp_stats = LeagueDashTeamStats(
        season=season,
        measure_type_detailed_defense="Opponent",
        per_mode_detailed="PerGame",
        season_type_all_star="Regular Season",
    )
    opp_df = opp_stats.get_data_frames()[0]

    team_map = {t["id"]: t["abbreviation"] for t in nba_teams.get_teams()}

    result = {}
    for _, row in opp_df.iterrows():
        abbr = team_map.get(row["TEAM_ID"], "")
        if not abbr:
            continue
        result[abbr] = {
            "opp_reb_allowed": float(row.get("OPP_REB", row.get("REB", 44.0))) if pd.notna(row.get("OPP_REB", row.get("REB"))) else 44.0,
            "opp_ast_allowed": float(row.get("OPP_AST", row.get("AST", 25.0))) if pd.notna(row.get("OPP_AST", row.get("AST"))) else 25.0,
            "opp_pts_allowed": float(row.get("OPP_PTS", row.get("PTS", 110.0))) if pd.notna(row.get("OPP_PTS", row.get("PTS"))) else 110.0,
            "opp_oreb_allowed": float(row.get("OPP_OREB", row.get("OREB", 10.0))) if pd.notna(row.get("OPP_OREB", row.get("OREB"))) else 10.0,
            "opp_dreb_allowed": float(row.get("OPP_DREB", row.get("DREB", 34.0))) if pd.notna(row.get("OPP_DREB", row.get("DREB"))) else 34.0,
            "opp_tov_forced": float(row.get("OPP_TOV", row.get("TOV", 14.0))) if pd.notna(row.get("OPP_TOV", row.get("TOV"))) else 14.0,
            "opp_fg_pct_allowed": float(row.get("OPP_FG_PCT", row.get("FG_PCT", 0.46))) if pd.notna(row.get("OPP_FG_PCT", row.get("FG_PCT"))) else 0.46,
        }

    return result


def _get_team_pts_allowed_by_position(season="2025-26"):
    """Fetch points allowed by position for each team.

    Uses LeagueDashPtDefend or approximation from base stats.
    Returns dict mapping team_abbr -> {G: pts, F: pts, C: pts}.
    """
    from nba_api.stats.static import teams as nba_teams

    team_stats = _get_team_advanced_stats(season)
    # Approximate position-level breakdown using league-wide scoring shares
    pos_share = {"G": 0.45, "F": 0.35, "C": 0.20}

    result = {}
    for abbr, stats in team_stats.items():
        opp_pts = stats["opp_pts_allowed"]
        result[abbr] = {pos: opp_pts * share for pos, share in pos_share.items()}

    return result


def _get_player_usage_rates(season="2025-26"):
    """Fetch player usage rates. Returns dict mapping player_id -> usage_pct."""
    from nba_api.stats.endpoints import LeagueDashPlayerStats

    time.sleep(0.6)
    stats = LeagueDashPlayerStats(
        season=season, measure_type_detailed_defense="Advanced",
        per_mode_detailed="PerGame", season_type_all_star="Regular Season",
    )
    df = stats.get_data_frames()[0]
    return {int(r["PLAYER_ID"]): float(r["USG_PCT"]) for _, r in df.iterrows() if pd.notna(r.get("USG_PCT"))}


def _get_player_positions_from_roster(season="2025-26"):
    """Get player positions from team rosters. Returns dict player_id -> 'G'/'F'/'C'."""
    from nba_api.stats.endpoints import CommonTeamRoster
    from nba_api.stats.static import teams as nba_teams

    result = {}
    for team in nba_teams.get_teams():
        time.sleep(0.6)
        try:
            roster = CommonTeamRoster(team_id=team["id"], season=season)
            df = roster.get_data_frames()[0]
            for _, row in df.iterrows():
                pos = str(row.get("POSITION", "")).upper()
                pid = int(row.get("PLAYER_ID", 0))
                if not pid:
                    continue
                if pos in ("G", "G-F"):
                    result[pid] = "G"
                elif pos in ("F", "F-G", "F-C"):
                    result[pid] = "F"
                elif pos in ("C", "C-F"):
                    result[pid] = "C"
                else:
                    result[pid] = "F"
        except Exception:
            continue
    return result


def _get_team_scoring_leaders(season="2025-26"):
    """Get top 2 scorers per team. Returns dict team_abbr -> [player_id, player_id]."""
    from nba_api.stats.endpoints import LeagueDashPlayerStats
    from nba_api.stats.static import teams as nba_teams

    time.sleep(0.6)
    stats = LeagueDashPlayerStats(
        season=season, per_mode_detailed="PerGame",
        season_type_all_star="Regular Season",
    )
    df = stats.get_data_frames()[0]

    team_map = {t["id"]: t["abbreviation"] for t in nba_teams.get_teams()}
    df["TEAM_ABBR"] = df["TEAM_ID"].map(team_map)
    df = df.sort_values("PTS", ascending=False)

    leaders = {}
    for _, row in df.iterrows():
        abbr = row.get("TEAM_ABBR", "")
        if abbr and abbr not in leaders:
            leaders[abbr] = []
        if abbr and len(leaders.get(abbr, [])) < 2:
            leaders[abbr].append({
                "player_id": int(row["PLAYER_ID"]),
                "ppg": float(row["PTS"]),
                "gp": int(row["GP"]),
            })
    return leaders


# ============================================================
#  Add external features to feature DataFrame
# ============================================================

def _build_shared_base(game_logs):
    """Build shared base columns used by all stat-type feature builders.

    Returns a DataFrame with parsed dates, minutes, home/away, opponent, rest, game_number.
    """
    df = game_logs.copy()
    df["GAME_DATE_PARSED"] = pd.to_datetime(df["GAME_DATE"], format="mixed")
    df = df.sort_values(["PLAYER_ID", "GAME_DATE_PARSED"]).reset_index(drop=True)
    df["MIN_FLOAT"] = df["MIN"].apply(_parse_minutes)
    df["home_away"] = df["MATCHUP"].apply(lambda x: 1 if "vs." in str(x) else 0)
    df["OPPONENT"] = df["MATCHUP"].apply(lambda x: str(x).split(" ")[-1] if pd.notna(x) else "")

    grouped = df.groupby("PLAYER_ID")

    # Minutes features (shared across all stat types)
    df["avg_minutes_last_5"] = grouped["MIN_FLOAT"].transform(lambda x: x.shift(1).rolling(5, min_periods=5).mean())
    df["avg_minutes_last_10"] = grouped["MIN_FLOAT"].transform(lambda x: x.shift(1).rolling(10, min_periods=10).mean())
    season_avg_min = grouped["MIN_FLOAT"].transform(lambda x: x.shift(1).expanding(min_periods=5).mean())
    df["minutes_trend"] = df["avg_minutes_last_5"] - season_avg_min
    df["minutes_std_last_5"] = grouped["MIN_FLOAT"].transform(lambda x: x.shift(1).rolling(5, min_periods=5).std()).fillna(0)
    df["season_avg_minutes"] = season_avg_min

    # Rest / schedule (shared)
    df["rest_days"] = grouped["GAME_DATE_PARSED"].transform(lambda x: x.diff().dt.days)
    df["rest_days"] = df["rest_days"].fillna(2).clip(upper=7)
    df["is_b2b"] = (df["rest_days"] <= 1).astype(int)
    df["game_number"] = grouped.cumcount() + 1

    return df


def build_rebound_features(game_logs):
    """Engineer features for rebounds prediction.

    Returns DataFrame with rebound-specific feature columns and REB/MIN_FLOAT as targets.
    """
    df = _build_shared_base(game_logs)
    grouped = df.groupby("PLAYER_ID")

    # --- Rebounding rolling averages ---
    df["rpg_last_5"] = grouped["REB"].transform(lambda x: x.shift(1).rolling(5, min_periods=5).mean())
    df["rpg_last_10"] = grouped["REB"].transform(lambda x: x.shift(1).rolling(10, min_periods=10).mean())
    df["rpg_last_20"] = grouped["REB"].transform(lambda x: x.shift(1).rolling(20, min_periods=20).mean())
    df["season_rpg"] = grouped["REB"].transform(lambda x: x.shift(1).expanding(min_periods=5).mean())

    # --- Offensive / Defensive rebound split ---
    if "OREB" in df.columns:
        df["oreb_last_5"] = grouped["OREB"].transform(lambda x: x.shift(1).rolling(5, min_periods=5).mean())
    else:
        df["oreb_last_5"] = 0.0

    if "DREB" in df.columns:
        df["dreb_last_5"] = grouped["DREB"].transform(lambda x: x.shift(1).rolling(5, min_periods=5).mean())
    else:
        df["dreb_last_5"] = 0.0

    # --- Rebound rate (rebounds per minute) ---
    df["_rpm"] = df["REB"] / df["MIN_FLOAT"].replace(0, np.nan)
    df["reb_per_min_last_5"] = grouped["_rpm"].transform(lambda x: x.shift(1).rolling(5, min_periods=5).mean())
    df["reb_per_min_last_5"] = df["reb_per_min_last_5"].fillna(0.15)
    df.drop(columns=["_rpm"], inplace=True)

    # --- Home/away rebound split ---
    reb_shifted = grouped["REB"].shift(1)
    df["_home_reb"] = np.where(df["home_away"] == 1, reb_shifted, np.nan)
    df["_away_reb"] = np.where(df["home_away"] == 0, reb_shifted, np.nan)
    df["player_home_rpg"] = grouped["_home_reb"].transform(lambda x: x.expanding(min_periods=3).mean())
    df["player_away_rpg"] = grouped["_away_reb"].transform(lambda x: x.expanding(min_periods=3).mean())
    df["player_home_rpg"] = df["player_home_rpg"].fillna(df["season_rpg"])
    df["player_away_rpg"] = df["player_away_rpg"].fillna(df["season_rpg"])
    df["home_away_reb_split"] = np.where(
        df["home_away"] == 1,
        df["player_home_rpg"] - df["season_rpg"],
        df["player_away_rpg"] - df["season_rpg"],
    )
    df.drop(columns=["_home_reb", "_away_reb"], inplace=True)

    # --- Rebound consistency ---
    df["reb_std_last_10"] = grouped["REB"].transform(lambda x: x.shift(1).rolling(10, min_periods=10).std())
    df["reb_std_last_10"] = df["reb_std_last_10"].fillna(
        grouped["REB"].transform(lambda x: x.shift(1).expanding(min_periods=3).std())
    ).fillna(0)

    # --- Opponent target encoding ---
    df["reb_vs_opp"] = np.nan
    for pid, group_df in df.groupby("PLAYER_ID"):
        for opp, opp_group in group_df.groupby("OPPONENT"):
            idx = opp_group.index
            shifted = opp_group["REB"].shift(1).expanding(min_periods=1).mean()
            df.loc[idx, "reb_vs_opp"] = shifted
    df["reb_vs_opp"] = df["reb_vs_opp"].fillna(df["season_rpg"])

    # --- Career baseline features (Improvement #1) ---
    df = _add_career_baseline(df, "REB", "reb")

    # --- Exponentially weighted recency features (Improvement #3) ---
    df = _add_ewm_features(df, "REB", "reb")

    # --- EWM for minutes too (Improvement #4) ---
    df = _add_ewm_features(df, "MIN_FLOAT", "min")

    # Drop rows without enough history
    df = df.dropna(subset=["rpg_last_20"]).reset_index(drop=True)

    feature_cols = [
        "PLAYER_ID", "GAME_DATE_PARSED", "OPPONENT", "MATCHUP",
        "REB", "MIN_FLOAT",
        # Rebounding
        "rpg_last_5", "rpg_last_10", "rpg_last_20", "season_rpg",
        "oreb_last_5", "dreb_last_5", "reb_per_min_last_5",
        # Career baseline
        "reb_career_avg", "reb_career_games", "reb_player_tier", "reb_career_min_avg",
        # Recency (EWM)
        "reb_ewm_10", "reb_ewm_5", "reb_momentum",
        # Minutes
        "avg_minutes_last_5", "avg_minutes_last_10", "season_avg_minutes",
        "minutes_trend", "minutes_std_last_5",
        # Minutes EWM
        "min_ewm_10", "min_ewm_5", "min_momentum",
        # Schedule
        "home_away", "rest_days", "is_b2b", "game_number",
        # Splits & consistency
        "home_away_reb_split", "reb_std_last_10", "reb_vs_opp",
    ]
    return df[feature_cols]


def build_assist_features(game_logs):
    """Engineer features for assists prediction.

    Returns DataFrame with assist-specific feature columns and AST/MIN_FLOAT as targets.
    """
    df = _build_shared_base(game_logs)
    grouped = df.groupby("PLAYER_ID")

    # --- Assist rolling averages ---
    df["apg_last_5"] = grouped["AST"].transform(lambda x: x.shift(1).rolling(5, min_periods=5).mean())
    df["apg_last_10"] = grouped["AST"].transform(lambda x: x.shift(1).rolling(10, min_periods=10).mean())
    df["apg_last_20"] = grouped["AST"].transform(lambda x: x.shift(1).rolling(20, min_periods=20).mean())
    df["season_apg"] = grouped["AST"].transform(lambda x: x.shift(1).expanding(min_periods=5).mean())

    # --- Turnover context ---
    if "TOV" in df.columns:
        df["tov_last_5"] = grouped["TOV"].transform(lambda x: x.shift(1).rolling(5, min_periods=5).mean())
        ast_shifted = grouped["AST"].transform(lambda x: x.shift(1).rolling(5, min_periods=5).mean())
        tov_shifted = df["tov_last_5"].replace(0, np.nan)
        df["ast_to_tov_last_5"] = (ast_shifted / tov_shifted).fillna(2.0)
    else:
        df["tov_last_5"] = 0.0
        df["ast_to_tov_last_5"] = 2.0

    # --- Assist rate (assists per minute) ---
    df["_apm"] = df["AST"] / df["MIN_FLOAT"].replace(0, np.nan)
    df["ast_per_min_last_5"] = grouped["_apm"].transform(lambda x: x.shift(1).rolling(5, min_periods=5).mean())
    df["ast_per_min_last_5"] = df["ast_per_min_last_5"].fillna(0.15)
    df.drop(columns=["_apm"], inplace=True)

    # --- Home/away assist split ---
    ast_shifted = grouped["AST"].shift(1)
    df["_home_ast"] = np.where(df["home_away"] == 1, ast_shifted, np.nan)
    df["_away_ast"] = np.where(df["home_away"] == 0, ast_shifted, np.nan)
    df["player_home_apg"] = grouped["_home_ast"].transform(lambda x: x.expanding(min_periods=3).mean())
    df["player_away_apg"] = grouped["_away_ast"].transform(lambda x: x.expanding(min_periods=3).mean())
    df["player_home_apg"] = df["player_home_apg"].fillna(df["season_apg"])
    df["player_away_apg"] = df["player_away_apg"].fillna(df["season_apg"])
    df["home_away_ast_split"] = np.where(
        df["home_away"] == 1,
        df["player_home_apg"] - df["season_apg"],
        df["player_away_apg"] - df["season_apg"],
    )
    df.drop(columns=["_home_ast", "_away_ast"], inplace=True)

    # --- Assist consistency ---
    df["ast_std_last_10"] = grouped["AST"].transform(lambda x: x.shift(1).rolling(10, min_periods=10).std())
    df["ast_std_last_10"] = df["ast_std_last_10"].fillna(
        grouped["AST"].transform(lambda x: x.shift(1).expanding(min_periods=3).std())
    ).fillna(0)

    # --- Opponent target encoding ---
    df["ast_vs_opp"] = np.nan
    for pid, group_df in df.groupby("PLAYER_ID"):
        for opp, opp_group in group_df.groupby("OPPONENT"):
            idx = opp_group.index
            shifted = opp_group["AST"].shift(1).expanding(min_periods=1).mean()
            df.loc[idx, "ast_vs_opp"] = shifted
    df["ast_vs_opp"] = df["ast_vs_opp"].fillna(df["season_apg"])

    # --- Career baseline features (Improvement #1) ---
    df = _add_career_baseline(df, "AST", "ast")

    # --- Exponentially weighted recency features (Improvement #3) ---
    df = _add_ewm_features(df, "AST", "ast")

    # --- EWM for minutes too (Improvement #4) ---
    df = _add_ewm_features(df, "MIN_FLOAT", "min")

    # Drop rows without enough history
    df = df.dropna(subset=["apg_last_20"]).reset_index(drop=True)

    feature_cols = [
        "PLAYER_ID", "GAME_DATE_PARSED", "OPPONENT", "MATCHUP",
        "AST", "MIN_FLOAT",
        # Assists
        "apg_last_5", "apg_last_10", "apg_last_20", "season_apg",
        "tov_last_5", "ast_to_tov_last_5", "ast_per_min_last_5",
        # Career baseline
        "ast_career_avg", "ast_career_games", "ast_player_tier", "ast_career_min_avg",
        # Recency (EWM)
        "ast_ewm_10", "ast_ewm_5", "ast_momentum",
        # Minutes
        "avg_minutes_last_5", "avg_minutes_last_10", "season_avg_minutes",
        "minutes_trend", "minutes_std_last_5",
        # Minutes EWM
        "min_ewm_10", "min_ewm_5", "min_momentum",
        # Schedule
        "home_away", "rest_days", "is_b2b", "game_number",
        # Splits & consistency
        "home_away_ast_split", "ast_std_last_10", "ast_vs_opp",
    ]
    return df[feature_cols]


def add_opponent_rebound_features(features_df, season="2025-26"):
    """Add opponent features relevant to rebounds prediction."""
    team_stats = _get_team_advanced_stats(season)
    opp_team_stats = _get_team_opponent_stats(season)
    df = features_df.copy()

    league_avg_def = np.mean([s["def_rating"] for s in team_stats.values()]) if team_stats else 110.0
    league_avg_pace = np.mean([s["pace"] for s in team_stats.values()]) if team_stats else 100.0
    league_avg_off = np.mean([s["off_rating"] for s in team_stats.values()]) if team_stats else 110.0

    # Compute league averages from real opponent stats
    league_avg_reb_allowed = np.mean([s["opp_reb_allowed"] for s in opp_team_stats.values()]) if opp_team_stats else 44.0
    league_avg_oreb_allowed = np.mean([s["opp_oreb_allowed"] for s in opp_team_stats.values()]) if opp_team_stats else 10.0
    league_avg_dreb_allowed = np.mean([s["opp_dreb_allowed"] for s in opp_team_stats.values()]) if opp_team_stats else 34.0
    league_avg_fg_pct_allowed = np.mean([s["opp_fg_pct_allowed"] for s in opp_team_stats.values()]) if opp_team_stats else 0.46

    df["opp_def_rating"] = df["OPPONENT"].map(lambda x: team_stats.get(x, {}).get("def_rating", league_avg_def))
    df["opp_pace"] = df["OPPONENT"].map(lambda x: team_stats.get(x, {}).get("pace", league_avg_pace))
    if "TEAM" in df.columns:
        df["team_pace"] = df["TEAM"].map(lambda x: team_stats.get(x, {}).get("pace", league_avg_pace))
    else:
        df["team_pace"] = league_avg_pace
    df["game_pace"] = (df["opp_pace"] + df["team_pace"]) / 2

    # Spread proxy and blowout risk
    if "TEAM" in df.columns:
        df["team_off_rating"] = df["TEAM"].map(lambda x: team_stats.get(x, {}).get("off_rating", league_avg_off))
    else:
        df["team_off_rating"] = league_avg_off
    opp_off = df["OPPONENT"].map(lambda x: team_stats.get(x, {}).get("off_rating", league_avg_off))
    df["spread_proxy"] = df["team_off_rating"] - opp_off
    df["blowout_risk"] = df["spread_proxy"].abs().clip(upper=15)
    df.drop(columns=["team_off_rating"], inplace=True)

    # --- REAL opponent rebound stats (Improvement #2) ---
    df["opp_reb_allowed"] = df["OPPONENT"].map(
        lambda x: opp_team_stats.get(x, {}).get("opp_reb_allowed", league_avg_reb_allowed)
    )
    df["opp_oreb_allowed"] = df["OPPONENT"].map(
        lambda x: opp_team_stats.get(x, {}).get("opp_oreb_allowed", league_avg_oreb_allowed)
    )
    df["opp_dreb_allowed"] = df["OPPONENT"].map(
        lambda x: opp_team_stats.get(x, {}).get("opp_dreb_allowed", league_avg_dreb_allowed)
    )
    # Opponent FG% allowed — lower FG% = more missed shots = more rebound opportunities
    df["opp_fg_pct_allowed"] = df["OPPONENT"].map(
        lambda x: opp_team_stats.get(x, {}).get("opp_fg_pct_allowed", league_avg_fg_pct_allowed)
    )
    # Rebound opportunity: combines pace and FG% (more misses at higher pace = more rebounds)
    df["opp_reb_opportunity"] = (1.0 - df["opp_fg_pct_allowed"]) * df["game_pace"] / 100.0

    return df


def add_opponent_assist_features(features_df, season="2025-26"):
    """Add opponent features relevant to assists prediction."""
    team_stats = _get_team_advanced_stats(season)
    opp_team_stats = _get_team_opponent_stats(season)
    df = features_df.copy()

    league_avg_def = np.mean([s["def_rating"] for s in team_stats.values()]) if team_stats else 110.0
    league_avg_pace = np.mean([s["pace"] for s in team_stats.values()]) if team_stats else 100.0
    league_avg_off = np.mean([s["off_rating"] for s in team_stats.values()]) if team_stats else 110.0

    league_avg_ast_allowed = np.mean([s["opp_ast_allowed"] for s in opp_team_stats.values()]) if opp_team_stats else 25.0
    league_avg_tov_forced = np.mean([s["opp_tov_forced"] for s in opp_team_stats.values()]) if opp_team_stats else 14.0

    df["opp_def_rating"] = df["OPPONENT"].map(lambda x: team_stats.get(x, {}).get("def_rating", league_avg_def))
    df["opp_pace"] = df["OPPONENT"].map(lambda x: team_stats.get(x, {}).get("pace", league_avg_pace))
    if "TEAM" in df.columns:
        df["team_pace"] = df["TEAM"].map(lambda x: team_stats.get(x, {}).get("pace", league_avg_pace))
    else:
        df["team_pace"] = league_avg_pace
    df["game_pace"] = (df["opp_pace"] + df["team_pace"]) / 2

    # Spread proxy and blowout risk
    if "TEAM" in df.columns:
        df["team_off_rating"] = df["TEAM"].map(lambda x: team_stats.get(x, {}).get("off_rating", league_avg_off))
    else:
        df["team_off_rating"] = league_avg_off
    opp_off = df["OPPONENT"].map(lambda x: team_stats.get(x, {}).get("off_rating", league_avg_off))
    df["spread_proxy"] = df["team_off_rating"] - opp_off
    df["blowout_risk"] = df["spread_proxy"].abs().clip(upper=15)
    df.drop(columns=["team_off_rating"], inplace=True)

    # --- Real opponent assist/turnover stats ---
    df["opp_ast_allowed"] = df["OPPONENT"].map(
        lambda x: opp_team_stats.get(x, {}).get("opp_ast_allowed", league_avg_ast_allowed)
    )
    df["opp_tov_forced"] = df["OPPONENT"].map(
        lambda x: opp_team_stats.get(x, {}).get("opp_tov_forced", league_avg_tov_forced)
    )
    # Assist opportunity uses real assists allowed instead of heuristic
    df["opp_ast_opportunity"] = df["opp_ast_allowed"] * df["game_pace"] / 100.0

    return df


def add_opponent_features(features_df, season="2025-26"):
    """Add opponent features: def_rating, pace, position defense, spread proxy."""
    team_stats = _get_team_advanced_stats(season)
    pos_defense = _get_team_pts_allowed_by_position(season)

    df = features_df.copy()

    league_avg_def = np.mean([s["def_rating"] for s in team_stats.values()]) if team_stats else 110.0
    league_avg_pace = np.mean([s["pace"] for s in team_stats.values()]) if team_stats else 100.0
    league_avg_off = np.mean([s["off_rating"] for s in team_stats.values()]) if team_stats else 110.0

    # Opponent defense
    df["opp_def_rating"] = df["OPPONENT"].map(lambda x: team_stats.get(x, {}).get("def_rating", league_avg_def))

    # Pace
    df["opp_pace"] = df["OPPONENT"].map(lambda x: team_stats.get(x, {}).get("pace", league_avg_pace))
    if "TEAM" in df.columns:
        df["team_pace"] = df["TEAM"].map(lambda x: team_stats.get(x, {}).get("pace", league_avg_pace))
    else:
        df["team_pace"] = league_avg_pace
    df["game_pace"] = (df["opp_pace"] + df["team_pace"]) / 2

    # Spread proxy: difference in offensive ratings (positive = our team is favored)
    if "TEAM" in df.columns:
        df["team_off_rating"] = df["TEAM"].map(lambda x: team_stats.get(x, {}).get("off_rating", league_avg_off))
    else:
        df["team_off_rating"] = league_avg_off
    opp_off = df["OPPONENT"].map(lambda x: team_stats.get(x, {}).get("off_rating", league_avg_off))
    df["spread_proxy"] = df["team_off_rating"] - opp_off
    # Blowout risk: abs(spread_proxy) > 5 means likely blowout = starters sit early
    df["blowout_risk"] = df["spread_proxy"].abs().clip(upper=15)
    df.drop(columns=["team_off_rating"], inplace=True)

    return df


def add_player_advanced_features(features_df, season="2025-26"):
    """Add player-level features: usage rate, position defense matchup."""
    usage_rates = _get_player_usage_rates(season)

    df = features_df.copy()
    league_avg_usg = np.mean(list(usage_rates.values())) if usage_rates else 0.2
    df["usage_rate"] = df["PLAYER_ID"].map(usage_rates).fillna(league_avg_usg)

    # Feature interactions
    df["pace_x_usage"] = df["game_pace"] * df["usage_rate"]
    df["rest_x_minutes"] = df["rest_days"] * df["avg_minutes_last_5"]

    return df


def add_position_defense(features_df, season="2025-26"):
    """Add opponent points allowed to player's position."""
    pos_defense = _get_team_pts_allowed_by_position(season)

    # Get positions via roster (cached across calls)
    positions = _get_player_positions_from_roster(season)

    df = features_df.copy()
    league_avg_pos_pts = {"G": 50, "F": 38, "C": 22}

    def get_pos_defense(row):
        pid = row.get("PLAYER_ID")
        opp = row.get("OPPONENT", "")
        pos = positions.get(int(pid) if pd.notna(pid) else 0, "F")
        return pos_defense.get(opp, league_avg_pos_pts).get(pos, 38.0)

    df["opp_pos_pts_allowed"] = df.apply(get_pos_defense, axis=1)
    return df
