from datetime import datetime, timezone
import time
import pytz

from futbolfantasy_analytics import get_futbolfantasy_data
from futmondo import get_players_positions_dict
from sofascore import get_players_ratings_list
from transfermarket_penalties import get_penalty_takers_dict
from transfermarket_team_history import get_players_team_history_dict


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

prices, positions, forms, start_probabilities = get_futbolfantasy_data(
    price_file_name="futbolfantasy_laliga_players_prices",
    positions_file_name="futbolfantasy_laliga_players_positions",
    forms_file_name="futbolfantasy_laliga_players_forms",
    start_probability_file_name="futbolfantasy_laliga_players_start_probabilities",
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


print()
print("##############################")
##############################
print("Scraping FUTMONDO...")

players_positions_dict = get_players_positions_dict(file_name="futmondo_laliga_players_positions", force_scrape=True)

# Print the result in a readable way
for team, players in players_positions_dict.items():
    print(team, players)

print()
print("##############################")
##############################
print("Scraping TRANSFERMARKET (penalties)...")

penalty_takers = get_penalty_takers_dict(file_name="transfermarket_laliga_penalty_takers", force_scrape=True)

print(penalty_takers)
for team, penalties in penalty_takers.items():
    print(team, penalties)


if day_of_week == 1 and (month_of_year == 9 or month_of_year == 2):
    print()
    print("##############################")
    ##############################
    print("Scraping TRANSFERMARKET (team history)...")

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


if day_of_week == 1:
    print()
    print("##############################")
    ##############################
    print("Scraping SOFASCORE...")

    result = get_players_ratings_list(file_name="sofascore_laliga_players_ratings", force_scrape=True)#, team_links=team_links)

    for p in result:
        print(p)



print()
print("##############################")
##############################

end_time = time.time()
elapsed_time = end_time - start_time

print(f"Execution time: {elapsed_time} seconds")


