import ast
import copy
import gc
from pprint import pprint
# from pympler.tracker import SummaryTracker
from statistics import mean
import matplotlib.pyplot as plt
import math
import csv
import numpy as np

# Look at: https://stackoverflow.com/questions/74503207/knapsack-with-specific-amount-of-items-from-different-groups

from biwenger import get_championship_data
from group_knapsack import best_full_teams, best_transfers
from player import Player, \
    set_players_value_to_last_fitness, set_manual_boosts, set_penalty_boosts, \
    set_players_elo_dif, set_players_sofascore_rating, set_players_value, \
    set_positions, set_team_history_boosts, \
    purge_everything, purge_worse_value_players, purge_no_team_players, \
    purge_negative_values, fill_with_team_players, get_old_players_data
from OLD_group_knapsack import best_squads, best_teams
from sofascore import get_players_ratings_list
from team import Team, get_old_teams_data
from transfermarket_penalties import get_penalty_takers_dict
from transfermarket_team_history import get_players_team_history_dict
from futmondo import get_players_positions_dict


possible_formations = [
    [3, 4, 3],
    [3, 5, 2],
    [4, 3, 3],
    [4, 4, 2],
    [4, 5, 1],
    [5, 3, 2],
    [5, 4, 1],
    # [3, 3, 4],
    # [3, 6, 1],
    # [4, 2, 4],
    # [4, 6, 0],
    # [5, 2, 3],
]


def get_current_players(
        no_form=False,
        no_fixtures=False,
        no_home_boost=False,
        alt_fixture_method=False,
        no_penalty_boost=False,
        no_team_history_boost=False,
        no_manual_boost=True,
        players_manual_boosts=[],
        forced_matches=[],
        alt_positions=False,
        use_old_players_data=False,
        use_old_teams_data=False,
        use_comunio_price=False,
        ratings_file_name="sofascore_players_ratings",
        penalties_file_name="transfermarket_la_liga_penalty_takers",
        team_history_file_name="transfermarket_la_liga_team_history",
        alt_positions_file_name="futmondo_la_liga_players_positions"
):
    all_teams, all_players = get_championship_data(forced_matches=forced_matches, use_comunio_price=use_comunio_price)

    if use_old_teams_data:
        all_teams = get_old_teams_data(forced_matches)

    if use_old_players_data:
        all_players = get_old_players_data()

    players_ratings_list = get_players_ratings_list(file_name=ratings_file_name)

    partial_players_data = all_players
    if not no_manual_boost:
        partial_players_data = set_manual_boosts(partial_players_data, players_manual_boosts)
    if not no_penalty_boost:
        penalty_takers = get_penalty_takers_dict(file_name=penalties_file_name)
        partial_players_data = set_penalty_boosts(partial_players_data, penalty_takers)
    if alt_positions:
        players_positions = get_players_positions_dict(file_name=alt_positions_file_name)
        partial_players_data = set_positions(partial_players_data, players_positions)
    partial_players_data = set_players_elo_dif(partial_players_data, all_teams)
    if not no_team_history_boost:
        players_team_history = get_players_team_history_dict(file_name=team_history_file_name)
        partial_players_data = set_team_history_boosts(partial_players_data, players_team_history)
    partial_players_data = set_players_sofascore_rating(partial_players_data, players_ratings_list)
    full_players_data = set_players_value(partial_players_data, no_form, no_fixtures, no_home_boost, alt_fixture_method)

    return full_players_data


def get_last_jornada_players():
    all_teams, all_players = get_championship_data()
    return set_players_value_to_last_fitness(all_players)

# Begin:

# --------------------------------------------------------------------
# JORNADA 1:
# --------------------------------------------------------------------


# first_jornada_players = get_current_players(forced_matches=jornada_01, no_form=True)
# # print(len(first_jornada_players))
# first_jornada_players = purge_no_team_players(first_jornada_players)
# first_jornada_players = purge_negative_values(first_jornada_players)
# # first_jornada_players = sorted(first_jornada_players, key=lambda x: x.value, reverse=True)
# # for player in first_jornada_players:
# #     print(player)
# # print()
# first_jornada_players = purge_worse_value_players(first_jornada_players)
# # print(len(first_jornada_players))

