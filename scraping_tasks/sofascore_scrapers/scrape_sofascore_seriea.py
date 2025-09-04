import os
import sys
from datetime import datetime, timezone
import time
import pytz
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from futbolfantasy_analytics import get_futbolfantasy_data
from futmondo import get_players_positions_dict_futmondo
from sofascore import get_players_ratings_list
from transfermarket_penalty_takers import get_penalty_takers_dict
from transfermarket_team_history import get_players_team_history_dict
from transfermarket_penalty_savers import get_penalty_savers_dict
from biwenger import get_biwenger_data_dict
from elo_ratings import get_teams_elos_dict


def safe_get_sofascore_ratings(label, file_name):
    try:
        print("----------------------------------------")
        print(f"- Scraping {label}:")
        data = get_players_ratings_list(
            file_name=file_name,
            backup_files=False,
            force_scrape=True
        )
        print(f"\n{label} , DONE!")
        # print(f"\n{label} — Sofascore Player Ratings:")
        # for p in data:
        #     # Print the object and its rating (guard in case attribute is missing)
        #     print(p)
        #     print(getattr(p, "sofascore_rating", None))
        # time.sleep(60)
        print()
        return data
    except Exception as e:
        print(f"Error scraping {label} Sofascore ratings: {e}")
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
print("Scraping SOFASCORE...")
print("##############################")

# try:


#     sofascore_laliga_players_ratings = get_players_ratings_list(
#         file_name="sofascore_laliga_players_ratings",
#         backup_files=False,
#         force_scrape=True
#     )
#     print()
#     for p in sofascore_laliga_players_ratings:
#         print(p)
#         print(p.sofascore_rating)


# sofascore_laliga_players_ratings = safe_get_sofascore_ratings("LaLiga", "sofascore_laliga_players_ratings")
# sofascore_premier_players_ratings = safe_get_sofascore_ratings("Premier League", "sofascore_premier_players_ratings")
sofascore_seriea_players_ratings = safe_get_sofascore_ratings("Serie A", "sofascore_seriea_players_ratings")
# sofascore_bundesliga_players_ratings = safe_get_sofascore_ratings("Bundesliga", "sofascore_bundesliga_players_ratings")
# sofascore_ligueone_players_ratings = safe_get_sofascore_ratings("Ligue 1", "sofascore_ligueone_players_ratings")
# sofascore_segundadivision_players_ratings = safe_get_sofascore_ratings("Segunda División", "sofascore_segundadivision_players_ratings")
#
# sofascore_champions_players_ratings = safe_get_sofascore_ratings("Champions League", "sofascore_champions_players_ratings")
# sofascore_europaleague_players_ratings = safe_get_sofascore_ratings("Europa League", "sofascore_europaleague_players_ratings")
# sofascore_conference_players_ratings = safe_get_sofascore_ratings("Conference League", "sofascore_conference_players_ratings")
# sofascore_mundialito_players_ratings = safe_get_sofascore_ratings("Mundialito", "sofascore_mundialito_players_ratings")
#
# sofascore_mundial_players_ratings = safe_get_sofascore_ratings("Mundial", "sofascore_mundial_players_ratings")
# sofascore_eurocopa_players_ratings = safe_get_sofascore_ratings("Eurocopa", "sofascore_eurocopa_players_ratings")
# sofascore_copaamerica_players_ratings = safe_get_sofascore_ratings("Copa América", "sofascore_copaamerica_players_ratings")


# except Exception as e:
#     print(f"Error scraping SOFASCORE: {e}")
#     print(f"Exception type: {type(e).__name__}")
#     print(f"Full class path: {e.__class__.__module__}.{e.__class__.__name__}")
#     print(f"Error class: {e.__class__}")

print()
print("##############################")
##############################

end_time = time.time()
elapsed_time = end_time - start_time

print(f"Execution time: {elapsed_time} seconds")
