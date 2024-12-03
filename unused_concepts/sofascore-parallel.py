# Source: https://github.com/Urbistondo/sofa-score-scraper/blob/master/player_scraper.py

import os
from selenium.common import NoSuchElementException, StaleElementReferenceException, TimeoutException, WebDriverException
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
import concurrent.futures

from player import Player
from useful_functions import write_dict_to_csv, read_dict_from_csv, overwrite_dict_to_csv, delete_file, create_driver, \
    run_with_timeout, CustomTimeoutException, find_manual_similar_string

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))  # This is your Project Root

# Maximum wait time for player data (in seconds)
MAX_WAIT_TIME = 5 * 60  # 5 minutes in seconds


def get_players_ratings_list(
        write_file=True,
        file_name="sofascore_players_ratings",
        team_links=None,
        backup_files=True,
        force_scrape=False
):
    teams_data_dict = get_players_data(write_file, file_name, team_links, backup_files=backup_files, force_scrape=force_scrape)
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
    # button_xpath = "//*[@id='__next']/main/div/div[3]/div/div[1]/div[2]/div[7]/div[2]/div[2]/button"
    # button = wait.until(EC.element_to_be_clickable((By.XPATH, button_xpath)))
    # button.click()
    # teams_base_xpath = "//*[@id='__next']/main/div/div[3]/div/div[1]/div[2]/div[1]/div[4]/div/a"
    # team_name_xpath = "//*[@id='__next']/main/div/div[3]/div/div[1]/div[2]/div[1]/div[4]/div/a/div/div[1]/span"
    # # Eurocopa
    # teams_base_xpath = "//*[@id='__next']/main/div/div[3]/div/div[1]/div[2]/div[12]/div/div/ul/ul/li/a"
    # team_name_xpath = "//*[@id='__next']/main/div/div[3]/div/div[1]/div[2]/div[12]/div/div/ul/ul/li/a"
    # La Liga
    teams_base_xpath = "//*[@id='__next']/main/div/div[3]/div/div/div[1]/div/div/div[1]/div/div[2]/div/a"
    team_name_xpath = teams_base_xpath + "/div/div[2]/div/div"
    # time.sleep(15)
    # driver.save_screenshot('team_links.png')
    team_links = wait.until(EC.presence_of_all_elements_located((By.XPATH, teams_base_xpath)))
    # time.sleep(15)
    # driver.save_screenshot('team_names.png')
    team_names = wait.until(EC.presence_of_all_elements_located((By.XPATH, team_name_xpath)))
    # Create a dictionary to hold the team names and their links
    team_data = {}
    for i, (team_link_element, team_name_element) in enumerate(zip(team_links, team_names)):
        # if i < 17:
        #     continue
        link = team_link_element.get_attribute('href')
        name = team_name_element.text
        # if (name=="Spain" or name=="France" or name=="England" or name=="Netherlands"
        #         or name=="Argentina" or name=="Canada" or name=="Colombia" or name=="Uruguay"):
        team_data[str(i+1)] = [name, link]
        # break
    team_data = fix_team_data(team_data)
    return team_data


