import ast
import copy
import gc
from pprint import pprint
# from pympler.tracker import SummaryTracker
from statistics import mean
import matplotlib.pyplot as plt
import math
import csv

# Look at: https://stackoverflow.com/questions/74503207/knapsack-with-specific-amount-of-items-from-different-groups

from biwenger import get_championship_data
from group_knapsack import best_full_teams, best_transfers
from player import Player, set_players_value_to_last_fitness, set_manual_boosts, \
    set_players_elo_dif, set_players_sofascore_rating, set_players_value, \
    purge_everything, purge_worse_value_players, purge_no_team_players, \
    purge_negative_values, fill_with_team_players, get_old_players_data, set_penalty_takers_boosts
from OLD_group_knapsack import best_squads, best_teams
from sofascore import get_players_ratings_list
from team import Team, get_old_teams_data
from transfermarket_penalty_takers import get_penalty_takers_dict

playersDB_example = [
    Player("Mendy", "GK", 20, 6.8, "SEN"),
    Player("Matt Turner", "GK", 11, 7.4, "USA"),
    Player("Szczesny", "GK", 19, 7.4, "POL"),
    Player("Schmeichel", "GK", 12, 7.2, "DIN"),
    Player("Keylor Navas", "GK", 16, 7.5, "COS"),
    Player("Neuer", "GK", 22, 7.5, "ALE"),
    Player("Livakovic", "GK", 17, 7.3, "CRO"),
    Player("Allison", "GK", 27, 7.4, "BRA"),
    Player("Onana", "GK", 16, 7.1, "CAM"),

    Player("Blind", "DEF", 20, 7, "HOL"),
    Player("Van Dijk", "DEF", 31, 7.1, "HOL"),
    Player("Shaw", "DEF", 21, 7.2, "ING"),
    Player("Stones", "DEF", 25, 7.1, "ING"),
    Player("Otamendi", "DEF", 20, 7.3, "ARG"),
    Player("Rubén Días", "DEF", 31, 7.1, "POR"),
    Player("Laporte", "DEF", 23, 7.2, "ESP"),
    Player("Mahele", "DEF", 21, 6.5, "DIN"),
    Player("Nuno", "DEF", 24, 7.1, "POR"),

    Player("Caicedo", "MID", 19, 7.1, "ECU"),
    Player("De Jong", "MID", 44, 7.3, "HOL"),
    Player("Bellingham", "MID", 32, 7.5, "ING"),
    Player("Foden", "MID", 37, 7.2, "ING"),
    Player("De Paul", "MID", 27, 7.4, "ARG"),
    Player("Eriksen", "MID", 25, 7.5, "DIN"),
    Player("De Bruyne", "MID", 38, 8, "BEL"),
    Player("Tielemans", "MID", 24, 7.3, "BEL"),
    Player("Modric", "MID", 22, 7.2, "CRO"),
    Player("Perisic", "MID", 25, 6.9, "CRO"),
    Player("Bruno Fernandes", "MID", 37, 7.8, "POR"),
    Player("Pedri", "MID", 31, 7.6, "ESP"),
    Player("Busquets", "MID", 21, 7.1, "ESP"),
    Player("Havertz", "MID", 30, 6.9, "ALE"),
    Player("Kimmich", "MID", 38, 7.6, "ALE"),
    Player("Gundogan", "MID", 28, 7.1, "ALE"),
    Player("Hojbjerg", "MID", 29, 6.8, "DIN"),
    Player("Valverde", "MID", 29, 7.8, "URU"),
    Player("Gueye", "MID", 19, 7, "SEN"),

    Player("Mbappe", "ATT", 75, 7.5, "FRA"),
    Player("Lewandowsik", "ATT", 51, 0, "POL"),
    Player("Messi", "ATT", 51, 8.2, "ARG"),
    Player("Kane", "ATT", 50, 7.7, "ING"),
    Player("Neymar", "ATT", 50, 7.5, "BRA"),
    Player("Depay", "ATT", 46, 0, "HOL"),
    Player("Benzema", "ATT", 41, 0, "FRA"),
    Player("Lukaku", "ATT", 40, 0, "BEL"),
    Player("Lautaro", "ATT", 40, 0, "ARG"),
    Player("Vlahovic", "ATT", 36, 0, "SER"),
    Player("Sterling", "ATT", 34, 0, "ING"),
    Player("Dani Olmo", "ATT", 34, 0, "ESP"),
    Player("Jonathan David", "ATT", 33, 0, "CAN"),
    Player("Gakpo", "ATT", 33, 7.4, "HOL"),
    Player("Griezmann", "ATT", 31, 7.7, "FRA"),
    Player("Morata", "ATT", 31, 0, "ESP"),
    Player("CR7", "ATT", 31, 0, "POR"),
    Player("Raphinha", "ATT", 31, 7.4, "BRA"),
    Player("Di María", "ATT", 22, 7.4, "ARG"),
    Player("Luis Suárez", "ATT", 22, 6.8, "URU"),
    Player("Valencia", "ATT", 16, 7.3, "ECU"),

]

