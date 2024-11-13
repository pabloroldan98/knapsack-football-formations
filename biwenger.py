# Source: https://stackoverflow.com/questions/59444927/html-request-for-biwenger-in-python

import re
import json
import requests
from pprint import pprint

from player import Player, get_position
from elo_ratings import get_teams_elos
from team import Team

from useful_functions import find_similar_string

def get_championship_data(forced_matches=[], is_country=False, host_team=None, use_comunio_price=False, verbose=True):

    all_data_url = 'https://cf.biwenger.com/api/v2/competitions/la-liga/data?lang=en&score=1&callback=jsonp_xxx'
    # all_data_url = 'https://cf.biwenger.com/api/v2/competitions/euro/data?lang=en&score=1&callback=jsonp_xxx'
    # all_data_url = 'https://cf.biwenger.com/api/v2/competitions/copa-america/data?lang=en&callback=jsonp_xxx'

    response = requests.get(all_data_url)
    data = json.loads(re.findall(r'jsonp_xxx\((.*)\)', response.text)[0])

    if verbose:
        print("Loading teams data...")
        print()
    championship_teams = get_teams_championship_data(data, is_country=is_country, host_team=host_team, forced_matches=forced_matches)
    if verbose:
        print("Loading players data...")
        print()
    championship_players = get_players_championship_data(data, use_comunio_price=use_comunio_price)

    sorted_championship_teams = sorted(championship_teams, key=lambda x: x.elo, reverse=True)
    sorted_championship_players = sorted(championship_players, key=lambda x: x.price, reverse=True)

    return sorted_championship_teams, sorted_championship_players


def get_teams_championship_data(data, is_country=False, host_team=None, forced_matches=[]):
    championship_teams = data['data']['teams']
    championship_players = data['data']['players']
    teams_elos_dict = get_teams_elos(is_country=is_country)
    championship_teams_db = create_teams_list(
        championship_teams,
        championship_players,
        teams_elos_dict,
        host_team=host_team,
        forced_matches=forced_matches
    )

    return championship_teams_db


def create_teams_list(championship_teams, championship_players, teams_elos_dict, host_team=None, forced_matches=[]):
    teams_list = []
    if not forced_matches:
        for championship_team_id in championship_teams:
            num_ok = 0
            num_injured = 0
            num_doubt = 0
            num_sanctioned = 0
            num_warned = 0
            for championship_player_id in championship_players:
                championship_player = championship_players[str(championship_player_id)]
                if str(championship_player["teamID"]) == str(championship_team_id):
                    player_status = championship_player["status"]
                    if player_status == "ok":
                        num_ok += 1
                    if player_status == "injured":
                        num_injured += 1
                    if player_status == "doubt":
                        num_doubt += 1
                    if player_status == "sanctioned":
                        num_sanctioned += 1
                    if player_status == "warned":
                        num_warned += 1

            championship_team = championship_teams[str(championship_team_id)]

            team_name = championship_team["name"]
            team_name_next_opponent = None
            if championship_team["nextGames"]:
                team_next_opponent, is_team_home = get_next_opponent(
                    int(championship_team_id),
                    championship_teams
                )
                team_name_next_opponent = team_next_opponent["name"]

            team_elo = get_team_elo(team_name, teams_elos_dict)

            if host_team:
                is_team_home = True if host_team == team_name else False

            new_team = Team(
                team_name,
                team_name_next_opponent,
                team_elo,
                is_team_home,
                num_ok,
                num_injured,
                num_doubt,
                num_sanctioned,
                num_warned
            )
            teams_list.append(new_team)

    else:
        for new_match in forced_matches:
            home_team = new_match[0]
            away_team = new_match[1]

            team_elo = get_team_elo(home_team, teams_elos_dict)
            is_team_home = True
            new_team = Team(
                home_team,
                away_team,
                team_elo,
                is_team_home
            )
            teams_list.append(new_team)

            team_elo = get_team_elo(away_team, teams_elos_dict)
            is_team_home = False
            new_team = Team(
                away_team,
                home_team,
                team_elo,
                is_team_home
            )
            teams_list.append(new_team)

    return teams_list


def get_team_elo(team_name, teams_elos_dict):
    teams_list = list(teams_elos_dict.keys())
    if team_name == "Athletic":
        closest_team_name = "Bilbao"
    elif team_name == "Czech Republic":
        closest_team_name = "Czechia"
    elif team_name == "Türkiye":
        closest_team_name = "Turkey"
    else:
        closest_team_name = find_similar_string(team_name, teams_list) #, 0.7)
    if closest_team_name in teams_elos_dict:
        team_elo = teams_elos_dict[closest_team_name]
    else:
        team_elo = 0
    return team_elo


def get_next_opponent(team_id, teams):
    my_team = teams[str(team_id)]

    next_team_home_id = int(my_team["nextGames"][0]["home"]["id"])
    next_team_away_id = int(my_team["nextGames"][0]["away"]["id"])

    if int(team_id) != next_team_home_id:
        next_team = teams[str(next_team_home_id)]
        is_my_team_home = False
    else:
        next_team = teams[str(next_team_away_id)]
        is_my_team_home = True

    return next_team, is_my_team_home


def get_players_championship_data(data, use_comunio_price=False):
    championship_teams = data['data']['teams']
    championship_players = data['data']['players']
    championship_players_db = create_players_list(championship_players, championship_teams, use_comunio_price=use_comunio_price)
    return championship_players_db


def create_players_list(championship_players, championship_teams, use_comunio_price=False):
    players_list = []
    for championship_player_id in championship_players:
        championship_player = championship_players[str(championship_player_id)]

        # pprint(championship_player)
        player_name = championship_player["name"]
        player_group = championship_player["position"]
        if use_comunio_price:
            player_price = int(championship_player["price"] / 100000)
        else:
            player_price = int(championship_player["fantasyPrice"] / 100000)
        player_status = championship_player["status"]
        player_standard_price = float(championship_player["price"])
        player_fantasy_price = float(championship_player["fantasyPrice"])
        player_price_trend = float(championship_player["priceIncrement"])
        player_fitness = championship_player["fitness"]

        player_team_id = str(championship_player["teamID"])
        if player_team_id == "None":
            player_team = "None"
        else:
            player_team = championship_teams[player_team_id]["name"]

        if player_group != 5:
            new_player = Player(
                name=player_name,
                position=get_position(player_group),
                price=player_price,
                value=0,
                team=player_team,
                status=player_status,
                standard_price=player_standard_price,
                fantasy_price=player_fantasy_price,
                price_trend=player_price_trend,
                fitness=player_fitness
            )
            players_list.append(new_player)
    return players_list


# all_teams, all_players = get_championship_data(is_country=False)
#
# for t in all_teams:
#     print(t)
#
# for p in all_players:
#     print(p)


# user_data_url = 'https://biwenger.as.com/api/v2/user/9268844?fields=*,account(id),players(id,owner),lineups(round,points,count,position),league(id,name,competition,mode,scoreID),market,seasons,offers,lastPositions'
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
