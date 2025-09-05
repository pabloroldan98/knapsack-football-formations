# Source: https://stackoverflow.com/questions/59444927/html-request-for-biwenger-in-python
import os
import re
import json
import requests
from pprint import pprint
import tls_requests
import urllib3
from urllib3.exceptions import ReadTimeoutError
from urllib.parse import urlencode

from player import Player, get_position, get_status
from elo_ratings import get_teams_elos_dict
from team import Team
from useful_functions import find_similar_string, read_dict_data, overwrite_dict_data

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))  # This is your Project Root


def competition_from_filename(file_name: str) -> str:
    """
    Infer Biwenger competition slug from the filename.
    Defaults to 'la-liga' if nothing matches.
    """
    s = re.sub(r'[^a-z0-9]+', '-', file_name.lower())  # normalize to dashed tokens

    mapping = {
        ("mundialito", "club-world-cup", "clubworldcup", "mundial-clubes", "mundialclubes", ): "club-world-cup",
        ("champions", "championsleague", "champions-league"): "champions-league",
        ('europaleague', 'europa-league', ): "europa-league",
        ('conference', 'conferenceleague', 'conference-league', ): "conference-league",
        ("eurocopa", "euro", "europa", "europeo", ): "euro",
        ("copaamerica", "copa-america", ): "copa-america",
        ("mundial", "worldcup", "world-cup", ): "world-cup",
        ("laliga", "la-liga", ): "la-liga",
        ('premier', 'premier-league', 'premierleague', ): "premier-league",
        ('seriea', 'serie-a', ): "serie-a",
        ('bundesliga', 'bundes-liga', 'bundes', ): "bundesliga",
        ('ligueone', 'ligue-one', 'ligue1', 'ligue-1', 'ligue', ): "ligue-1",
        ('segunda', 'segundadivision', 'segunda-division', 'laliga2', 'la-liga2', 'la-liga-2', 'hypermotion', 'la-liga-hypermotion', 'laligahypermotion', ): "segunda-division",
    }
    for keys, slug in mapping.items():
        for k in sorted(keys, key=len, reverse=True):  # longest first
            if k in s:
                return slug
    return "la-liga"


def get_biwenger_data_dict(
        write_file=False,
        file_name="biwenger_laliga_data",
        force_scrape=True
):
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    data = None
    if force_scrape:
        try:
            slug = competition_from_filename(file_name)
            params = {"lang": "en", "callback": "jsonp_xxx"}  # <-- no 'score' here
            all_data_url = f"https://cf.biwenger.com/api/v2/competitions/{slug}/data?{urlencode(params)}"
            # # all_data_url = 'https://cf.biwenger.com/api/v2/competitions/club-world-cup/data?lang=en&score=1&callback=jsonp_xxx'
            # all_data_url = 'https://cf.biwenger.com/api/v2/competitions/la-liga/data?lang=en&score=1&callback=jsonp_xxx'
            # # all_data_url = 'https://cf.biwenger.com/api/v2/competitions/euro/data?lang=en&score=1&callback=jsonp_xxx'
            # # all_data_url = 'https://cf.biwenger.com/api/v2/competitions/copa-america/data?lang=en&callback=jsonp_xxx'

            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            # response = requests.get(all_data_url, headers=headers, verify=False)
            response = tls_requests.get(all_data_url, headers=headers, verify=False)
            data = json.loads(re.findall(r'jsonp_xxx\((.*)\)', response.text)[0])
        except:
            pass
    if not data: # if force_scrape failed or not force_scrape
        data = read_dict_data(file_name)
        if data:
            return data

    if write_file:
        # write_dict_data(data, file_name)
        overwrite_dict_data(data, file_name, ignore_old_data=True)

    return data


def get_championship_data(
        forced_matches=[],
        is_country=False,
        extra_teams=False,
        host_team=None,
        use_comunio_price=False,
        biwenger_file_name="biwenger_laliga_data",
        elo_ratings_file_name="elo_ratings_laliga_data",
        verbose=True
):
    print()
    data = get_biwenger_data_dict(file_name=biwenger_file_name)

    print()
    print()
    if verbose:
        print("Loading teams data...")
        print()
    championship_teams = get_teams_championship_data(data, is_country=is_country, extra_teams=extra_teams, host_team=host_team, forced_matches=forced_matches, file_name=elo_ratings_file_name)
    if verbose:
        print("Loading players data...")
        print()
    championship_players = get_players_championship_data(data, use_comunio_price=use_comunio_price)

    sorted_championship_teams = sorted(championship_teams, key=lambda x: x.elo, reverse=True)
    sorted_championship_players = sorted(championship_players, key=lambda x: x.price, reverse=True)

    return sorted_championship_teams, sorted_championship_players