possible_formations = [
    [3, 4, 3],
    [3, 5, 2],
    [4, 3, 3],
    [4, 4, 2],
    [4, 5, 1],
    [5, 3, 2],
    [5, 4, 1],
]

players_manual_boosts = [
    Player("Al-Haydos", penalty_boost=0.7, strategy_boost=0.1),
    Player("Afif", penalty_boost=0, strategy_boost=0.1),

    Player("Enner Valencia", penalty_boost=0.7, strategy_boost=0),
    Player("Estupiñán", penalty_boost=0, strategy_boost=0.1),
    Player("Ángel Mena", penalty_boost=0, strategy_boost=0.1),

    Player("Depay", penalty_boost=0.7, strategy_boost=0.1),
    Player("Berghuis", penalty_boost=0, strategy_boost=0.1),

    Player("Sadio Mane", penalty_boost=0.7, strategy_boost=0.1),
    Player("Boulaye Dia", penalty_boost=0.35, strategy_boost=0),
    Player("Ismaila Sarr", penalty_boost=0.35, strategy_boost=0),
    Player("Idrissa Gueye", penalty_boost=0, strategy_boost=0.1),

    Player("Harry Kane", penalty_boost=0.7, strategy_boost=0),
    Player("Arnold", penalty_boost=0, strategy_boost=0.1),
    Player("Trippier", penalty_boost=0, strategy_boost=0.1),

    Player("Gareth Bale", penalty_boost=0.7, strategy_boost=0.1),
    Player("Harry Wilson", penalty_boost=0, strategy_boost=0.1),

    Player("Pulisic", penalty_boost=0.7, strategy_boost=0.1),
    Player("Reyna", penalty_boost=0, strategy_boost=0.1),

    Player("Taremi", penalty_boost=0.7, strategy_boost=0),
    Player("Sholizadeh", penalty_boost=0, strategy_boost=0.1),
    Player("Jahanbaksh", penalty_boost=0, strategy_boost=0.1),

    Player("Messi", penalty_boost=0.7, strategy_boost=0.1),
    Player("Di María", penalty_boost=0, strategy_boost=0.1),

    Player("Lewandowski", penalty_boost=0.7, strategy_boost=0.1),
    Player("Zielinski", penalty_boost=0, strategy_boost=0.1),

    Player("Al-Faraj", penalty_boost=0.7, strategy_boost=0.1),
    Player("Al-Dawsari", penalty_boost=0, strategy_boost=0.1),

    Player("Raúl Jiménez", penalty_boost=0.7, strategy_boost=0),
    Player("Orbelín Pineda", penalty_boost=0.1, strategy_boost=0),
    Player("Hirving Lozano", penalty_boost=0.2, strategy_boost=0),
    Player("Alexis Vega", penalty_boost=0.2, strategy_boost=0),
    Player("Héctor Herrera", penalty_boost=0, strategy_boost=0.1),
    Player("Guardado", penalty_boost=0, strategy_boost=0.1),

    Player("Mbappe", penalty_boost=0.7, strategy_boost=0),
    Player("Griezmann", penalty_boost=0, strategy_boost=0.1),
    Player("Theo Hernández", penalty_boost=0, strategy_boost=0.1),

    Player("Jamie Maclaren", penalty_boost=0.7, strategy_boost=0),
    Player("Jason Cummings", penalty_boost=0.3, strategy_boost=0),
    Player("Craig Goodwin", penalty_boost=0.2, strategy_boost=0),
    Player("Aaron Moy", penalty_boost=0.5, strategy_boost=0.1),
    Player("Hrustic", penalty_boost=0, strategy_boost=0.1),

    Player("Eriksen", penalty_boost=0.7, strategy_boost=0.1),
    Player("Braithwaite", penalty_boost=0, strategy_boost=0.1),

    Player("Khazri", penalty_boost=0.7, strategy_boost=0.1),
    Player("Laïdouni", penalty_boost=0, strategy_boost=0.1),

    Player("Morata", penalty_boost=0.7, strategy_boost=0),
    Player("Ferrán Torres", penalty_boost=0.4, strategy_boost=0),
    Player("Pablo Sarabia", penalty_boost=0, strategy_boost=0.1),
    Player("Koke", penalty_boost=0, strategy_boost=0.1),

    Player("Celso Borges", penalty_boost=0.7, strategy_boost=0.1),
    Player("Joel Campbell", penalty_boost=0, strategy_boost=0.1),

    Player("Kamada", penalty_boost=0.3, strategy_boost=0),
    Player("Ritsu Doan", penalty_boost=0.5, strategy_boost=0),
    Player("Minamino", penalty_boost=0.5, strategy_boost=0),
    Player("Takefusa Kubo", penalty_boost=0, strategy_boost=0.1),
    Player("Kaoru Mitoma", penalty_boost=0, strategy_boost=0.1),

    Player("Gundogan", penalty_boost=0.7, strategy_boost=0.1),
    Player("Kimmich", penalty_boost=0, strategy_boost=0.1),

    Player("Lukaku", penalty_boost=0.7, strategy_boost=0),
    Player("Eden Hazard", penalty_boost=0.5, strategy_boost=0),
    Player("De Bruyne", penalty_boost=0, strategy_boost=0.1),
    Player("Carrasco", penalty_boost=0, strategy_boost=0.1),

    Player("Cyle Larin", penalty_boost=0.7, strategy_boost=0),
    Player("Alphonso Davies", penalty_boost=0.4, strategy_boost=0.1),
    Player("Eustáquio", penalty_boost=0, strategy_boost=0.1),

    Player("Modric", penalty_boost=0.7, strategy_boost=0.1),
    Player("Brozovic", penalty_boost=0, strategy_boost=0.1),

    Player("Boufal", penalty_boost=0.7, strategy_boost=0),
    Player("Ziyech", penalty_boost=0.35, strategy_boost=0.1),
    Player("Achraf Hakimi", penalty_boost=0, strategy_boost=0.1),

    Player("Neymar", penalty_boost=0.7, strategy_boost=0.1),
    Player("Casemiro", penalty_boost=0, strategy_boost=0.1),
    Player("Raphinha", penalty_boost=0, strategy_boost=0.1),

    Player("Ricardo Rodríguez", penalty_boost=0.7, strategy_boost=0.1),
    Player("Shaquiri", penalty_boost=0, strategy_boost=0.1),

    Player("Aboubakar", penalty_boost=0.7, strategy_boost=0),
    Player("Ngamaleu", penalty_boost=0.3, strategy_boost=0.1),
    Player("Ekambi", penalty_boost=0, strategy_boost=0.1),
    Player("Choupo-Moting", penalty_boost=0.3, strategy_boost=0),

    Player("Tadic", penalty_boost=0.7, strategy_boost=0.05),
    Player("Milinkovic-Savic", penalty_boost=0, strategy_boost=0.1),

    Player("Cristiano Ronaldo", penalty_boost=0.7, strategy_boost=0.1),
    Player("Bernardo Silva", penalty_boost=0, strategy_boost=0.1),
    Player("Bruno Fernandes", penalty_boost=0.1, strategy_boost=0.1),

    Player("Thomas Partey", penalty_boost=0.2, strategy_boost=0.1),
    Player("Jordan Ayew", penalty_boost=0.2, strategy_boost=0.1),
    Player("Iñaki Williams", penalty_boost=0.2, strategy_boost=0),

    Player("Luis Suárez", penalty_boost=0.7, strategy_boost=0),
    Player("Cavani", penalty_boost=0.5, strategy_boost=0),
    Player("De Arrascaeta", penalty_boost=0, strategy_boost=0.1),
    Player("Fede Valverde", penalty_boost=0, strategy_boost=0.1),

    Player("Son", penalty_boost=0.7, strategy_boost=0.1),
    Player("Jae Sung Lee", penalty_boost=0, strategy_boost=0.1),

]

