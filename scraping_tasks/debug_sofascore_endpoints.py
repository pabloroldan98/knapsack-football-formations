"""
Debug script: calls every SofaScore endpoint used by the scraper, once per
TLS client_identifier and host, and prints a status matrix.

Run it locally or in GitHub Actions to find out which combinations work:
    python -u ./scraping_tasks/debug_sofascore_endpoints.py
"""
import os
import sys
import time

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import tls_requests

from sofascore import pick_sofascore_headers

# Known-good ids for testing (Segunda Division + Racing Santander + Diego Marino)
UNIQUE_TOURNAMENT_ID = 54
SEASON_ID = 77558
TEAM_ID = 2835
PLAYER_ID = 69379

HOSTS = [
    "https://www.sofascore.com",
    "https://api.sofascore.com",
]

ENDPOINTS = {
    "league_teams": f"/api/v1/unique-tournament/{UNIQUE_TOURNAMENT_ID}/season/{SEASON_ID}/teams",
    "team_players": f"/api/v1/team/{TEAM_ID}/players",
    "player_info": f"/api/v1/player/{PLAYER_ID}",
    "player_summary": f"/api/v1/player/{PLAYER_ID}/last-year-summary",
    "player_stats": f"/api/v1/player/{PLAYER_ID}/statistics/match-type/overall",
}

CLIENT_IDENTIFIERS = [
    "safari_16_0",
    "safari_ios_17_0",
    "safari_ios_18_0",
    "okhttp4_android_13",
    "okhttp4_android_12",
    "firefox_132",
    "firefox_120",
    "chrome_133",
    "chrome_131",
    "chrome_124",
    "chrome_120",
]

HEADER_MODES = {
    "no_headers": None,
    "sofascore_headers": pick_sofascore_headers(),
}


def check(url, client_identifier, headers):
    try:
        response = tls_requests.get(
            url,
            headers=headers,
            client_identifier=client_identifier,
            verify=False,
            timeout=20,
        )
        return str(response.status_code)
    except Exception as e:
        return f"ERR({type(e).__name__})"


def main():
    print(f"GITHUB_ACTIONS={os.getenv('GITHUB_ACTIONS')}")
    print()

    results = {}
    for host in HOSTS:
        for header_label, headers in HEADER_MODES.items():
            print("=" * 70)
            print(f"HOST: {host} | headers: {header_label}")
            print("=" * 70)
            col_width = max(len(name) for name in ENDPOINTS) + 2
            header_row = "identifier".ljust(22) + "".join(name.ljust(col_width) for name in ENDPOINTS)
            print(header_row)
            for ident in CLIENT_IDENTIFIERS:
                row = ident.ljust(22)
                for name, path in ENDPOINTS.items():
                    status = check(f"{host}{path}", ident, headers)
                    results[(host, header_label, ident, name)] = status
                    row += status.ljust(col_width)
                    time.sleep(0.2)
                print(row)
            print()

    print("=" * 70)
    print("WORKING COMBINATIONS (all endpoints 200):")
    print("=" * 70)
    found_any = False
    for host in HOSTS:
        for header_label in HEADER_MODES:
            for ident in CLIENT_IDENTIFIERS:
                statuses = [results[(host, header_label, ident, name)] for name in ENDPOINTS]
                if all(s == "200" for s in statuses):
                    print(f"  {host} | headers={header_label} | client_identifier={ident}")
                    found_any = True
    if not found_any:
        print("  NONE - SofaScore blocks every tested combination from this IP")


if __name__ == "__main__":
    main()
