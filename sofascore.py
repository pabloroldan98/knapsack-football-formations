# Source: https://github.com/Urbistondo/sofa-score-scraper/blob/master/player_scraper.py

import csv
import os

from selenium.common import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium import webdriver
from pprint import pprint

from player import Player


def get_players_ratings_list(write_file=True, file_name="sofascore_players_ratings", team_links=None):
    players_average_ratings_dict = get_players_average_ratings(write_file, file_name, team_links)
    players_ratings_list = []
    for player_name, player_rating in players_average_ratings_dict.items():
        new_player = Player(player_name, sofascore_rating=player_rating)
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


def get_players_average_ratings(write_file=True, file_name="sofascore_players_ratings", team_links=None):
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
    player_paths = []
    for key, value in team_links.items():
        print('Extracting %s player links...' % value[0])
        driver.get(value[1])
        players = driver.find_elements(By.XPATH, "//*[contains(@class, 'sc-fqkvVR gwUJxr')]/a")
        for p in players:
            player_paths.append(p.get_attribute('href'))

    players_with_ratings = dict()
    save_counter = -1
    j = 0
    for p in player_paths:
        driver.get(p)
        average_rating = float(6.0)
        try:
            average_rating = float(driver.find_element(By.XPATH, "//span[@class='sc-jEACwC gWYCya']").get_attribute("textContent"))
        except: # NoSuchElementException:  # Spelling error making this code not work as expected
            pass
        try:
            player_name = driver.find_element(By.XPATH, "//h2[@class='sc-jEACwC cFQcxI']").get_attribute("textContent")
            print('Extracting team data from %s ...' % player_name)
            players_with_ratings[player_name] = average_rating
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


def write_dict_to_csv(dict_data, file_name):
    with open(file_name + ".csv", 'w', encoding='utf-8', newline='') as csv_file:  # Specify newline parameter
        writer = csv.writer(csv_file)
        for key, value in dict_data.items():
            writer.writerow([key, value])


def read_dict_from_csv(file_name):
    with open(file_name + ".csv", encoding='utf-8') as csv_file:
        reader = csv.reader(csv_file)
        mydict = dict(reader)
        return mydict


# driver = webdriver.Chrome(keep_alive=True)
# team_links = get_team_links_from_league("https://www.sofascore.com/tournament/football/spain/laliga/8#52376", driver)
# driver.quit()
# # pprint(team_links)
# result = get_players_ratings_list(file_name="sofascore_la_liga_players_ratings", team_links=team_links)
