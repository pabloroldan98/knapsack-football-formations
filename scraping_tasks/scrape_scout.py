import os
import sys
from datetime import datetime, timezone
import time
import pytz
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from scout import get_scout_data, get_players_start_probabilities_dict_scout
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
        data = get_players_start_probabilities_dict_scout(
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
print("Scraping SCOUT...")
print("##############################")


premier_start_probabilities = safe_get_start_probabilities(
    "Premier League", "scout_premier_players_start_probabilities"
)

print()
print("##############################")
##############################

end_time = time.time()
elapsed_time = end_time - start_time

print(f"Execution time: {elapsed_time} seconds")
