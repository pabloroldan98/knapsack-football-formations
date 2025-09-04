import os
import sys
from datetime import datetime, timezone
import time
import pytz
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from jornadaperfecta import get_jornadaperfecta_data, get_players_start_probabilities_dict_jornadaperfecta
from analiticafantasy import get_analiticafantasy_data
from futbolfantasy_analytics import get_futbolfantasy_data
from futmondo import get_players_positions_dict_futmondo
from sofascore import get_players_ratings_list
from transfermarket_penalty_takers import get_penalty_takers_dict
from transfermarket_team_history import get_players_team_history_dict
from transfermarket_penalty_savers import get_penalty_savers_dict
from biwenger import get_biwenger_data_dict
from elo_ratings import get_teams_elos_dict


def safe_get_start_probabilities(label, file_name):
    try:
        print("----------------------------------------")
        print(f"- Scraping {label}:")
        data = get_players_start_probabilities_dict_jornadaperfecta(
            file_name=file_name,
            force_scrape=True
        )
        print(f"\n{label} - Start Probabilities:")
        for team, players in data.items():
            print(team, players)
        print()
        return data
    except Exception as e:
        print(f"Error scraping {label} Start Probabilities: {e}")
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
print("Scraping JORNADAPERFECTA...")
print("##############################")

# try:


    # laliga_prices, laliga_positions, laliga_forms, laliga_start_probabilities, laliga_price_trends = get_jornadaperfecta_data(
    #     price_file_name="jornadaperfecta_laliga_players_prices",
    #     positions_file_name="jornadaperfecta_laliga_players_positions",
    #     forms_file_name="jornadaperfecta_laliga_players_forms",
    #     start_probability_file_name="jornadaperfecta_laliga_players_start_probabilities",
    #     price_trends_file_name="jornadaperfecta_laliga_players_price_trends",
    #     force_scrape=True
    # )
    # print("Prices:")
    # for team, players in laliga_prices.items():
    #     print(team, players)
    # print("\nPositions:")
    # for team, players in laliga_positions.items():
    #     print(team, players)
    # print("\nForms:")
    # for team, players in laliga_forms.items():
    #     print(team, players)
    # print("\nStart Probabilities:")
    # for team, players in laliga_start_probabilities.items():
    #     print(team, players)
    # print("\nPrice Trends:")
    # for team, players in price_trends.items():
    #     print(team, players)
    # laliga_start_probabilities = get_players_start_probabilities_dict_jornadaperfecta(
    #     file_name="jornadaperfecta_laliga_players_start_probabilities",
    #     force_scrape=True
    # )
    # print("\nStart Probabilities:")
    # for team, players in laliga_start_probabilities.items():
    #     print(team, players)

laliga_start_probabilities = safe_get_start_probabilities(
    "LaLiga", "jornadaperfecta_laliga_players_start_probabilities"
)
premier_start_probabilities = safe_get_start_probabilities(
    "Premier League", "jornadaperfecta_premier_players_start_probabilities"
)
seriea_start_probabilities = safe_get_start_probabilities(
    "Serie A", "jornadaperfecta_seriea_players_start_probabilities"
)
bundesliga_start_probabilities = safe_get_start_probabilities(
    "Bundesliga", "jornadaperfecta_bundesliga_players_start_probabilities"
)
ligueone_start_probabilities = safe_get_start_probabilities(
    "Ligue 1", "jornadaperfecta_ligueone_players_start_probabilities"
)
segundadivision_start_probabilities = safe_get_start_probabilities(
    "Segunda División", "jornadaperfecta_segundadivision_players_start_probabilities"
)

champions_start_probabilities = safe_get_start_probabilities(
    "Champions League", "jornadaperfecta_champions_players_start_probabilities"
)
europaleague_start_probabilities = safe_get_start_probabilities(
    "Europa League", "jornadaperfecta_europaleague_players_start_probabilities"
)
conference_start_probabilities = safe_get_start_probabilities(
    "Conference League", "jornadaperfecta_conference_players_start_probabilities"
)
# mundialito_start_probabilities = safe_get_start_probabilities(
#     "Mundialito", "jornadaperfecta_mundialito_players_start_probabilities"
# )
#
# mundial_start_probabilities = safe_get_start_probabilities(
#     "Mundial", "jornadaperfecta_mundial_players_start_probabilities"
# )
# eurocopa_start_probabilities = safe_get_start_probabilities(
#     "Eurocopa", "jornadaperfecta_eurocopa_players_start_probabilities"
# )
# copaamerica_start_probabilities = safe_get_start_probabilities(
#     "Copa América", "jornadaperfecta_copaamerica_players_start_probabilities"
# )


# except Exception as e:
#     print(f"Error scraping JORNADAPERFECTA: {e}")
#     print(f"Exception type: {type(e).__name__}")
#     print(f"Full class path: {e.__class__.__module__}.{e.__class__.__name__}")
#     print(f"Error class: {e.__class__}")

print()
print("##############################")
##############################

end_time = time.time()
elapsed_time = end_time - start_time

print(f"Execution time: {elapsed_time} seconds")
