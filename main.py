# from pympler.tracker import SummaryTracker

# Look at: https://stackoverflow.com/questions/74503207/knapsack-with-specific-amount-of-items-from-different-groups

from biwenger import get_championship_data
from futbolfantasy_analytics import get_players_prices_dict, get_players_forms_dict, \
    get_players_start_probabilities_dict, get_players_price_trends_dict
from group_knapsack import best_full_teams
from player import set_players_value_to_last_fitness, set_manual_boosts, set_penalty_takers_boosts, \
    set_players_elo_dif, set_players_sofascore_rating, set_players_value, \
    set_positions, set_team_history_boosts, \
    purge_everything, get_old_players_data, set_prices, set_forms, set_start_probabilities, \
    set_price_trends, set_penalty_savers_boosts
from sofascore import get_players_ratings_list
from team import get_old_teams_data, set_team_status_nerf
from transfermarket_penalty_savers import get_penalty_savers_dict
from transfermarket_penalty_takers import get_penalty_takers_dict
from transfermarket_team_history import get_players_team_history_dict
from futmondo import get_players_positions_dict
from useful_functions import find_similar_string

possible_formations = [
    # [2, 2, 2],
    # [0, 1, 1, 0],

    [3, 4, 3],
    [3, 5, 2],
    [4, 3, 3],
    [4, 4, 2],
    [4, 5, 1],
    [5, 3, 2],
    [5, 4, 1],

    # [3, 3, 4],
    # # [3, 6, 1],
    # [4, 2, 4],
    # # [4, 6, 0],
    # [5, 2, 3],
]


def get_current_players(
        no_form=False,
        no_fixtures=False,
        no_home_boost=False,
        alt_fixture_method=False,
        no_penalty_takers_boost=False,
        no_penalty_savers_boost=False,
        no_team_history_boost=False,
        no_manual_boost=True,
        players_manual_boosts=[],
        forced_matches=[],
        is_country=False,
        host_team=None,
        alt_positions=False,
        alt_prices=False,
        alt_price_trends=False,
        alt_forms=False,
        add_start_probability=False,
        no_team_status_nerf=False,
        use_old_players_data=False,
        use_old_teams_data=False,
        use_comunio_price=False,
        ratings_file_name="sofascore_players_ratings",
        penalty_takers_file_name="transfermarket_la_liga_penalty_takers",
        penalty_saves_file_name="transfermarket_laliga_penalty_savers",
        team_history_file_name="transfermarket_la_liga_team_history",
        alt_positions_file_name="futmondo_la_liga_players_positions",
        alt_prices_file_name="futbolfantasy_laliga_players_prices",
        alt_price_trends_file_name="futbolfantasy_laliga_players_price_trends",
        alt_forms_file_name="futbolfantasy_laliga_players_forms",
        start_probabilit_file_name="futbolfantasy_laliga_players_start_probabilities",
        debug=False
):
    all_teams, all_players = get_championship_data(forced_matches=forced_matches, is_country=is_country, host_team=host_team, use_comunio_price=use_comunio_price)
    if debug:
        print("000000")

    if use_old_teams_data:
        all_teams = get_old_teams_data(forced_matches)
    if debug:
        print("111111")

    if use_old_players_data:
        all_players = get_old_players_data()
    if debug:
        print("222222")

    players_ratings_list = get_players_ratings_list(file_name=ratings_file_name)

    partial_players_data = all_players
    if not no_manual_boost:
        partial_players_data = set_manual_boosts(partial_players_data, players_manual_boosts)
    if debug:
        print("333333")
    if alt_positions:
        players_positions = get_players_positions_dict(file_name=alt_positions_file_name)
        partial_players_data = set_positions(partial_players_data, players_positions, verbose=False)
    if debug:
        print("444444")
    if not no_penalty_takers_boost:
        penalty_takers = get_penalty_takers_dict(file_name=penalty_takers_file_name)
        partial_players_data = set_penalty_takers_boosts(partial_players_data, penalty_takers)
    if debug:
        print("555555")
    if not no_penalty_savers_boost:
        penalty_savers = get_penalty_savers_dict(file_name=penalty_saves_file_name)
        partial_players_data = set_penalty_savers_boosts(partial_players_data, penalty_savers)
    if debug:
        print("666666")
    if alt_prices:
        players_prices = get_players_prices_dict(file_name=alt_prices_file_name)
        partial_players_data = set_prices(partial_players_data, players_prices, verbose=False)
    if debug:
        print("777777")
    if alt_price_trends:
        players_price_trends = get_players_price_trends_dict(file_name=alt_price_trends_file_name)
        players_standard_prices=None
        if alt_prices:
            players_standard_prices = get_players_prices_dict(file_name=alt_prices_file_name)
        partial_players_data = set_price_trends(partial_players_data, players_price_trends, players_standard_prices, verbose=False)
    if debug:
        print("888888")
    if add_start_probability:
        players_start_probabilities = get_players_start_probabilities_dict(file_name=start_probabilit_file_name)
        partial_players_data = set_start_probabilities(partial_players_data, players_start_probabilities, verbose=False)
    if debug:
        print("999999")
    if not no_team_status_nerf:
        all_teams = set_team_status_nerf(all_teams, verbose=False)
    if debug:
        print("AAAAAA")
    partial_players_data = set_players_elo_dif(partial_players_data, all_teams)
    if debug:
        print("BBBBBB")
    if not no_team_history_boost:
        players_team_history = get_players_team_history_dict(file_name=team_history_file_name)
        partial_players_data = set_team_history_boosts(partial_players_data, players_team_history, verbose=False)
    if debug:
        print("CCCCCC")
    partial_players_data = set_players_sofascore_rating(partial_players_data, players_ratings_list)
    if debug:
        print("DDDDDD")
    if alt_forms and not no_form:
        players_form = get_players_forms_dict(file_name=alt_forms_file_name)
        partial_players_data = set_forms(partial_players_data, players_form)
    if debug:
        print("EEEEEE")
    full_players_data = set_players_value(partial_players_data, no_form, no_fixtures, no_home_boost, alt_fixture_method, alt_forms)
    if debug:
        print("FFFFFF")

    return full_players_data


