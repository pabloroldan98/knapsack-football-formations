# Source: https://github.com/Urbistondo/sofa-score-scraper/blob/master/player_scraper.py

import os

from selenium.common import NoSuchElementException, StaleElementReferenceException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import json
import copy
from pprint import pprint
import ast
import time

from player import Player
from useful_functions import write_dict_to_csv, read_dict_from_csv


def get_players_ratings_list(write_file=True, file_name="sofascore_players_ratings", team_links=None):
    teams_data_dict = get_players_data(write_file, file_name, team_links)
    players_ratings_list = []
    for team_name, players_ratings in teams_data_dict.items():
        if isinstance(players_ratings, str):
            players_ratings_dict = eval(players_ratings)
        else:
            players_ratings_dict = copy.deepcopy(players_ratings)
        for player_name, rating in players_ratings_dict.items():
            new_player = Player(player_name, sofascore_rating=rating, team=team_name)
            players_ratings_list.append(new_player)
    return players_ratings_list


def fix_team_data(team_data):
    for key, value in team_data.items():
        name, url = value
        if not name:
            # Extract the second to last part of the URL path, replace "-" with " ", and capitalize each word
            name = url.split("/")[-2].replace("-", " ").title().strip()
            team_data[key] = [name, url]
    return team_data


def get_team_links_from_league(league_url, driver):
    driver.get(league_url)
    wait = WebDriverWait(driver, 15)  # 15 seconds timeout
    # # Copa America
    # button_xpath = "//*[@id='__next']/main/div/div[3]/div/div[1]/div[2]/div[1]/div[5]/button"
    # button = wait.until(EC.element_to_be_clickable((By.XPATH, button_xpath)))
    # button.click()
    # teams_base_xpath = "//*[@id='__next']/main/div/div[3]/div/div[1]/div[2]/div[1]/div[4]/div/a"
    # team_name_xpath = "//*[@id='__next']/main/div/div[3]/div/div[1]/div[2]/div[1]/div[4]/div/a/div/div[1]/span"
    # Eurocopa
    teams_base_xpath = "//*[@id='__next']/main/div/div[3]/div/div[1]/div[2]/div[12]/div/div/ul/ul/li/a"
    team_name_xpath = "//*[@id='__next']/main/div/div[3]/div/div[1]/div[2]/div[12]/div/div/ul/ul/li/a"
    # # La Liga
    # teams_base_xpath = "//*[@id='__next']/main/div/div[3]/div/div/div[1]/div/div/div[1]/div/div[2]/div/a"
    # team_name_xpath = teams_base_xpath + "/div/div[3]/div/div"
    # team_name_xpath = teams_base_xpath + "/div/div[3]/div/span"
    # time.sleep(15)
    team_links = wait.until(EC.presence_of_all_elements_located((By.XPATH, teams_base_xpath)))
    team_names = wait.until(EC.presence_of_all_elements_located((By.XPATH, team_name_xpath)))
    # team_links = driver.find_elements(By.XPATH, teams_base_xpath)
    # team_names = driver.find_elements(By.XPATH, team_name_xpath)
    # Create a dictionary to hold the team names and their links
    team_data = {}
    for i, (team_link_element, team_name_element) in enumerate(zip(team_links, team_names)):
        # if i>=9:
        link = team_link_element.get_attribute('href')
        name = team_name_element.text
        # if name=="Portugal" or name=="Czechia":
        team_data[str(i+1)] = [name, link]
        # break
    team_data = fix_team_data(team_data)
    return team_data


