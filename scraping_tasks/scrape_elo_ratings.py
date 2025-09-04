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


def safe_get_elos(label, is_country, file_name, country=None, extra_teams=False):
    try:
        print("----------------------------------------")
        print(f"- Scraping {label}:")
        elo_dict = get_teams_elos_dict(
            is_country=is_country,
            country=country,
            extra_teams=extra_teams,
            write_file=True,
            file_name=file_name,
            force_scrape=True
        )
        print(f"\n{label} Elo Ratings:")
        for team, elo in elo_dict.items():
            print(f"{team}: {elo}")
        print()
        return elo_dict
    except Exception as e:
        print(f"Error scraping {label} Elo Ratings: {e}")
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
print("Scraping ELO RATINGS...")
print("##############################")

# try:


# Leagues
elo_ratings_laliga_data = safe_get_elos(
    "LaLiga",
    is_country=False, country="ESP", extra_teams=False,
    file_name="elo_ratings_laliga_data"
)

elo_ratings_premier_data = safe_get_elos(
    "Premier League",
    is_country=False, country="ENG", extra_teams=False,
    file_name="elo_ratings_premier_data"
)

elo_ratings_seriea_data = safe_get_elos(
    "Serie A",
    is_country=False, country="ITA", extra_teams=False,
    file_name="elo_ratings_seriea_data"
)

elo_ratings_bundesliga_data = safe_get_elos(
    "Bundesliga",
    is_country=False, country="GER", extra_teams=False,
    file_name="elo_ratings_bundesliga_data"
)

elo_ratings_ligueone_data = safe_get_elos(
    "Ligue 1",
    is_country=False, country="FRA", extra_teams=False,
    file_name="elo_ratings_ligueone_data"
)

elo_ratings_segundadivision_data = safe_get_elos(
    "Segunda División",
    is_country=False, country="ESP", extra_teams=False,
    file_name="elo_ratings_segundadivision_data"
)

# Tournaments
elo_ratings_champions_data = safe_get_elos(
    "Champions League",
    is_country=False, country=None, extra_teams=False,
    file_name="elo_ratings_champions_data"
)

# elo_ratings_mundialito_data = safe_get_elos(
#     "Mundialito",
#     is_country=False, country=None, extra_teams=True,
#     file_name="elo_ratings_mundialito_data"
# )

# Countries
elo_ratings_countries_data = safe_get_elos(
    "Countries",
    is_country=True,
    file_name="elo_ratings_countries_data"
)


# except Exception as e:
#     print(f"Error scraping ELO RATINGS: {e}")
#     print(f"Exception type: {type(e).__name__}")
#     print(f"Full class path: {e.__class__.__module__}.{e.__class__.__name__}")
#     print(f"Error class: {e.__class__}")

print()
print("##############################")
##############################

end_time = time.time()
elapsed_time = end_time - start_time

print(f"Execution time: {elapsed_time} seconds")