def get_last_jornada_players():
    all_teams, all_players = get_championship_data()
    return set_players_value_to_last_fitness(all_players)


print()

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
# best_full_teams(last_jornada_players, possible_formations, 300, verbose=2)


# --------------------------------------------------------------------
# BEST POSSIBLE CURRENT
# --------------------------------------------------------------------
# current_players = get_current_players()


current_players = get_current_players(
    no_form=False,
    no_fixtures=False,
    no_home_boost=False,
    no_team_history_boost=False,
    alt_fixture_method=False,
    alt_positions=True,
    alt_prices=True,
    alt_price_trends=True,
    alt_forms=True,
    add_start_probability=True,
    no_penalty_takers_boost=False,
    no_penalty_savers_boost=False,
    no_team_status_nerf=False,
    no_manual_boost=True,
    use_old_players_data=False,
    use_old_teams_data=False,
    use_comunio_price=True,
    ratings_file_name="sofascore_laliga_players_ratings",
    penalty_takers_file_name="transfermarket_laliga_penalty_takers",
    penalty_saves_file_name="transfermarket_laliga_penalty_savers",
    team_history_file_name="transfermarket_laliga_team_history",
    # alt_positions_file_name="futmondo_la_liga_players_positions",
    alt_positions_file_name="futbolfantasy_laliga_players_positions",
    alt_prices_file_name="futbolfantasy_laliga_players_prices",
    alt_price_trends_file_name="futbolfantasy_laliga_players_price_trends",
    alt_forms_file_name="futbolfantasy_laliga_players_forms",
    start_probabilit_file_name="futbolfantasy_laliga_players_start_probabilities",
    is_country=False,
    # host_team="Germany",
    debug=False,
    # forced_matches=jornada_XX,
)
    # ratings_file_name = "sofascore_copa_america_players_ratings",
    # penalty_takers_file_name="transfermarket_copa_america_penalty_takers",
    # team_history_file_name="transfermarket_copa_america_country_history",
    # # alt_positions_file_name="futmondo_la_liga_players_positions",
    # is_country=True,
    # host_team="US",
    # debug=False,
# )

# # FOR MULTIPLE JORNADAS
# # Update current_players in-place
# for current_player in current_players:
#     for future_player in future_players:
#         if current_player.name == future_player.name:
#             # Calculate the mean of value, form, and fixture
#             current_player.value = (current_player.value + future_player.value) / 2
#             current_player.form = (current_player.form + future_player.form) / 2
#             current_player.fixture = (current_player.fixture + future_player.fixture) / 2


# current_players = sorted(current_players, key=lambda x: (x.value-7)/max(x.price, 1), reverse=True)
current_players = sorted(
    current_players,
    key=lambda x: (-x.value, -x.form, -x.fixture, x.price, x.team),
    reverse=False
)


worthy_players = current_players.copy()

# worthy_players = [player for player in worthy_players if player.price > 0]
worthy_players = [player for player in worthy_players if player.price >= 0]