# best_full_teams(first_jornada_players, possible_formations, 300)


# --------------------------------------------------------------------
# BEST POSSIBLE SQUAD OF THE LAST JORNADA
# --------------------------------------------------------------------


# last_jornada_players = get_last_jornada_players()
# best_full_teams(last_jornada_players, possible_formations, 300, super_verbose=True)


# --------------------------------------------------------------------
# BEST POSSIBLE CURRENT
# --------------------------------------------------------------------
# current_players = get_current_players()


current_players = get_current_players(
    no_form=False,
    no_fixtures=False,
    no_home_boost=False,
    alt_fixture_method=True,
    alt_positions=False,
    no_penalty_boost=False,
    no_manual_boost=True,
    use_old_players_data=False,
    use_old_teams_data=False,
    use_comunio_price=False,
    ratings_file_name="sofascore_la_liga_players_ratings"
)

# worthy_players = sorted(current_players, key=lambda x: x.value/x.price, reverse=True)
worthy_players = sorted(current_players, key=lambda x: x.value, reverse=True)

purged_players = purge_everything(worthy_players)

for player in worthy_players:
# for player in worthy_players:
#     if ((player.position=="ATT") | (player.position=="MID")): # & (player.value>=7) & (player.sofascore_rating>=7) & (player.form>1.01) & (player.fixture>=0.9):
#         print(player)
#     if player.sofascore_rating == 6:
#     if (player.position == "GK"):
#     if (player.team_history_boost > 0):
    print(player)
print()

print(len(purged_players))

# mega_purged_players = purge_everything(purged_players, mega_purge=True)


# --------------------------------------------------------------------
# THE METHOD CALL:
# --------------------------------------------------------------------

# best_transfers(my_team, mega_purged_players, 5, verbose=True)

needed_purge = purged_players[:50]


# best_full_teams(needed_purge, possible_formations, 30000, super_verbose=False)
best_full_teams(needed_purge, possible_formations, -1, super_verbose=False)


print()
my_players_names = [
    "Rodrygo",
    "Iago Aspas",
    "Williams",
    "Pepelu",
    "Kubo",
    "Sávio",
    "Alberto Moleiro",
    "Rüdiger",
    "Sergi Cardona",
    "Cancelo",
    "Sergio Herrera",
    "Artem Dovbyk",
    "David López",
    "Arda Güler",
    "Mayoral",
    "Sivera",
]
my_players_names = [
    "Ledesma",
    "Guaita",
    "Mendy",
    "Cristhian Mosquera",
    "Juan Miranda",
    "Diego Rico",
    "Kroos",
    "Isco",
    "Barrenetxea",
    "Frenkie De Jong",
    "Ander Herrera",
    "Mason Greenwood",
    "Budimir",
    "João Félix",
    "Cyle Larin",
]
my_players_names = [
    "Sergio Herrera",
    "Daley Blind",
    "Alex Suárez",
    "Sergio Ramos",
    "Manu Sánchez",
    "Kike Salas",
    "Aleix García",
    "Kroos",
    "Modric",
    "Camavinga",
    "Tchouameni",
    "Artem Dovbyk",
    "Sávio",
    "Rodrygo",
    "Morata",
    "Roman Yaremchuk",
    "Vitor Roque",
]
my_players_names = [
    "Guaita",
    "Acuña",
    "Foulquier",
    "Rubén Peña",
    "Diego Rico",
    "Saúl Coco",
    "Yellu Santiago",
    "Jordi Martín",
    "Fekir",
    "Tchouameni",
    "Mikel Merino",
    "Guevara",
    "Juanmi",
    "Gündogan",
    "Raul García de Haro",
    "Mason Greenwood",
    "Rodrygo",
    "Williams",
]

my_players_list = []
for player in worthy_players:
    if player.name in my_players_names:
        print(player)

for player in purged_players:
    if player.name in my_players_names:
        my_players_list.append(player)
        # print(player)

print()

best_full_teams(my_players_list, possible_formations, -1, super_verbose=False)



