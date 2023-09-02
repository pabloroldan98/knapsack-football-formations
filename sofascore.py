# Source: https://github.com/Urbistondo/sofa-score-scraper/blob/master/player_scraper.py

import os

from selenium.common import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium import webdriver
from pprint import pprint
import ast

from player import Player
from useful_functions import write_dict_to_csv, read_dict_from_csv


def get_players_ratings_list(write_file=True, file_name="sofascore_players_ratings", team_links=None):
    players_data = get_players_data(write_file, file_name, team_links)
    players_data_dict = {key: ast.literal_eval(value) for key, value in players_data.items()}
    players_ratings_list = []
    for player_name, player_data in players_data_dict.items():
        new_player = Player(player_name, sofascore_rating=player_data["rating"], team=player_data["team"])
        players_ratings_list.append(new_player)
    return players_ratings_list


def get_team_links_from_league(league_url, driver):
    driver.get(league_url)
    # Base XPath for team links
    teams_base_xpath = "//*[@id='__next']/main/div/div[3]/div/div/div[1]/div[2]/div/div[1]/div/div[2]/div/a"
    # Specific XPath for team names based on the base XPath
    team_name_xpath = teams_base_xpath + "/div/div[3]/div/span"
    team_links = driver.find_elements(By.XPATH, teams_base_xpath)
    team_names = driver.find_elements(By.XPATH, team_name_xpath)
    # Create a dictionary to hold the team names and their links
    team_data = {}
    for i, (team_link_element, team_name_element) in enumerate(zip(team_links, team_names)):
        link = team_link_element.get_attribute('href')
        name = team_name_element.text
        team_data[str(i+1)] = [name, link]
    return team_data


def get_players_data(write_file=True, file_name="sofascore_players_ratings", team_links=None):
    if os.path.isfile('./' + file_name + '.csv'):
        return read_dict_from_csv(file_name)

    driver = webdriver.Chrome(keep_alive=False)
    if not team_links:
        extra_driver = webdriver.Chrome(keep_alive=True)
        team_links = get_team_links_from_league(
            "https://www.sofascore.com/tournament/football/spain/laliga/8#52376",
            extra_driver
        )
        extra_driver.quit()
    team_players_paths = dict()
    for key, value in team_links.items():
        player_paths_list = []
        print('Extracting %s player links...' % value[0])
        driver.get(value[1])
        players = driver.find_elements(By.XPATH, "//*[contains(@class, 'sc-fqkvVR gwUJxr')]/a")
        for p in players:
            player_paths_list.append(p.get_attribute('href'))
        team_players_paths[value[0]] = player_paths_list

    players_with_ratings = dict()
    save_counter = -1
    j = 0
    for team_name, player_paths in team_players_paths.items():
        for p in player_paths:
            driver.get(p)
            average_rating = float(6.0)
            try:
                average_rating = float(driver.find_element(By.XPATH, "//span[@class='sc-jEACwC cmGEOd']").get_attribute("textContent"))
            except: # NoSuchElementException:  # Spelling error making this code not work as expected
                pass
            try:
                player_name = driver.find_element(By.XPATH, "//h2[@class='sc-jEACwC iLVhST']").get_attribute("textContent")
                print('Extracting player data from %s ...' % player_name)
                player_data = {
                    "rating": average_rating,
                    "team": team_name
                }
                players_with_ratings[player_name] = player_data
            except NoSuchElementException:  # Spelling error making this code not work as expected
                pass
            save_counter = save_counter + 1
            if save_counter == 26:
                write_dict_to_csv(players_with_ratings, file_name + "_" + str(j))
                save_counter = 0
                j = j + 1

    driver.quit()

    if write_file:
        write_dict_to_csv(players_with_ratings, file_name)

    return players_with_ratings


# driver = webdriver.Chrome(keep_alive=True)
# team_links = get_team_links_from_league("https://www.sofascore.com/tournament/football/spain/laliga/8#52376", driver)
# driver.quit()
# pprint(team_links)
# result = get_players_ratings_list(file_name="sofascore_la_liga_players_data")#, team_links=team_links)
# for p in result:
#     print(p)
