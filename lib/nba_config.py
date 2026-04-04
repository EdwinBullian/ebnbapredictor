"""Patch nba_api to use longer timeout and better headers for cloud deployment.

Import this module ONCE at app startup before any nba_api calls.
"""
import nba_api.stats.library.http as nba_http

# Patch headers with a Windows Chrome user agent
nba_http.NBAStatsHTTP.headers = {
    "Host": "stats.nba.com",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Referer": "https://www.nba.com/",
    "Origin": "https://www.nba.com",
    "Connection": "keep-alive",
    "Pragma": "no-cache",
    "Cache-Control": "no-cache",
    "x-nba-stats-origin": "stats",
    "x-nba-stats-token": "true",
    "Sec-Ch-Ua": '"Not:A-Brand";v="99", "Google Chrome";v="131", "Chromium";v="131"',
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-site",
}

# Monkey-patch send_api_request to default timeout to 120s instead of None
_original_send = nba_http.NBAStatsHTTP.send_api_request

def _patched_send(self, endpoint, parameters, referer=None, proxy=None,
                  headers=None, timeout=None, raise_exception_on_error=False):
    if timeout is None:
        timeout = 120
    return _original_send(
        self, endpoint, parameters,
        referer=referer, proxy=proxy, headers=headers,
        timeout=timeout, raise_exception_on_error=raise_exception_on_error,
    )

nba_http.NBAStatsHTTP.send_api_request = _patched_send

print("[nba_config] Patched nba_api: timeout=120s, updated headers")
