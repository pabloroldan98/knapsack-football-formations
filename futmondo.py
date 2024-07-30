import requests
from bs4 import BeautifulSoup
from pprint import pprint
import os
import ast

from useful_functions import write_dict_to_csv, read_dict_from_csv


class FutmondoWebScraper:
    def __init__(self):
        self.base_url = "https://www.futmondo.com"
        self.teams = {}

    def get_teams(self, url):
        response = requests.get(url)
        soup = BeautifulSoup(response.content, 'html.parser')

        team_elements = soup.select('.teamCrests.blackBg .teamLink a')

        for element in team_elements:
            team_name = element.img['title']
            team_link = self.base_url + element['href']
            self.teams[team_name] = {"link": team_link}

    def get_players(self):
        for team_name, team_data in self.teams.items():
            url = team_data['link']
            response = requests.get(url)
            soup = BeautifulSoup(response.content, 'html.parser')

            player_elements = soup.select('#staticPlayers ul li')
            players = {}

            for element in player_elements:
                player_name = element.select_one('a.name').text.strip().split('\n')[0]
                player_position = get_position(element.get('data-role'))
                players[player_name] = player_position

            self.teams[team_name]['players'] = players

    def run(self):
        url = "https://www.futmondo.com/team?team=50819964ffd960540d0014ed"
        self.get_teams(url)
        self.get_players()

        return self.teams


def get_position(futmondo_position):
    if futmondo_position == "portero":
        position = "GK"
    elif futmondo_position == "defensa":
        position = "DEF"
    elif futmondo_position == "centrocampista":
        position = "MID"
    else:
        position = "ATT"
    return position


def get_players_positions_dict(write_file=True, file_name="futmondo_la_liga_players_positions"):
    if os.path.isfile('./csv_files/' + file_name + '.csv'):
        data = read_dict_from_csv(file_name)
        result = {key: ast.literal_eval(value) for key, value in data.items()}
        return result

    scraper = FutmondoWebScraper()
    result = scraper.run()

    team_players_positions_dict = {team_name: team_dict["players"] for team_name, team_dict in result.items()}

    if write_file:
        write_dict_to_csv(team_players_positions_dict, file_name)

    return team_players_positions_dict


# players_positions_dict = get_players_positions_dict("futmondo_la_liga_players_positions)
#
# # Print the result in a readable way
# pprint(players_positions_dict)