my_first_team = [
    Player("Matt Turner", "GK", 11, 7.4, "USA"),

    Player("Blind", "DEF", 20, 7, "HOL"),
    Player("Shaw", "DEF", 21, 7.2, "ING"),
    Player("Otamendi", "DEF", 20, 7.3, "ARG"),

    Player("Caicedo", "MID", 19, 7.1, "ECU"),
    Player("De Bruyne", "MID", 38, 8, "BEL"),
    Player("Bruno Fernandes", "MID", 37, 7.8, "POR"),
    Player("Valverde", "MID", 29, 7.8, "URU"),

    Player("Messi", "ATT", 51, 8.2, "ARG"),
    Player("Griezmann", "ATT", 31, 7.7, "FRA"),
    Player("Di María", "ATT", 22, 7.4, "ARG"),
]


my_team = [
    Player("Matt Turner"),

    Player("Blind"),
    Player("Shaw"),
    Player("Otamendi"),
    Player("Alphonso Davies"),

    Player("Kamada"),
    Player("De Bruyne"),
    Player("Zielinski"),

    Player("Messi"),
    Player("Griezmann"),
    Player("Bale"),
]


jornada_01 = [("Qatar", "Ecuador"), ("England", "Iran"), ("Senegal", "Netherlands"), ("US", "Wales"), ("Argentina", "Saudi Arabia"), ("Denmark", "Tunisia"), ("Mexico", "Poland"), ("France", "Australia"), ("Morocco", "Croatia"), ("Germany", "Japan"), ("Spain", "Costa Rica"), ("Belgium", "Canada"), ("Switzerland", "Cameroon"), ("Uruguay", "South Korea"), ("Portugal", "Ghana"), ("Brazil", "Serbia"), ]
jornada_02 = [("Qatar", "Senegal"), ("England", "US"), ("Ecuador", "Netherlands"), ("Iran", "Wales"), ("Poland", "Saudi Arabia"), ("Australia", "Tunisia"), ("Mexico", "Argentina"), ("France", "Denmark"), ("Canada", "Croatia"), ("Germany", "Spain"), ("Japan", "Costa Rica"), ("Belgium", "Morocco"), ("Serbia", "Cameroon"), ("Ghana", "South Korea"), ("Portugal", "Uruguay"), ("Brazil", "Switzerland"), ]
jornada_03 = [("Qatar", "Netherlands"), ("England", "Wales"), ("Ecuador", "Senegal"), ("Iran", "US"), ("Mexico", "Saudi Arabia"), ("France", "Tunisia"), ("Poland", "Argentina"), ("Australia", "Denmark"), ("Canada", "Morocco"), ("Japan", "Spain"), ("Germany", "Costa Rica"), ("Belgium", "Croatia"), ("Brazil", "Cameroon"), ("Portugal", "South Korea"), ("Ghana", "Uruguay"), ("Serbia", "Switzerland"), ]
jornada_03_players = "OLD_players_before_jornada_03.csv"


