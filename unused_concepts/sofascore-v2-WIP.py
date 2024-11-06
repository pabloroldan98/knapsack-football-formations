import requests
from bs4 import BeautifulSoup
import cloudscraper
import csv
import os

from player import Player
from useful_functions import write_dict_to_csv, read_dict_from_csv

def get_team_links_from_league(league_url):
    response = requests.get(league_url)
    soup = BeautifulSoup(response.text, 'html.parser')

    # Find team links based on the HTML structure of the page
    # You would need to adjust the selectors below according to the actual structure of the site
    teams = soup.select('a.team-link')  # Use the correct CSS selector to find team links

    team_data = {}
    for i, team in enumerate(teams):
        link = team['href']
        name = team.get_text()
        team_data[str(i + 1)] = [name, link]
    return team_data

def get_players_data(write_file=True, file_name="sofascore_players_ratings", team_links=None):
    if os.path.isfile('./' + file_name + '.csv'):
        return read_dict_from_csv(file_name)

    team_players_paths = dict()
    for key, value in team_links.items():
        player_paths_list = []
        print('Extracting %s player links...' % value[0])
        response = requests.get(value[1])
        soup = BeautifulSoup(response.text, 'html.parser')

        # Find player links
        players = soup.select('a.player-link')  # Use the correct CSS selector to find player links

        for p in players:
            player_paths_list.append(p['href'])
        player_paths_list = sorted(list(set(player_paths_list)))
        team_players_paths[value[0]] = player_paths_list

    teams_with_players_ratings = dict()
    j = 0
    for team_name, player_paths in team_players_paths.items():
        players_ratings = {}
        for p in player_paths:
            player_page = requests.get(p)
            player_soup = BeautifulSoup(player_page.text, 'html.parser')

            # Parse player rating and name
            average_rating = float(player_soup.select_one('span.rating').text)  # Update selector
            player_name = player_soup.select_one('h2.player-name').text  # Update selector

            print('Extracting player data from %s ...' % player_name)
            players_ratings[player_name] = average_rating

        teams_with_players_ratings[team_name] = players_ratings
        write_dict_to_csv(teams_with_players_ratings, file_name + "_" + str(j))
        j += 1

    if write_file:
        write_dict_to_csv(teams_with_players_ratings, file_name)

    return teams_with_players_ratings

# Example usage:
# league_url = "https://www.sofascore.com/tournament/football/spain/laliga/8"
# team_links = get_team_links_from_league(league_url)
# pprint(team_links)
# result = get_players_data(file_name="sofascore_la_liga_players_ratings", team_links=team_links)
# for team, players in result.items():
#     for player, rating in players.items():
#         print(f"{player} from {team} has a rating of {rating}")


# session = requests.Session()
# headers = {
#     'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
# }
# session.headers.update(headers)
# # Replace this URL with the actual league URL you're scraping
# league_url = "https://www.sofascore.com/player/vinicius-junior/868812"
# try:
#     response = session.get(league_url)
#     response.raise_for_status()  # Will raise an HTTPError if the HTTP request returned an unsuccessful status code
#
#     # Only process the page if the content was fetched successfully
#     if response.status_code == 200:
#         soup = BeautifulSoup(response.text, 'html.parser')
#         print(soup)
#         # Find all <a> tags
#         all_links = soup.find_all('a')
#
#         # Print href and class of all <a> tags to find potential team links
#         for link in all_links:
#             href = link.get('href')
#             classes = link.get('class')
#             # Only print <a> tags that have a class attribute to narrow down the output
#             if classes:
#                 print(f"href: {href}, classes: {classes}")
# except requests.exceptions.HTTPError as err:
#     print(err)

# NOTAS:
# Esto no vale, pero hay una api de sofascore que saca:
# - La Liga: https://api.sofascore.app/api/v1/unique-tournament/8
# - Real Madrid: https://api.sofascore.app/api/v1/team/2829 y sus jugadores: https://api.sofascore.app/api/v1/team/2829/players
# - Vinicius: https://api.sofascore.app/api/v1/player/868812


# scraper = cloudscraper.create_scraper()  # returns a CloudScraper instance
# # Or: scraper = cloudscraper.CloudScraper()  # CloudScraper inherits from requests.Session
# print(scraper.get("https://www.sofascore.com/player/vinicius-junior/868812").text)

import json

# Case 1: players_ratings is a string that contains a JSON object
players_ratings = '{"player1": 1000, "player2": 958, "player3": 1200}'
players_ratings_dict = json.loads(players_ratings)
print(players_ratings_dict)  # Output will be the original JSON object as a Python dictionary
variable_type = type(players_ratings_dict)
print(variable_type)

# Case 2: players_ratings is a dictionary
players_ratings = {'player1': 1000, 'player2': 958, 'player3': 1200}
players_ratings_dict = json.loads(players_ratings)
print(players_ratings_dict)  # Output will be the same dictionary as players_ratings
variable_type = type(players_ratings_dict)
print(variable_type)
