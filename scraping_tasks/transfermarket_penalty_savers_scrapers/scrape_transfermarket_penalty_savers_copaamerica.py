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


def safe_get_penalty_savers(label, file_name):
    try:
        print("----------------------------------------")
        print(f"- Scraping {label}:")
        data = get_penalty_savers_dict(
            file_name=file_name,
            force_scrape=True
        )
        print(f"\n{label} — Penalty Savers:")
        for team, goalkeepers_penalties in data.items():
            print()
            print(team)
            for goalkeeper, penalty_saves in goalkeepers_penalties.items():
                print(goalkeeper, penalty_saves)
        print()
        return data
    except Exception as e:
        print(f"Error scraping {label} Penalty Savers: {e}")
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
print("Scraping TRANSFERMARKET (penalty SAVERS)...")
print("##############################")

# try:


    # laliga_goalkeepers_penalty_saves = get_penalty_savers_dict(
    #     file_name="transfermarket_laliga_penalty_savers",
    #     force_scrape=True
    # )
    # for team, goalkeepers_penalties in laliga_goalkeepers_penalty_saves.items():
    #     print()
    #     print(team)
    #     for goalkeeper, penalty_saves in goalkeepers_penalties.items():
    #         print(goalkeeper, penalty_saves)


# laliga_goalkeepers_penalty_saves = safe_get_penalty_savers("LaLiga", "transfermarket_laliga_penalty_savers")
# premier_goalkeepers_penalty_saves = safe_get_penalty_savers("Premier League", "transfermarket_premier_penalty_savers")
# seriea_goalkeepers_penalty_saves = safe_get_penalty_savers("Serie A", "transfermarket_seriea_penalty_savers")
# bundesliga_goalkeepers_penalty_saves = safe_get_penalty_savers("Bundesliga", "transfermarket_bundesliga_penalty_savers")
# ligueone_goalkeepers_penalty_saves = safe_get_penalty_savers("Ligue 1", "transfermarket_ligueone_penalty_savers")
# segunda_goalkeepers_penalty_saves = safe_get_penalty_savers("Segunda División", "transfermarket_segunda_penalty_savers")
#
# champions_goalkeepers_penalty_saves = safe_get_penalty_savers("Champions League", "transfermarket_champions_penalty_savers")
# europaleague_goalkeepers_penalty_saves = safe_get_penalty_savers("Europa League", "transfermarket_europaleague_penalty_savers")
# conference_goalkeepers_penalty_saves = safe_get_penalty_savers("Conference League", "transfermarket_conference_penalty_savers")
# mundialito_goalkeepers_penalty_saves = safe_get_penalty_savers("Mundialito", "transfermarket_mundialito_penalty_savers")
#
# mundial_goalkeepers_penalty_saves = safe_get_penalty_savers("Mundial", "transfermarket_mundial_penalty_savers")
# eurocopa_goalkeepers_penalty_saves = safe_get_penalty_savers("Eurocopa", "transfermarket_eurocopa_penalty_savers")
copaamerica_goalkeepers_penalty_saves = safe_get_penalty_savers("Copa América", "transfermarket_copaamerica_penalty_savers")


# except Exception as e:
#     print(f"Error scraping TRANSFERMARKET (penalty SAVERS): {e}")
#     print(f"Exception type: {type(e).__name__}")
#     print(f"Full class path: {e.__class__.__module__}.{e.__class__.__name__}")
#     print(f"Error class: {e.__class__}")

print()
print("##############################")
##############################

end_time = time.time()
elapsed_time = end_time - start_time

print(f"Execution time: {elapsed_time} seconds")
