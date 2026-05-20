import os
import sys
from datetime import datetime, timezone
import time
import pytz
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from forced_matches import get_forced_matches_dict
from futbolfantasy_analytics import get_futbolfantasy_data, get_players_start_probabilities_dict_futbolfantasy
from futmondo import get_players_positions_dict_futmondo
from sofascore import get_players_ratings_list
from transfermarket_penalty_takers import get_penalty_takers_dict
from transfermarket_team_history import get_players_team_history_dict
from transfermarket_penalty_savers import get_penalty_savers_dict
from biwenger import get_biwenger_data_dict
from elo_ratings import get_teams_elos_dict


def safe_get_forced_matches(label, file_name, use_biwenger_names=True):
    try:
        print("----------------------------------------")
        print(f"- Scraping {label}:")
        data = get_forced_matches_dict(
            file_name=file_name,
            force_scrape=True,
            use_biwenger_names=use_biwenger_names,
        )
        print(f"\n{label} - Forced Matches:")
        for jornada_key, matches in data.items():
            print(jornada_key, matches)
        print()
        return data
    except Exception as e:
        print(f"Error scraping {label} Forced Matches: {e}")
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
print("Scraping FORCED MATCHES...")
print("##############################")

# try:


    # laliga_forced_matches = get_forced_matches_dict(
    #     file_name="forced_matches_laliga",
    #     force_scrape=True
    # )
    # print("Forced Matches:")
    # for jornada_key, matches in laliga_forced_matches.items():
    #     print(jornada_key, matches)

laliga_forced_matches = safe_get_forced_matches(
    "LaLiga", "forced_matches_laliga"
)
premier_forced_matches = safe_get_forced_matches(
    "Premier League", "forced_matches_premier"
)
seriea_forced_matches = safe_get_forced_matches(
    "Serie A", "forced_matches_seriea"
)
# bundesliga_forced_matches = safe_get_forced_matches(
#     "Bundesliga", "forced_matches_bundesliga"
# )
# ligueone_forced_matches = safe_get_forced_matches(
#     "Ligue 1", "forced_matches_ligueone"
# )
segunda_forced_matches = safe_get_forced_matches(
    "Segunda División", "forced_matches_segunda"
)

champions_forced_matches = safe_get_forced_matches(
    "Champions League", "forced_matches_champions", use_biwenger_names=False
)
europaleague_forced_matches = safe_get_forced_matches(
    "Europa League", "forced_matches_europaleague", use_biwenger_names=False
)
# conference_forced_matches = safe_get_forced_matches(
#     "Conference League", "forced_matches_conference"
# )
mundialito_forced_matches = safe_get_forced_matches(
    "Mundialito", "forced_matches_mundialito", use_biwenger_names=False
)

mundial_forced_matches = safe_get_forced_matches(
    "Mundial", "forced_matches_mundial", use_biwenger_names=False
)
# eurocopa_forced_matches = safe_get_forced_matches(
#     "Eurocopa", "forced_matches_eurocopa"
# )
# copaamerica_forced_matches = safe_get_forced_matches(
#     "Copa América", "forced_matches_copaamerica"
# )


# except Exception as e:
#     print(f"Error scraping FORCED MATCHES: {e}")
#     print(f"Exception type: {type(e).__name__}")
#     print(f"Full class path: {e.__class__.__module__}.{e.__class__.__name__}")
#     print(f"Error class: {e.__class__}")

print()
print("##############################")
##############################

end_time = time.time()
elapsed_time = end_time - start_time

print(f"Execution time: {elapsed_time} seconds")
