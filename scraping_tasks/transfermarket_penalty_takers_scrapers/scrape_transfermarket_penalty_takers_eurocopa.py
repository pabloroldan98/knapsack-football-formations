import os
import sys
from datetime import datetime, timezone
import time
import pytz
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from futbolfantasy_analytics import get_futbolfantasy_data
from futmondo import get_players_positions_dict_futmondo
from sofascore import get_players_ratings_list
from transfermarket_penalty_takers import get_penalty_takers_dict
from transfermarket_team_history import get_players_team_history_dict
from transfermarket_penalty_savers import get_penalty_savers_dict
from biwenger import get_biwenger_data_dict
from elo_ratings import get_teams_elos_dict


def safe_get_penalty_takers(label, file_name):
    try:
        print("----------------------------------------")
        print(f"- Scraping {label}:")
        data = get_penalty_takers_dict(
            file_name=file_name,
            force_scrape=True
        )
        print(f"\n{label} — Penalty Takers:")
        for team, penalties in data.items():
            print(team, penalties)
        print()
        return data
    except Exception as e:
        print(f"Error scraping {label} Penalty Takers: {e}")
        print(f"Exception type: {type(e).__name__}")
        print(f"Full class path: {e.__class__.__module__}.{e.__class__.__name__}")
        print(f"Error class: {e.__class__}")
        return None


start_time = time.time()

# Define the timezone for Spain
cet = pytz.timezone('Europe/Madrid')
# Get the current time in UTC and convert to Spain time
now_utc = datetime.now(timezone.utc)
now = now_utc.astimezone(cet)

# Print current time and day of week
day_of_week = now.weekday()  # Monday is 0 and Sunday is 6
month_of_year = now.month    # January is 1 and December is 12

print(f"Current time: {now}")
print(f"Day of the week: {day_of_week}")
print(f"Month of the year: {month_of_year}")

print()
print("##############################")
##############################
print("Scraping TRANSFERMARKET (penalty TAKERS)...")
print("##############################")

# try:


    # penalty_takers = get_penalty_takers_dict(file_name="transfermarket_laliga_penalty_takers", force_scrape=True)
    # for team, penalties in penalty_takers.items():
    #     print(team, penalties)


# laliga_penalty_takers = safe_get_penalty_takers("LaLiga", "transfermarket_laliga_penalty_takers")
# premier_penalty_takers = safe_get_penalty_takers("Premier League", "transfermarket_premier_penalty_takers")
# seriea_penalty_takers = safe_get_penalty_takers("Serie A", "transfermarket_seriea_penalty_takers")
# bundesliga_penalty_takers = safe_get_penalty_takers("Bundesliga", "transfermarket_bundesliga_penalty_takers")
# ligueone_penalty_takers = safe_get_penalty_takers("Ligue 1", "transfermarket_ligueone_penalty_takers")
# segunda_penalty_takers = safe_get_penalty_takers("Segunda División", "transfermarket_segunda_penalty_takers")
#
# champions_penalty_takers = safe_get_penalty_takers("Champions League", "transfermarket_champions_penalty_takers")
# europaleague_penalty_takers = safe_get_penalty_takers("Europa League", "transfermarket_europaleague_penalty_takers")
# conference_penalty_takers = safe_get_penalty_takers("Conference League", "transfermarket_conference_penalty_takers")
# mundialito_penalty_takers = safe_get_penalty_takers("Mundialito", "transfermarket_mundialito_penalty_takers")
#
# mundial_penalty_takers = safe_get_penalty_takers("Mundial", "transfermarket_mundial_penalty_takers")
eurocopa_penalty_takers = safe_get_penalty_takers("Eurocopa", "transfermarket_eurocopa_penalty_takers")
# copaamerica_penalty_takers = safe_get_penalty_takers("Copa América", "transfermarket_copaamerica_penalty_takers")


# except Exception as e:
#     print(f"Error scraping TRANSFERMARKET (penalty TAKERS): {e}")
#     print(f"Exception type: {type(e).__name__}")
#     print(f"Full class path: {e.__class__.__module__}.{e.__class__.__name__}")
#     print(f"Error class: {e.__class__}")

print()
print("##############################")
##############################

end_time = time.time()
elapsed_time = end_time - start_time

print(f"Execution time: {elapsed_time} seconds")