print()
for player in worthy_players:
#     if (player.name == "XXX"):
#         print(player)
#     if (player.price <= 25) & (player.start_probability >= 0.6) & (player.position == "DEF"):# & (player.form > 1) & (player.fixture > 1):
#     if player.sofascore_rating == 6:
#     if (player.position == "GK"):
#     if ((player.position=="ATT") | (player.position=="MID")): # & (player.value>=7) & (player.sofascore_rating>=7) & (player.form>1.01) & (player.fixture>=0.9):
#     if (player.team_history_boost > 0):
    print(player)
    # print((player.standard_price/player.price)/300000)
print()

# print(len(worthy_players))
print("------------------------- PURGED PLAYERS -------------------------")

worthy_players_og = worthy_players.copy()

purged_players = purge_everything(worthy_players, probability_threshold=0.6, fixture_filter=True)
worthy_players = purged_players.copy()


print()
for player in worthy_players:
    print(player)
print()

# purged_players = worthy_players.copy()
# worthy_players = purged_players.copy()

# mega_purged_players = purge_everything(purged_players, mega_purge=True)


# --------------------------------------------------------------------
# THE METHOD CALL:
# --------------------------------------------------------------------

# best_transfers(my_team, mega_purged_players, 5, verbose=True)

# needed_purge = purged_players[:50]
# needed_purge = worthy_players[:150]
# needed_purge = [player for player in worthy_players if player.price > 7]
# needed_purge = [player for player in worthy_players if (player.form >=1 and player.fixture >=1)]
needed_purge = worthy_players[:150]
# needed_purge = worthy_players.copy()



#
# needed_purge = [player for player in needed_purge if player.name != "XXXXXX"]
# needed_purge = [player for player in needed_purge if player.name != "XXXXXX"]
# needed_purge = [player for player in needed_purge if player.name != "XXXXXX"]
#
# needed_purge = [player for player in needed_purge if player.price > 7]
#
#
# best_full_teams(needed_purge, possible_formations, 14+61+75+30, verbose=2)



# best_full_teams(needed_purge, possible_formations, 25, verbose=2)
# best_full_teams(needed_purge, possible_formations, 210, verbose=2)



################################################### CHECK YOUR TEAM ###################################################



print()
print("------------------------- YOUR TEAM -------------------------")
print()
my_players_names = [
    "Sergio Herrera",
    "Álvaro Fernández",
    "Luiz Júnior",
    "Dimitrievski",

    "Kiko Femenía",
    "Luis Pérez",
    "Krejci",
    "Maffeo",
    "Cabrera",
    "El Hilali",
    "Blind",

    "Luka Sucic",
    "Puado",
    "Jordán",
    "Marc Casadó",
    "Kike Pérez",

    "Raphinha",
    "Yamal",
    "Yéremy Pino",
    "Oyarzabal",
]

# my_players_names = [
#     "Juan Soriano",
#     "Koundé",
#     "Boyomo",
#     "Iñigo Martínez",
#     "Azpilicueta",
#     "Valverde",
#     "Uche",
#     "Rubén García",
#     "Raphinha",
#     "Bryan Gil",
#     "Vinícius Jr",
# ]


my_players_list = []
for player in current_players:
    if player.name in my_players_names:
        print(player)

print()
print("------------------------- BEST FORMATIONS -------------------------")
print()
for player in purged_players:
    if player.name in my_players_names:
        my_players_list.append(player)
        # print(player)

print()
#
best_full_teams(my_players_list, possible_formations, -1, verbose=1)






################################################### BEST TRANSFERS ###################################################




# mega_purge = purged_players[:60]
#
# mega_purge = fill_with_team_players(my_team, mega_purge)
#
# best_transfers(my_team, mega_purge, 5, n_results=25, by_n_transfers=False)




################################################### PLOT DATA ###################################################




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


