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


def safe_get_team_history(label, file_name, use_country_as_team=False):
    try:
        print("----------------------------------------")
        print(f"- Scraping {label}:")
        data = get_players_team_history_dict(
            file_name=file_name,
            use_country_as_team=use_country_as_team,
            force_scrape=True
        )
        print(f"\n{label} — Team History:")
        for team, players in data.items():
            print()
            print(team)
            for player, team_history in players.items():
                print(player, team_history)
        time.sleep(60)
        print()
        return data
    except Exception as e:
        print(f"Error scraping {label} Team History: {e}")
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
print("Scraping TRANSFERMARKET (team history)...")
print("##############################")

# try:


    # players_team_history = get_players_team_history_dict(
    #     file_name="transfermarket_laliga_team_history",
    #     use_country_as_team=False,
    #     force_scrape=True
    # )
    # for team, players in players_team_history.items():
    #     print()
    #     print(team)
    #     for player, team_history in players.items():
    #         print(player, team_history)


# except Exception as e:
#     print(f"Error scraping TRANSFERMARKET (team history): {e}")
#     print(f"Exception type: {type(e).__name__}")
#     print(f"Full class path: {e.__class__.__module__}.{e.__class__.__name__}")
#     print(f"Error class: {e.__class__}")


laliga_team_history = safe_get_team_history("LaLiga", "transfermarket_laliga_team_history", use_country_as_team=False)
premier_team_history = safe_get_team_history("Premier League", "transfermarket_premier_team_history", use_country_as_team=False)
seriea_team_history = safe_get_team_history("Serie A", "transfermarket_seriea_team_history", use_country_as_team=False)
bundesliga_team_history = safe_get_team_history("Bundesliga", "transfermarket_bundesliga_team_history", use_country_as_team=False)
ligueone_team_history = safe_get_team_history("Ligue 1", "transfermarket_ligueone_team_history", use_country_as_team=False)
segunda_team_history = safe_get_team_history("Segunda División", "transfermarket_segunda_team_history", use_country_as_team=False)

champions_team_history = safe_get_team_history("Champions League", "transfermarket_champions_team_history", use_country_as_team=False)
europaleague_team_history = safe_get_team_history("Europa League", "transfermarket_europaleague_team_history", use_country_as_team=False)
conference_team_history = safe_get_team_history("Conference League", "transfermarket_conference_team_history", use_country_as_team=False)
# mundialito_team_history = safe_get_team_history("Mundialito", "transfermarket_mundialito_team_history", use_country_as_team=False)
#
# mundial_team_history = safe_get_team_history("Mundial", "transfermarket_mundial_team_history", use_country_as_team=True)
# eurocopa_team_history = safe_get_team_history("Eurocopa", "transfermarket_eurocopa_team_history", use_country_as_team=True)
# copaamerica_team_history = safe_get_team_history("Copa América", "transfermarket_copaamerica_team_history", use_country_as_team=True)


print()
print("##############################")
##############################

end_time = time.time()
elapsed_time = end_time - start_time

print(f"Execution time: {elapsed_time} seconds")
