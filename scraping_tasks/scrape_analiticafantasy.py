import os
import sys
from datetime import datetime, timezone
import time
import pytz
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from analiticafantasy import get_analiticafantasy_data
from futbolfantasy_analytics import get_futbolfantasy_data
from futmondo import get_players_positions_dict
from sofascore import get_players_ratings_list
from transfermarket_penalty_takers import get_penalty_takers_dict
from transfermarket_team_history import get_players_team_history_dict
from transfermarket_penalty_savers import get_penalty_savers_dict
from biwenger import get_biwenger_data_dict
from elo_ratings import get_teams_elos_dict


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
print("Scraping ANALITICAFANTASY...")

try:
    start_probabilities = get_analiticafantasy_data(
        start_probability_file_name="analiticafantasy_laliga_players_start_probabilities",
        force_scrape=True
    )
    print("\nStart Probabilities:")
    for team, players in start_probabilities.items():
        print(team, players)
except Exception as e:
    print(f"Error scraping ANALITICAFANTASY: {e}")
    print(f"Exception type: {type(e).__name__}")
    print(f"Full class path: {e.__class__.__module__}.{e.__class__.__name__}")
    print(f"Error class: {e.__class__}")

print()
print("##############################")
##############################

end_time = time.time()
elapsed_time = end_time - start_time

print(f"Execution time: {elapsed_time} seconds")