# mega_purge = purged_players[:60]
#
# mega_purge = fill_with_team_players(my_team, mega_purge)
#
# best_transfers(my_team, mega_purge, 5, n_results=25, by_n_transfers=False)





# --------------------------------------------------------------------
# PLOTTING STATS:
# --------------------------------------------------------------------


# fixtures = []
# next_match_elo_difs = []
# team_names = []
# # Populate the lists
# for player in purged_players:
#     fixtures.append(player.fixture)
#     next_match_elo_difs.append(player.next_match_elo_dif)
#     team_names.append(player.team)
#
# # Create the scatter plot
# plt.scatter(fixtures, next_match_elo_difs)
#
# # Annotate each point with the player's name
# for i, team_name in enumerate(team_names):
#     plt.annotate(team_name, (fixtures[i], next_match_elo_difs[i]))
#
# # Add axis labels and title
# plt.xlabel("Fixture")
# plt.ylabel("Next Match Elo Difference")
# plt.title("Fixture vs Next Match Elo Difference")
#
# # Show the plot
# plt.show()


# # Extract data for plotting
# standard_prices = [player.standard_price for player in purged_players]
# price_trends = [player.price_trend for player in purged_players]
#
# # Take the logarithms of the data
# log_standard_prices = np.log(standard_prices)
# # log_price_trends = np.log(price_trends)
#
#
# # Create the first plot: standard_price vs price_trend
# plt.figure(figsize=(10, 6))
# plt.scatter(standard_prices, price_trends, color='blue', label='Standard Price vs Price Trend')
# plt.xlabel('Standard Price')
# plt.ylabel('Price Trend')
# plt.title('Standard Price vs Price Trend')
# plt.legend()
# plt.grid()
#
# # Add player names as annotations
# for i, player in enumerate(purged_players):
#     plt.annotate(player.name, (standard_prices[i], price_trends[i]), textcoords="offset points", xytext=(0,10), ha='center')
#
# plt.tight_layout()  # To ensure the annotations fit nicely
#
# # Create the second plot: log(standard_price) vs log(price_trend)
# plt.figure(figsize=(10, 6))
# plt.scatter(log_standard_prices, price_trends, color='orange', label='Log(Standard Price) vs Log(Price Trend)')
# plt.xlabel('Log(Standard Price)')
# plt.ylabel('Price Trend')
# plt.title('Log(Standard Price) vs Price Trend')
# plt.legend()
# plt.grid()
#
# # Add player names as annotations
# for i, player in enumerate(purged_players):
#     plt.annotate(player.name, (log_standard_prices[i], price_trends[i]), textcoords="offset points", xytext=(0,10), ha='center')
#
# plt.tight_layout()  # To ensure the annotations fit nicely
#
# # Show the plots
# plt.show()


# --------------------------------------------------------------------
# Testing:
# --------------------------------------------------------------------

# all_teams, all_players = get_championship_data()
# for players in last_jornada_players:
#     print(players)

# best_transfers(my_team, playersDB_example, 4, n_results=50)

# all_teams, all_players = get_championship_data()
#
# print(len(gc.get_objects()))
# gc.collect()
# print(len(gc.get_objects()))
#
#
# count=dict()
# for player in all_players:
#     for team in all_teams:
#         if player.team == team.name:
#             count[player.team] = 0
#             print(player.team)
# print(len(count))

# max_elo = all_teams[0].elo
# for team in all_teams:
#     elo_dif = max_elo - team.elo
#     print(team)
#     print(elo_dif)
#
# for player in all_players:
#     print(player)

# best_full_teams(playersDB_example, possible_formations, 300)


# best_teams(playerDB, possible_formations, 300)

# best_squads(playerDB, possible_formations, 300)


# newlist = sorted(playerDB, key=lambda x: x.value/x.price, reverse=True)
# for player in newlist:
#     print(player)

# newlist = sorted(playerDB, key=lambda x: x.get_group())
# for player in newlist:
#     print(player)
#
#
# attrs = [o.name for o in playerDB]
#
# for playerName in attrs:
#     print(playerName)