def country_from_filename(file_name: str):
    s = re.sub(r'[^a-z0-9]+', '-', file_name.lower())  # normalize to dashed tokens

    mapping = {
        ("mundialito", "club-world-cup", "clubworldcup", "mundial-clubes", "mundialclubes", ): None,
        ("champions", "championsleague", "champions-league"): None,
        ('europaleague', 'europa-league', ): None,
        ('conference', 'conferenceleague', 'conference-league', ): None,
        ("eurocopa", "euro", "europa", "europeo", ): None,
        ("copaamerica", "copa-america", ): None,
        ("mundial", "worldcup", "world-cup", ): None,
        ("laliga", "la-liga", ): "ESP",
        ('premier', 'premier-league', 'premierleague', ): "ENG",
        ('seriea', 'serie-a', ): "ITA",
        ('bundesliga', 'bundes-liga', 'bundes', ): "GER",
        ('ligueone', 'ligue-one', 'ligue1', 'ligue-1', 'ligue', ): "FRA",
        ("segunda", "segundadivision", "segunda-division", "laliga2", "la-liga-2", "la-liga-hypermotion", "hypermotion", "laligahypermotion", ): "ESP",
    }
    for keys, slug in mapping.items():
        for k in sorted(keys, key=len, reverse=True):  # longest first
            if k in s:
                return slug
    return None


def get_teams_championship_data(data, is_country=False, extra_teams=False, host_team=None, forced_matches=[], file_name="elo_ratings_laliga_data"):
    championship_teams = data['data']['teams']
    championship_players = data['data']['players']

    country = country_from_filename(file_name)
    teams_elos_dict = get_teams_elos_dict(is_country=is_country, country=country, extra_teams=extra_teams, file_name=file_name)
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
            team_status_num = {
                "ok": 0,
                "injured": 0,
                "doubt": 0,
                "sanctioned": 0,
                "warned": 0,
            }
            for championship_player_id in championship_players:
                championship_player = championship_players[str(championship_player_id)]
                if str(championship_player["teamID"]) == str(championship_team_id):
                    player_status = championship_player["status"]
                    if player_status in team_status_num:
                        team_status_num[player_status] += 1

            championship_team = championship_teams[str(championship_team_id)]

            team_name = championship_team["name"]
            team_name_next_opponent = None
            is_team_home = False
            if championship_team["nextGames"]:
                team_next_opponent, is_team_home = get_next_opponent(
                    int(championship_team_id),
                    championship_teams
                )
                team_name_next_opponent = team_next_opponent["name"]

            team_elo = get_team_elo(team_name, teams_elos_dict)

            if host_team:
                if isinstance(host_team, str):
                    is_team_home = True if team_name == host_team else False
                elif isinstance(host_team, list):
                    is_team_home = True if team_name in host_team else False
                else:
                    is_team_home = False

            team_img_link = f"https://cdn.biwenger.com/i/t/{championship_team_id}.png"

            new_team = Team(
                name=team_name,
                next_opponent=team_name_next_opponent,
                elo=team_elo,
                is_home=is_team_home,
                num_ok=team_status_num["ok"],
                num_injured=team_status_num["injured"],
                num_doubt=team_status_num["doubt"],
                num_sanctioned=team_status_num["sanctioned"],
                num_warned=team_status_num["warned"],
                img_link=team_img_link
            )
            teams_list.append(new_team)

    else:
        teams_status_num_dict = {}
        for championship_team_id in championship_teams:
            team_name = championship_teams[str(championship_team_id)]["name"]

            team_status_num = {
                "ok": 0,
                "injured": 0,
                "doubt": 0,
                "sanctioned": 0,
                "warned": 0,
            }
            for championship_player_id in championship_players:
                championship_player = championship_players[str(championship_player_id)]
                if str(championship_player["teamID"]) == str(championship_team_id):
                    player_status = championship_player["status"]
                    if player_status in team_status_num:
                        team_status_num[player_status] += 1

            teams_status_num_dict[team_name] = team_status_num

        for new_match in forced_matches:
            home_team = new_match[0]
            away_team = new_match[1]

            team_elo = get_team_elo(home_team, teams_elos_dict)
            is_team_home = True
            if host_team:
                if isinstance(host_team, str):
                    is_team_home = True if team_name == host_team else False
                elif isinstance(host_team, list):
                    is_team_home = True if team_name in host_team else False
                else:
                    is_team_home = False
            try:
                team_status_num = teams_status_num_dict[away_team]
            except:
                team_status_num = {
                    "ok": 0,
                    "injured": 0,
                    "doubt": 0,
                    "sanctioned": 0,
                    "warned": 0,
                }
            new_team = Team(
                name=home_team,
                next_opponent=away_team,
                elo=team_elo,
                is_home=is_team_home,
                num_ok=team_status_num["ok"],
                num_injured=team_status_num["injured"],
                num_doubt=team_status_num["doubt"],
                num_sanctioned=team_status_num["sanctioned"],
                num_warned=team_status_num["warned"]
            )
            teams_list.append(new_team)

            team_elo = get_team_elo(away_team, teams_elos_dict)
            is_team_home = False
            if host_team:
                if isinstance(host_team, str):
                    is_team_home = True if team_name == host_team else False
                elif isinstance(host_team, list):
                    is_team_home = True if team_name in host_team else False
                else:
                    is_team_home = False
            try:
                team_status_num = teams_status_num_dict[away_team]
            except:
                team_status_num = {
                    "ok": 0,
                    "injured": 0,
                    "doubt": 0,
                    "sanctioned": 0,
                    "warned": 0,
                }
            new_team = Team(
                name=away_team,
                next_opponent=home_team,
                elo=team_elo,
                is_home=is_team_home,
                num_ok=team_status_num["ok"],
                num_injured=team_status_num["injured"],
                num_doubt=team_status_num["doubt"],
                num_sanctioned=team_status_num["sanctioned"],
                num_warned=team_status_num["warned"]
            )
            teams_list.append(new_team)

    return teams_list