def get_players_data(
        write_file=True,
        file_name="sofascore_players_ratings",
        team_links=None,
        backup_files=True,
        force_scrape=False
):
    if not force_scrape:
        if os.path.isfile(ROOT_DIR + '/csv_files/' + file_name + '.csv'):
            data = read_dict_from_csv(file_name)
            return data

    driver = create_driver(keep_alive=False)
    wait = WebDriverWait(driver, 15)  # Reusable WebDriverWait
    if not team_links:
        extra_driver = create_driver(keep_alive=True)  # Keep alive for extra_driver
        team_links = get_team_links_from_league(
            "https://www.sofascore.com/tournament/football/spain/laliga/8#52376",
            # "https://www.sofascore.com/tournament/football/europe/european-championship/1#id:56953",
            # "https://www.sofascore.com/tournament/football/south-america/copa-america/133#id:57114",
            extra_driver
        )
        extra_driver.quit()
    print()
    # team_players_paths = dict()
    # for key, value in team_links.items():
    def scrape_team_players(driver, wait, value):
        player_paths_list = []
        timeout_retries = 3
        while timeout_retries > 0:
            def scrape_team_players_task():
                player_paths_list = []
                print('Extracting %s player links...' % value[0])
                driver.get(value[1])
                players_xpath = "//a[starts-with(@href, '/player/') and .//div[contains(@cursor, 'pointer')]]"
                players = wait.until(EC.presence_of_all_elements_located((By.XPATH, players_xpath)))
                for i in range(len(players)):  # Iterate by index instead of direct reference
                    retries = 3
                    while retries > 0:
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
                            players = wait.until(EC.presence_of_all_elements_located((By.XPATH, players_xpath)))
                return player_paths_list
            try:
                # Run the task with timeout
                player_paths_list = run_with_timeout(MAX_WAIT_TIME, scrape_team_players_task)
                break  # Exit the loop if successful
            except (CustomTimeoutException, TimeoutException, WebDriverException, StaleElementReferenceException):
                timeout_retries -= 1  # Decrement retry counter
                driver.quit()
                driver = create_driver(keep_alive=False)  # Restart the driver
                wait = WebDriverWait(driver, 15)  # Reusable WebDriverWait
                print(f"Retrying to fetch team players ({value[1]}) due to timeout... ({timeout_retries} retry left)")

        player_paths_list = sorted(list(set(player_paths_list)))
        # player_paths_list = ['https://www.sofascore.com/player/antonio-rudiger/142622', 'https://www.sofascore.com/player/thibaut-courtois/70988', ]
        print(player_paths_list)
        return player_paths_list

    def parallel_scrape_team_players(team_links, driver):
        team_players_paths = dict()

        with concurrent.futures.ThreadPoolExecutor(max_workers=len(team_links)) as executor:  # Adjust max_workers as needed
            future_to_team = {
                executor.submit(scrape_team_players, driver, wait, value): key
                for key, value in team_links.items()
            }

            for future in concurrent.futures.as_completed(future_to_team):
                key = future_to_team[future]
                try:
                    player_paths_list = future.result()
                    player_paths_list = sorted(list(set(player_paths_list)))  # Remove duplicates
                    print(f"{key}: {player_paths_list}")
                    team_players_paths[key] = player_paths_list
                except Exception as exc:
                    print(f"{key} generated an exception: {exc}")

        return team_players_paths

        # team_players_paths[value[0]] = player_paths_list
        # break

    team_players_paths = parallel_scrape_team_players(team_links, driver)

    teams_with_players_ratings = dict()
    j = 0
    for team_name, player_paths in team_players_paths.items():
        players_ratings = {}  # Dictionary for players in this team
        for p in player_paths:
            average_rating = float(6.0)
            timeout_retries = 1
            while timeout_retries > 0:
                def scrape_players_rating_task():
                    driver.get(p)
                    average_rating = float(6.0)
                    try:  # Average 12 months
                        # Find the span containing "Summary (last 12 months)"
                        average_rating = float(wait.until(EC.presence_of_element_located((By.XPATH, "//span[contains(text(), 'Summary (last 12 months)')]/..//..//span[@role='meter']"))).get_attribute('aria-valuenow'))
                    except:  # NoSuchElementException: # Spelling error making this code not work
                        try: # Average last competition
                            # Find the span containing "Average Sofascore Rating"
                            average_rating = float(wait.until(EC.presence_of_element_located((By.XPATH, "//span[contains(text(), 'Average Sofascore Rating')]/..//..//span[@role='meter']"))).get_attribute('aria-valuenow'))
                            average_rating = round(average_rating * 0.95, 4)
                        except:
                            pass
                    return average_rating
                try:
                    # Run the task with timeout
                    average_rating = run_with_timeout(MAX_WAIT_TIME, scrape_players_rating_task)
                    break  # Exit the loop if successful
                except (CustomTimeoutException, TimeoutException, WebDriverException, StaleElementReferenceException):
                    timeout_retries -= 1  # Decrement retry counter
                    driver.quit()
                    driver = create_driver(keep_alive=False)  # Restart the driver
                    wait = WebDriverWait(driver, 15)  # Reusable WebDriverWait
                    print(f"Retrying to fetch sofascore player rating ({p}) due to timeout... ({timeout_retries} retry left)")
                    if timeout_retries <= 0:
                        driver.get(p)
            try:
                player_name = wait.until(EC.presence_of_element_located((By.XPATH, "(//h2)[1]"))).get_attribute("textContent")
                print('Extracting player data from %s ...' % player_name)
                print(average_rating)
                if player_name != "":
                    player_name = find_manual_similar_string(player_name)
                    players_ratings[player_name] = average_rating
            except NoSuchElementException:  # Spelling error making this code not work as expected
                pass
        teams_with_players_ratings[team_name] = players_ratings  # Add to main dict
        if backup_files:
            # write_dict_to_csv(teams_with_players_ratings, file_name + "_" + str(j))
            overwrite_dict_to_csv(teams_with_players_ratings, file_name + "_" + str(j), ignore_valid_file=True)
        j += 1

    driver.quit()

    if write_file:
        # write_dict_to_csv(teams_with_players_ratings, file_name)
        overwrite_dict_to_csv(teams_with_players_ratings, file_name)

    if backup_files:
        for k in range(j):
            delete_file(file_name + "_" + str(j))

    return teams_with_players_ratings


# start_time = time.time()
#
# result = get_players_ratings_list(file_name="test", force_scrape=True)
#
# end_time = time.time()
# elapsed_time = end_time - start_time
#
# print(f"Execution time: {elapsed_time} seconds")
#
# for p in result:
#     print(p)