# Extract data for plotting
standard_prices = [player.standard_price for player in worthy_players]
price_trends = [player.price_trend for player in worthy_players]
prices = [player.price for player in worthy_players]
#
# # Take the logarithms of the data
# log_standard_prices = np.log(np.abs(standard_prices)) * np.sign(standard_prices)
# log_price_trends = np.log(np.abs(price_trends)) * np.sign(price_trends)
# log_prices = np.log(prices)
#
#
# Create the first plot: standard_price vs price_trend
# plt.figure(figsize=(10, 6))
# plt.scatter(standard_prices, price_trends, color='blue', label='Standard Price vs Price Trend')
# plt.xlabel('Standard Price')
# plt.ylabel('Price Trend')
# plt.title('Standard Price vs Price Trend')
# plt.legend()
# plt.grid()
#
# # Add player names as annotations
# for i, player in enumerate(worthy_players):
#     plt.annotate(player.name, (standard_prices[i], price_trends[i]), textcoords="offset points", xytext=(0,10), ha='center')
#
# plt.tight_layout()  # To ensure the annotations fit nicely
#
# # Create the second plot: log(standard_price) vs log(price_trend)
# plt.figure(figsize=(10, 6))
# plt.scatter(log_standard_prices, price_trends, color='orange', label='Log(Standard Price) vs Price Trend')
# plt.xlabel('Log(Standard Price)')
# plt.ylabel('Price Trend')
# plt.title('Log(Standard Price) vs Price Trend')
# plt.legend()
# plt.grid()
#
# # Add player names as annotations
# for i, player in enumerate(worthy_players):
#     plt.annotate(player.name, (log_standard_prices[i], price_trends[i]), textcoords="offset points", xytext=(0,10), ha='center')
#
# plt.tight_layout()  # To ensure the annotations fit nicely
# # Create the second plot: log(standard_price) vs log(price_trend)
# plt.figure(figsize=(10, 6))
# plt.scatter(standard_prices, log_price_trends, color='orange', label='Standard Price vs Log(Price Trend)')
# plt.xlabel('Standard Price')
# plt.ylabel('Log(Price Trend)')
# plt.title('Standard Price vs Log(Price Trend)')
# plt.legend()
# plt.grid()
#
# # Add player names as annotations
# for i, player in enumerate(worthy_players):
#     plt.annotate(player.name, (standard_prices[i], log_price_trends[i]), textcoords="offset points", xytext=(0,10), ha='center')
#
# plt.tight_layout()  # To ensure the annotations fit nicely
# # Create the second plot: log(standard_price) vs log(price_trend)
# plt.figure(figsize=(10, 6))
# plt.scatter(log_price_trends, standard_prices, color='orange', label='Log(Price Trend) vs Standard Price')
# plt.xlabel('Log(Price Trend)')
# plt.ylabel('Standard Price')
# plt.title('Log(Price Trend) vs Standard Price')
# plt.legend()
# plt.grid()
#
# # Add player names as annotations
# for i, player in enumerate(worthy_players):
#     plt.annotate(player.name, (log_price_trends[i], standard_prices[i]), textcoords="offset points", xytext=(0,10), ha='center')
#
# plt.tight_layout()  # To ensure the annotations fit nicely
#
# Create the second plot: log(standard_price) vs log(price_trend)
# plt.figure(figsize=(10, 6))
# plt.scatter(log_standard_prices, log_price_trends, color='orange', label='Log(Standard Price) vs Log(Price Trend)')
# plt.xlabel('Log(Standard Price)')
# plt.ylabel('Log(Price Trend)')
# plt.title('Log(Standard Price) vs Log(Price Trend)')
# plt.legend()
# plt.grid()
#
# # Add player names as annotations
# for i, player in enumerate(worthy_players):
#     plt.annotate(player.name, (log_standard_prices[i], log_price_trends[i]), textcoords="offset points", xytext=(0,10), ha='center')
#
# plt.tight_layout()  # To ensure the annotations fit nicely
#
#
# # Create the second plot: log(standard_price) vs log(price_trend)
# plt.figure(figsize=(10, 6))
# plt.scatter(prices, standard_prices, color='orange', label='Price vs Standard Price')
# plt.xlabel('Price')
# plt.ylabel('Standard Price')
# plt.title('Price vs Standard Price')
# plt.legend()
# plt.grid()
#
# # Add player names as annotations
# for i, player in enumerate(worthy_players):
#     plt.annotate(player.name, (prices[i], standard_prices[i]), textcoords="offset points", xytext=(0,10), ha='center')
#
# plt.tight_layout()  # To ensure the annotations fit nicely
#
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
#
#
# CHECK SIMILAR PLAYERS IN DB
#
# import csv
#
# # Read the dictionary from the CSV file
# with open('./csv_files/sofascore_laliga_players_ratings.csv', 'r', encoding='utf-8') as file:
#     reader = csv.reader(file)
#     data_dict = {row[0]: row[1] for row in reader}  # Convert rows into a dictionary
#
# # Iterate through the dictionary and check each name against its list
# for team, players in data_dict.items():
#     print(f"Checking for similarities in team: {team}")
#     # Convert the string representation of the dictionary to an actual Python dictionary
#     players_dict = eval(players)
#     player_names = list(players_dict.keys())
#
#     # Iterate through each player's name
#     for player in player_names:
#         # Create a new list excluding the current player
#         other_players = [p for p in player_names if p != player]
#
#         # Call the function to find similar players
#         similar_player = find_similar_string(player, other_players, similarity_threshold=0.7, verbose=False)
#         if similar_player and similar_player != player:
#             print(f"Similar names found: '{player}' and '{similar_player}' in team '{team}'.")