def get_players_data(write_file=True, file_name="sofascore_players_ratings", team_links=None):
    if os.path.isfile('./' + file_name + '.csv'):
        return read_dict_from_csv(file_name)

    driver = webdriver.Chrome(keep_alive=False)
    wait = WebDriverWait(driver, 15)  # Reusable WebDriverWait
    if not team_links:
        # chrome_options = webdriver.ChromeOptions()
        # chrome_options.add_argument('--disable-gpu')  # If no GPU is available.
        # chrome_options.add_argument('--disable-extensions')
        # chrome_options.add_argument('--no-sandbox')
        # chrome_options.add_argument('--disable-images')
        extra_driver = webdriver.Chrome(keep_alive=True) #, options=chrome_options)
        # time.sleep(15)
        team_links = get_team_links_from_league(
            # "https://www.sofascore.com/tournament/football/spain/laliga/8#52376",
            "https://www.sofascore.com/tournament/football/europe/european-championship/1#id:56953",
            # "https://www.sofascore.com/tournament/football/south-america/copa-america/133#id:57114",
            extra_driver
        )
        extra_driver.quit()
    print()
    team_players_paths = dict()
    for key, value in team_links.items():
        player_paths_list = []
        print('Extracting %s player links...' % value[0])
        driver.get(value[1])
        player_paths_list = []
        players = wait.until(EC.presence_of_all_elements_located((By.XPATH, "//a[starts-with(@href, '/player/')]")))
        for i in range(len(players)):  # Iterate by index instead of direct reference
            retries = 3
            while retries:
                try:
                    player_href = players[i].get_attribute('href')  # Directly use the index to refer to the current player
                    player_paths_list.append(player_href)
                    break  # Exit the loop successfully
                except StaleElementReferenceException:
                    retries -= 1  # Decrement retry counter
                    if retries == 0:
                        print(f"Failed to retrieve href for player after several attempts.")
                        break  # Exit the loop if retries are exhausted
                    time.sleep(1)  # Short pause to allow DOM to stabilize
                    players = wait.until(EC.presence_of_all_elements_located((By.XPATH, "//a[starts-with(@href, '/player/')]")))
        # for p in players:
        #     try:
        #         player_href = p.get_attribute('href')
        #         player_paths_list.append(player_href)
        #     except StaleElementReferenceException:
        #         continue  # Skip this iteration and let the loop retry fetching fresh elements
        # # time.sleep(15)
        # players = wait.until(EC.presence_of_all_elements_located((By.XPATH, "//a[starts-with(@href, '/player/')]")))
        # # players = driver.find_elements(By.XPATH, "//a[starts-with(@href, '/player/')]")
        # for p in players:
        #     wait.until(EC.staleness_of(p))
        #     player_paths_list.append(p.get_attribute('href'))
        #     # break
        player_paths_list = sorted(list(set(player_paths_list)))
        # player_paths_list = ['https://www.sofascore.com/player/antonio-rudiger/142622', 'https://www.sofascore.com/player/thibaut-courtois/70988', ]
        print(player_paths_list)
        team_players_paths[value[0]] = player_paths_list
        # break

    teams_with_players_ratings = dict()
    j = 0
    for team_name, player_paths in team_players_paths.items():
        players_ratings = {}  # Dictionary for players in this team
        for p in player_paths:
            driver.get(p)
            average_rating = float(6.0)
            try: # Average 12 months
                # Find the div containing "Average Sofascore rating"
                average_rating = float(wait.until(EC.presence_of_element_located((By.XPATH, "//div[contains(text(), 'Average Sofascore rating')]/..//span[@role='meter']"))).get_attribute('aria-valuenow'))
            except:  # NoSuchElementException: # Spelling error making this code not work
                try: # Average last competition
                    # Find the span containing "Average Sofascore rating"
                    average_rating = float(wait.until(EC.presence_of_element_located((By.XPATH, "//span[contains(text(), 'Average Sofascore rating')]/..//span[@role='meter']"))).get_attribute('aria-valuenow'))
                    average_rating = average_rating*0.95
                except:
                    pass
            try:
                player_name = wait.until(EC.presence_of_element_located((By.XPATH, "(//h2)[1]"))).get_attribute("textContent")
                print('Extracting player data from %s ...' % player_name)
                print(average_rating)
                if player_name != "":
                    players_ratings[player_name] = average_rating
            except NoSuchElementException:  # Spelling error making this code not work as expected
                pass
            # break
            # retries = 3  # Maximum number of retries
            # for _ in range(retries):
            #     try:
            #         average_rating = float(wait.until(EC.presence_of_element_located((By.XPATH, "//span[@color='surface.s1'][@font-size='21']"))))
            #         # average_rating = float(driver.find_element(By.XPATH, "//span[@color='surface.s1'][@font-size='21']").get_attribute("textContent"))
            #         break  # Break out of the loop if successful
            #     except: # NoSuchElementException: # Spelling error making this code not work
            #         # if _ == retries - 1:  # Last attempt
            #         #     print("Failed to fetch rating after several attempts.")
            #         pass
            # for _ in range(retries):
            #     try:
            #         # time.sleep(15)
            #         player_name = wait.until(EC.presence_of_element_located((By.XPATH, "(//h2)[1]"))).get_attribute("textContent")
            #         # player_name = driver.find_element(By.XPATH, "(//h2)[1]").get_attribute("textContent")
            #         print('Extracting player data from %s ...' % player_name)
            #         # player_data = {
            #         #     "rating": average_rating,
            #         #     "team": team_name,
            #         # }
            #         # players_ratings[player_name] = player_data
            #         if player_name != "":
            #             players_ratings[player_name] = average_rating
            #         break  # Break out of the loop if successful
            #     except NoSuchElementException:  # Spelling error making this code not work as expected
            #         pass
            # break
        teams_with_players_ratings[team_name] = players_ratings  # Add to main dict
        write_dict_to_csv(teams_with_players_ratings, file_name + "_" + str(j))
        j += 1

    driver.quit()

    if write_file:
        write_dict_to_csv(teams_with_players_ratings, file_name)

    return teams_with_players_ratings


# chrome_options = webdriver.ChromeOptions()
# chrome_options.add_argument('--disable-gpu')  # If no GPU is available.
# chrome_options.add_argument('--disable-extensions')
# chrome_options.add_argument('--no-sandbox')
# chrome_options.add_argument('--disable-images')

# my_driver = webdriver.Chrome(keep_alive=True) #, options=chrome_options)
# # team_links = get_team_links_from_league("https://www.sofascore.com/tournament/football/spain/laliga/8#52376", my_driver)
# team_links = get_team_links_from_league("https://www.sofascore.com/tournament/football/europe/european-championship/1#id:56953", my_driver)
# my_driver.quit()
# pprint(team_links)

# start_time = time.time()
#
# result = get_players_ratings_list(file_name="sofascore_eurocopa_players_ratings")#, team_links=team_links)
# # result = get_players_ratings_list(file_name="test")#, team_links=team_links)
#
# end_time = time.time()
# elapsed_time = end_time - start_time
#
# print(f"Execution time: {elapsed_time} seconds")
#
# for p in result:
#     print(p)
