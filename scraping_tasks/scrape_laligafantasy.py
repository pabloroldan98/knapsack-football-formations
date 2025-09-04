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
from laligafantasy import get_laligafantasy_data
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
print("Scraping LaLigaFantasy...")
print("##############################")

try:
    laligafantasy_data = get_laligafantasy_data(
        write_file=True,
        file_name="laligafantasy_laliga_data",
        force_scrape=True
    )
    print()
    for player in laligafantasy_data:
        print(player)
    print("----------------------------------------")
except Exception as e:
    print(f"Error scraping LaLigaFantasy: {e}")
    print(f"Exception type: {type(e).__name__}")
    print(f"Full class path: {e.__class__.__module__}.{e.__class__.__name__}")
    print(f"Error class: {e.__class__}")

print()
print("##############################")
##############################

end_time = time.time()
elapsed_time = end_time - start_time

print(f"Execution time: {elapsed_time} seconds")