def get_team_elo(team_name, teams_elos_dict):
    teams_list = list(teams_elos_dict.keys())
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
        player_position_group = championship_player["position"]
        if use_comunio_price:
            player_price = int(round(championship_player["price"] / 100_000))
        else:
            # player_price = int(round(championship_player["fantasyPrice"] / 100_000))
            player_price = int(round(championship_player["fantasyPrice"] / 1_000_000))
        player_status_group = championship_player["status"]
        player_standard_price = float(championship_player["price"])
        player_fantasy_price = float(championship_player["fantasyPrice"])
        player_price_trend = float(championship_player["priceIncrement"])
        player_fitness = championship_player.get("fitness", [])
        player_img_link = f"https://cdn.biwenger.com/i/p/{championship_player_id}.png"

        player_team_id = str(championship_player["teamID"])
        if player_team_id == "None":
            player_team = "None"
        else:
            player_team = championship_teams[player_team_id]["name"]

        if player_position_group != 5:
            new_player = Player(
                name=player_name,
                position=get_position(player_position_group),
                price=player_price,
                value=0,
                team=player_team,
                status=get_status(player_status_group),
                standard_price=player_standard_price,
                fantasy_price=player_fantasy_price,
                price_trend=player_price_trend,
                form=1+player_price_trend/10_000_000,
                fitness=player_fitness,
                img_link=player_img_link
            )
            players_list.append(new_player)
    return players_list


def get_next_jornada():
    all_teams, _ = get_championship_data(verbose=False)
    jornadas_dict = read_dict_data("forced_matches_laliga_2025_26")

    next_jornadas = []

    # Loop over teams
    for team in all_teams:
        # Loop over jornadas sorted by number
        for jornada_name, matches in sorted(jornadas_dict.items(), key=lambda x: int(x[0].split('_')[1])):

            # Check each match
            for match in matches:
                home, away = match
                if team.is_home and team.next_opponent == away:
                    next_jornadas.append(jornada_name)
                    break
                elif not team.is_home and team.next_opponent == home:
                    next_jornadas.append(jornada_name)
                    break
            else:
                continue
            break

    # Return the latest jornada key among all teams
    return max(next_jornadas, key=lambda x: int(x.split('_')[1])) if next_jornadas else None


# all_teams, all_players = get_championship_data(
#     is_country=False,
#     extra_teams=False,
#     use_comunio_price=False,
#     biwenger_file_name="biwenger_laliga_data",
#     elo_ratings_file_name="elo_ratings_laliga_data",
# )
#
# for t in all_teams:
#     print(t)
# print("---------------------------------------------")
# for p in all_players:
#     print(p)



# all_teams, all_players = get_championship_data(
#     is_country=False,
#     extra_teams=True,
#     host_team=["Inter Miami", "Seattle", ],
#     use_comunio_price=False,
#     biwenger_file_name="biwenger_mundialito_data",
#     elo_ratings_file_name="elo_ratings_mundialito_data",
# )
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
