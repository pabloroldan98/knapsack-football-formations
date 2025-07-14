import os
import sys
from datetime import datetime, timezone
import time
import pytz
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

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
print("Scraping FUTBOLFANTASY...")

try:
    prices, positions, forms, start_probabilities, price_trends = get_futbolfantasy_data(
        price_file_name="futbolfantasy_laliga_players_prices",
        positions_file_name="futbolfantasy_laliga_players_positions",
        forms_file_name="futbolfantasy_laliga_players_forms",
        start_probability_file_name="futbolfantasy_laliga_players_start_probabilities",
        price_trends_file_name="futbolfantasy_laliga_players_price_trends",
        force_scrape=True
    )
    print("Prices:")
    for team, players in prices.items():
        print(team, players)
    print("\nPositions:")
    for team, players in positions.items():
        print(team, players)
    print("\nForms:")
    for team, players in forms.items():
        print(team, players)
    print("\nStart Probabilities:")
    for team, players in start_probabilities.items():
        print(team, players)
    print("\nPrice Trends:")
    for team, players in price_trends.items():
        print(team, players)
except Exception as e:
    print(f"Error scraping FUTBOLFANTASY: {e}")
    print(f"Exception type: {type(e).__name__}")
    print(f"Full class path: {e.__class__.__module__}.{e.__class__.__name__}")
    print(f"Error class: {e.__class__}")

print()
print("##############################")
##############################
print("Scraping FUTMONDO...")

try:
    players_positions_dict = get_players_positions_dict(file_name="futmondo_laliga_players_positions", force_scrape=True)
    # Print the result in a readable way
    for team, players in players_positions_dict.items():
        print(team, players)
except Exception as e:
    print(f"Error scraping FUTMONDO: {e}")
    print(f"Exception type: {type(e).__name__}")
    print(f"Full class path: {e.__class__.__module__}.{e.__class__.__name__}")
    print(f"Error class: {e.__class__}")

print()
print("##############################")
##############################
print("Scraping TRANSFERMARKET (penalty TAKERS)...")

try:
    penalty_takers = get_penalty_takers_dict(file_name="transfermarket_laliga_penalty_takers", force_scrape=True)
    print(penalty_takers)
    for team, penalties in penalty_takers.items():
        print(team, penalties)
except Exception as e:
    print(f"Error scraping TRANSFERMARKET (penalty TAKERS): {e}")
    print(f"Exception type: {type(e).__name__}")
    print(f"Full class path: {e.__class__.__module__}.{e.__class__.__name__}")
    print(f"Error class: {e.__class__}")

print()
print("##############################")
##############################
print("Scraping TRANSFERMARKET (penalty SAVERS)...")

try:
    penalty_savers = get_penalty_savers_dict(file_name="transfermarket_laliga_penalty_savers", force_scrape=True)
    print(penalty_savers)
    for team, penalties in penalty_savers.items():
        print(team, penalties)
except Exception as e:
    print(f"Error scraping TRANSFERMARKET (penalty SAVERS): {e}")
    print(f"Exception type: {type(e).__name__}")
    print(f"Full class path: {e.__class__.__module__}.{e.__class__.__name__}")
    print(f"Error class: {e.__class__}")

print()
print("##############################")
##############################
print("Scraping BIWENGER...")

try:
    biwenger_data = get_biwenger_data_dict(
        write_file=True,
        file_name="biwenger_laliga_data",
        force_scrape=True
    )
    print(biwenger_data)
except Exception as e:
    print(f"Error scraping BIWENGER: {e}")
    print(f"Exception type: {type(e).__name__}")
    print(f"Full class path: {e.__class__.__module__}.{e.__class__.__name__}")
    print(f"Error class: {e.__class__}")

print()
print("##############################")
##############################
print("Scraping ELO RATINGS...")

try:
    league_elo_ratings_dict = get_teams_elos_dict(
        is_country=False,
        country=None,
        extra_teams=False,
        write_file=True,
        file_name="elo_ratings_laliga_data",
        force_scrape=True
    )
    country_elo_ratings_dict = get_teams_elos_dict(
        is_country=True,
        write_file=True,
        file_name="elo_ratings_countries_data",
        force_scrape=True
    )
    print("League Elo Ratings:")
    for team, elo in league_elo_ratings_dict.items():
        print(f"{team}: {elo}")
    print("\nCountry Elo Ratings:")
    for team, elo in country_elo_ratings_dict.items():
        print(f"{team}: {elo}")
except Exception as e:
    print(f"Error scraping ELO RATINGS: {e}")
    print(f"Exception type: {type(e).__name__}")
    print(f"Full class path: {e.__class__.__module__}.{e.__class__.__name__}")
    print(f"Error class: {e.__class__}")

if day_of_week == 1 and (month_of_year == 9 or month_of_year == 2 or month_of_year == 8 or month_of_year == 1):
    print()
    print("##############################")
    ##############################
    print("Scraping TRANSFERMARKET (team history)...")

    try:
        players_team_history = get_players_team_history_dict(
            file_name="transfermarket_laliga_team_history",
            use_country_as_team=False,
            force_scrape=True
        )
        print(players_team_history)
        for team, players in players_team_history.items():
            print()
            print(team)
            for player, team_history in players.items():
                print(player, team_history)
    except Exception as e:
        print(f"Error scraping TRANSFERMARKET (team history): {e}")
        print(f"Exception type: {type(e).__name__}")
        print(f"Full class path: {e.__class__.__module__}.{e.__class__.__name__}")
        print(f"Error class: {e.__class__}")

if day_of_week == 1:
    print()
    print("##############################")
    ##############################
    print("Scraping SOFASCORE...")

    try:
        result = get_players_ratings_list(
            file_name="sofascore_laliga_players_ratings",
            backup_files=False,
            force_scrape=True
        )
        for p in result:
            print(p)
    except Exception as e:
        print(f"Error scraping SOFASCORE: {e}")
        print(f"Exception type: {type(e).__name__}")
        print(f"Full class path: {e.__class__.__module__}.{e.__class__.__name__}")
        print(f"Error class: {e.__class__}")

print()
print("##############################")
##############################

end_time = time.time()
elapsed_time = end_time - start_time

print(f"Execution time: {elapsed_time} seconds")
