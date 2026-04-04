# lib/data_collection.py
import time
import os
import pandas as pd
from nba_api.stats.endpoints import LeagueLeaders, PlayerGameLog

def _retry_nba_call(endpoint_cls, max_retries=3, **kwargs):
    """Call an nba_api endpoint with retries and exponential backoff."""
    for attempt in range(max_retries):
        try:
            endpoint = endpoint_cls(timeout=60, **kwargs)
            return endpoint.get_data_frames()[0]
        except Exception as e:
            if attempt < max_retries - 1:
                wait = 2 ** (attempt + 1)  # 2s, 4s backoff
                print(f"NBA API retry {attempt + 1}/{max_retries} after {wait}s: {e}")
                time.sleep(wait)
            else:
                raise


def get_top_players(season="2025-26", stat_category="PTS", top_n=100):
    """Get the top N players in a stat category for a given season.

    Args:
        season: NBA season string (e.g., "2025-26")
        stat_category: One of "PTS", "REB", "AST"
        top_n: Number of players to return

    Returns DataFrame with columns: PLAYER_ID, PLAYER, TEAM_ID, TEAM, GP, plus the stat column.
    """
    df = _retry_nba_call(
        LeagueLeaders,
        season=season,
        stat_category_abbreviation=stat_category,
        per_mode48="PerGame",
        season_type_all_star="Regular Season",
    )
    df = df.head(top_n)
    keep_cols = ["PLAYER_ID", "PLAYER", "TEAM_ID", "TEAM", "GP"]
    if stat_category in df.columns:
        keep_cols.append(stat_category)
    df = df[keep_cols]
    return df


def get_top_scorers(season="2025-26", top_n=100):
    """Get the top N scorers. Backwards-compatible alias."""
    df = get_top_players(season=season, stat_category="PTS", top_n=top_n)
    if "PTS" not in df.columns:
        df["PTS"] = 0
    return df


def get_top_rebounders(season="2025-26", top_n=100):
    """Get the top N rebounders."""
    return get_top_players(season=season, stat_category="REB", top_n=top_n)


def get_top_assisters(season="2025-26", top_n=100):
    """Get the top N assist leaders."""
    return get_top_players(season=season, stat_category="AST", top_n=top_n)


def get_player_game_logs(player_id, seasons=None):
    """Get game logs for a player across multiple seasons.

    Args:
        player_id: NBA player ID
        seasons: List of season strings like ["2025-26", "2024-25"]. Defaults to last 3 seasons.

    Returns DataFrame with game log data including PTS, MIN, GAME_DATE, MATCHUP, etc.
    """
    if seasons is None:
        seasons = ["2025-26", "2024-25", "2023-24"]

    all_logs = []
    for season in seasons:
        time.sleep(0.6)  # Rate limiting for nba_api
        try:
            df = _retry_nba_call(
                PlayerGameLog,
                player_id=player_id,
                season=season,
                season_type_all_star="Regular Season",
            )
            if len(df) > 0:
                all_logs.append(df)
        except Exception:
            continue

    if not all_logs:
        return pd.DataFrame()

    combined = pd.concat(all_logs, ignore_index=True)
    return combined


def collect_all_game_logs(top_scorers_df, cache_path="data/game_logs/all_logs.csv", seasons=None, force_refresh=False):
    """Collect game logs for all players in top_scorers_df.

    Caches results to CSV. If cache exists, loads from disk instead of re-fetching.

    Args:
        top_scorers_df: DataFrame with PLAYER_ID and PLAYER columns
        cache_path: Path to save/load cached data
        seasons: List of season strings

    Returns DataFrame of all game logs with PLAYER_ID column.
    """
    if os.path.exists(cache_path) and not force_refresh:
        return pd.read_csv(cache_path)

    all_logs = []
    for _, row in top_scorers_df.iterrows():
        player_id = row["PLAYER_ID"]
        print(f"Fetching logs for {row['PLAYER']} ({player_id})...")
        logs = get_player_game_logs(player_id, seasons=seasons)
        if len(logs) > 0:
            logs["PLAYER_ID"] = player_id
            all_logs.append(logs)

    if not all_logs:
        return pd.DataFrame()

    combined = pd.concat(all_logs, ignore_index=True)

    os.makedirs(os.path.dirname(cache_path), exist_ok=True)
    combined.to_csv(cache_path, index=False)

    return combined