def get_current_players(
        no_form=False,
        no_fixtures=False,
        no_home_boost=False,
        no_penalty_boost=False,
        no_manual_boost=True,
        forced_matches=[],
        use_old_players_data=False,
        use_old_teams_data=False,
        ratings_file_name="sofascore_players_ratings",
        penalties_file_name="transfermarket_laliga_penalty_takers"
):
    all_teams, all_players = get_championship_data(forced_matches=forced_matches)

    if use_old_teams_data:
        all_teams = get_old_teams_data(forced_matches)

    if use_old_players_data:
        all_players = get_old_players_data()

    players_ratings_list = get_players_ratings_list(file_name=ratings_file_name)

    partial_players_data = all_players
    if not no_manual_boost:
        partial_players_data = set_manual_boosts(all_players, players_manual_boosts)
    if not no_penalty_boost:
        penalty_takers = get_penalty_takers_dict(file_name=penalties_file_name)
        partial_players_data = set_penalty_takers_boosts(all_players, players_manual_boosts)
    partial_players_data = set_players_elo_dif(partial_players_data, all_teams)
    partial_players_data = set_players_sofascore_rating(partial_players_data, players_ratings_list)
    full_players_data = set_players_value(partial_players_data, no_form, no_fixtures, no_home_boost)

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
    no_manual_boost=True,
    no_form=False,
    no_fixtures=False,
    no_home_boost=False,
    use_old_players_data=False,
    use_old_teams_data=False,
    ratings_file_name="sofascore_laliga_players_ratings"
)

# worthy_players = sorted(current_players, key=lambda x: x.value/x.price, reverse=True)
worthy_players = sorted(current_players, key=lambda x: x.value, reverse=True)

purged_players = purge_everything(worthy_players)

for player in purged_players:
    print(player)
print()

print(len(purged_players))

# mega_purged_players = purge_everything(purged_players, mega_purge=True)


# --------------------------------------------------------------------
# THE METHOD CALL:
# --------------------------------------------------------------------

# best_transfers(my_team, mega_purged_players, 5, verbose=True)

# needed_purge = purged_players[:180]




# best_full_teams(purged_players, possible_formations, 300, super_verbose=False)





# mega_purge = purged_players[:60]
#
# mega_purge = fill_with_team_players(my_team, mega_purge)
#
# best_transfers(my_team, mega_purge, 5, n_results=25, by_n_transfers=False)





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

