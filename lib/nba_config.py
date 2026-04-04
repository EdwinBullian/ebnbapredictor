"""Patch nba_api default headers so stats.nba.com doesn't block cloud server IPs.

Import this module ONCE at app startup (e.g. in server.py) before any nba_api calls.
"""
import nba_api.stats.library.http as nba_http

CUSTOM_HEADERS = {
    "Host": "stats.nba.com",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.nba.com/",
    "Origin": "https://www.nba.com",
    "Connection": "keep-alive",
    "x-nba-stats-origin": "stats",
    "x-nba-stats-token": "true",
}

# Patch the default headers used by all nba_api endpoints
nba_http.NBAStatsHTTP._NBAStatsHTTP__default_headers = CUSTOM_HEADERS

# Also increase default timeout
nba_http.NBAStatsHTTP._NBAStatsHTTP__default_timeout = 60

print("[nba_config] Patched nba_api headers and timeout for cloud deployment")
