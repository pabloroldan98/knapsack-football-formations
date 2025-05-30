import requests
import tls_requests
from bs4 import BeautifulSoup
from pprint import pprint
import os
import ast

from useful_functions import write_dict_data, read_dict_data, is_valid_league_dict, overwrite_dict_data

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))  # This is your Project Root


class FutmondoWebScraper:
    def __init__(self):
        self.base_url = "https://www.futmondo.com"
        self.teams = {}

    def get_teams(self, url):
        # response = requests.get(url)
        response = tls_requests.get(url)
        soup = BeautifulSoup(response.content, 'html.parser')

        team_elements = soup.select('.teamCrests.blackBg .teamLink a')

        for element in team_elements:
            team_name = element.img['title']
            team_link = self.base_url + element['href']
            self.teams[team_name] = {"link": team_link}

    def get_players(self):
        for team_name, team_data in self.teams.items():
            url = team_data['link']
            # response = requests.get(url)
            response = tls_requests.get(url)
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


def get_players_positions_dict(
        write_file=True,
        file_name="futmondo_laliga_players_positions",
        force_scrape=False
):
    if not force_scrape:
        data = read_dict_data(file_name)
        if data:
            return data

    scraper = FutmondoWebScraper()
    result = scraper.run()

    team_players_positions_dict = {team_name: team_dict["players"] for team_name, team_dict in result.items()}

    if write_file:
        # write_dict_data(team_players_positions_dict, file_name)
        overwrite_dict_data(team_players_positions_dict, file_name)

    return team_players_positions_dict


# players_positions_dict = get_players_positions_dict(file_name="futmondo_laliga_players_positions", force_scrape=True)
#
# # Print the result in a readable way
# pprint(players_positions_dict)
