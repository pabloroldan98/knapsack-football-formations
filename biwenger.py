# Source: https://stackoverflow.com/questions/59444927/html-request-for-biwenger-in-python

import re
import json
import requests
from pprint import pprint
from unidecode import unidecode

from player import Player, get_position
from eloratings import get_teams_elos
from team import Team


def get_championship_data(forced_matches=[], verbose=True):

    all_data_url = 'https://cf.biwenger.com/api/v2/competitions/la-liga/data?lang=en&score=1&callback=jsonp_xxx'

    response = requests.get(all_data_url)
    data = json.loads(re.findall(r'jsonp_xxx\((.*)\)', response.text)[0])

    if verbose:
        print("Loading teams data...")
        print()
    championship_teams = get_teams_championship_data(data, forced_matches=forced_matches)
    if verbose:
        print("Loading players data...")
        print()
    championship_players = get_players_championship_data(data)

    sorted_championship_teams = sorted(championship_teams, key=lambda x: x.elo, reverse=True)
    sorted_championship_players = sorted(championship_players, key=lambda x: x.price, reverse=True)

    return sorted_championship_teams, sorted_championship_players


def get_teams_championship_data(data, forced_matches=[]):
    championship_teams = data['data']['teams']
    teams_elos_dict, short_teams_elos_dict = get_teams_elos()
    championship_teams_db = create_teams_list(championship_teams, teams_elos_dict, short_teams_elos_dict, forced_matches=forced_matches)

    return championship_teams_db


def create_teams_list(championship_teams, teams_elos_dict, short_teams_elos_dict, forced_matches=[]):
    teams_list = []
    if not forced_matches:
        for worldcup_team_id in championship_teams:
            worldcup_team = championship_teams[str(worldcup_team_id)]

            team_name = worldcup_team["name"]
            team_name_next_opponent = None
            if worldcup_team["nextGames"]:
                team_next_opponent = get_next_opponent(int(worldcup_team_id),
                                                       championship_teams)
                team_name_next_opponent = team_next_opponent["name"]

            team_elo = get_team_elo(team_name, teams_elos_dict, short_teams_elos_dict)

            new_team = Team(
                team_name,
                team_name_next_opponent,
                team_elo
            )
            teams_list.append(new_team)

    else:
        for new_match in forced_matches:
            home_team = new_match[0]
            away_team = new_match[1]

            team_elo = get_team_elo(home_team, teams_elos_dict, short_teams_elos_dict)
            new_team = Team(
                home_team,
                away_team,
                team_elo
            )
            teams_list.append(new_team)

            team_elo = get_team_elo(away_team, teams_elos_dict, short_teams_elos_dict)
            new_team = Team(
                away_team,
                home_team,
                team_elo
            )
            teams_list.append(new_team)

    return teams_list


def get_team_elo(team_name, teams_elos_dict, short_teams_elos_dict):
    if team_name in teams_elos_dict:
        team_elo = teams_elos_dict[team_name]
    elif team_name in short_teams_elos_dict:
        team_elo = short_teams_elos_dict[team_name]
    else:
        team_elo = 0
    return team_elo


def get_next_opponent(team_id, teams):
    my_team = teams[str(team_id)]

    next_team_home_id = int(my_team["nextGames"][0]["home"]["id"])
    next_team_away_id = int(my_team["nextGames"][0]["away"]["id"])

    if int(team_id) != next_team_home_id:
        next_team = teams[str(next_team_home_id)]
    else:
        next_team = teams[str(next_team_away_id)]

    return next_team


def get_players_championship_data(data):
    championship_teams = data['data']['teams']
    championship_players = data['data']['players']
    championship_players_db = create_players_list(championship_teams, championship_players)
    return championship_players_db


def create_players_list(championship_teams, championship_players):
    players_list = []
    for worldcup_player_id in championship_players:
        worldcup_player = championship_players[str(worldcup_player_id)]

        # pprint(worldcup_player)
        player_name = worldcup_player["name"]
        player_group = worldcup_player["position"]
        player_price = int(worldcup_player["fantasyPrice"] / 1000000)
        player_status = worldcup_player["status"]
        player_standard_price = float(worldcup_player["price"])
        player_price_trend = float(worldcup_player["priceIncrement"])
        player_fitness = worldcup_player["fitness"]

        player_team_id = str(worldcup_player["teamID"])
        if player_team_id == "None":
            player_team = "None"
        else:
            player_team = championship_teams[player_team_id]["name"]

        new_player = Player(
            player_name,
            get_position(player_group),
            player_price,
            0,
            player_team,
            player_status,
            player_standard_price,
            player_price_trend,
            player_fitness
        )
        players_list.append(new_player)
    return players_list


# all_teams, all_players = get_championship_data()
#
# for t in all_teams:
#     print(t)
#
# for p in all_players:
#     print(p)


# user_data_url = 'https://biwenger.as.com/api/v2/user/16728?fields=*,account(id),players(id,owner),lineups(round,points,count,position),league(id,name,competition,mode,scoreID),market,seasons,offers,lastPositions'
# all_data_url = 'https://cf.biwenger.com/api/v2/competitions/world-cup/data?lang=en&score=1&callback=jsonp_xxx' # <--- check @αԋɱҽԃ αмєяιcαη answer, it's possible to do it without callback= parameter
#
# response = requests.get(all_data_url)
# data = json.loads( re.findall(r'jsonp_xxx\((.*)\)', response.text)[0] )

# user_data = requests.get(user_data_url).json()

# pprint(user_data)  # <-- uncomment this to see user data
# pprint(data)       # <-- uncomment this to see data about all players
#
# pprint(data["data"]["players"])
#
# print(type(data['data']['players']["29346"]["fitness"][0]))
# min=10000
# max=0
# for player_id in data['data']['players']:
#     player = data['data']['players'][str(player_id)]
#     player_standard_price = player["price"]
#     player_price_trend = player["priceIncrement"]
#     player_coef = (player_standard_price+player_price_trend) / player_standard_price
#     if player_coef < min:
#         min=player_coef
#     if player_coef > max:
#         max=player_coef
#     print(player_coef)
#     pprint(data['data']['players'][str(player_id)])
#     print('-' * 80)
#
# print(min)
# print(max)

# for teams in data['data']['teams']:
#     pprint(data['data']['teams'][str(teams)])
#     print('-' * 80)
