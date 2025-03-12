# Source: https://github.com/Urbistondo/sofa-score-scraper/blob/master/player_scraper.py

import os
import re

import requests
from bs4 import BeautifulSoup
import urllib3
from http.client import RemoteDisconnected
from requests.exceptions import ReadTimeout
from urllib3.exceptions import ReadTimeoutError
from selenium.common.exceptions import NoSuchElementException, StaleElementReferenceException, TimeoutException, WebDriverException
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
from useful_functions import write_dict_data, read_dict_data, overwrite_dict_data, delete_file, create_driver, \
    run_with_timeout, CustomTimeoutException, CustomConnectionException, find_manual_similar_string

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))  # This is your Project Root

# Maximum wait time for player data (in seconds)
MAX_WAIT_TIME = 30  # 30 seconds


def get_players_ratings_list(
        write_file=True,
        file_name="sofascore_players_ratings",
        team_links=None,
        backup_files=True,
        force_scrape=False
):
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

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


def get_team_links_from_league(league_url):
    # We do a direct HTTP GET
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/91.0.4472.124 Safari/537.36"
        )
    }
    # Insecure: Disables certificate verification
    response = requests.get(league_url, headers=headers, verify=False)
    html = response.text

    soup = BeautifulSoup(html, "html.parser")

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
    # teams_base_xpath = "//*[@data-testid='standings_row']"
    # team_name_xpath = teams_base_xpath + "/div/div[2]/div/div"
    # time.sleep(15)

    # Find all <a> tags with data-testid="standings_row"
    rows = soup.find_all("a", attrs={"data-testid": "standings_row"})
    half_len = len(rows) // 2
    rows = rows[:half_len]

    team_data = {}
    for i, row in enumerate(rows):
        if i < 15:
            continue
        link = row.get("href", "")
        if link.startswith("/"):
            link = "https://www.sofascore.com" + link

        # Step 1: find the main <div> inside the <a>
        outer_div = row.find("div", class_="Box")
        if not outer_div:
            continue  # Might be a malformed row

        # Step 2: get all direct child elements (div/img/etc)
        children = list(outer_div.children)

        if len(children) < 3:
            continue
        name_container = children[2]

        name_div = name_container.find("div", class_="Text fsoviT")
        if not name_div:
            team_name = ""
        else:
            team_name = name_div.get_text(strip=True)

        team_data[str(i+1)] = [team_name, link]
        break
    team_data = fix_team_data(team_data)
    return team_data


def get_player_statistics_rating(player_url):
    """
    Given a SofaScore player URL like:
        https://www.sofascore.com/player/unai-marrero/1094782
    This function:
      1) Extracts the player_id (e.g. 1094782)
      2) Fetches the player's 'statistics/seasons' data
      3) Takes the FIRST uniqueTournament and its FIRST season
      4) Calls the 'statistics/overall' endpoint for that uniqueTournament/season
      5) Returns the 'statistics'->'rating' float or None if not found
    """
    print("Fallback rating")
    # time.sleep(5)
    print(player_url)

    # 1) Extract the player ID from the URL via regex or string split
    match = re.search(r"/player/[^/]+/(\d+)$", player_url)
    if not match:
        print(f"Could not extract player_id from URL: {player_url}")
        return None
    player_id = match.group(1)

    # 2) Fetch seasons info: /api/v1/player/{player_id}/statistics/seasons
    seasons_url = f"https://www.sofascore.com/api/v1/player/{player_id}/statistics/seasons"
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/91.0.4472.124 Safari/537.36"
        ),
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Referer": "https://www.sofascore.com/",  # or the actual page from which you'd ordinarily access the API
    }
    print(seasons_url)
    resp = requests.get(seasons_url, headers=headers, verify=False)
    if resp.status_code != 200:
        # Raise your custom exception if HTTP status is not 200
        raise CustomConnectionException(f"HTTP {resp.status_code} when fetching {seasons_url}")
    data = resp.json()

    # 3) Parse to find the FIRST uniqueTournament and FIRST season ID
    unique_tournament_seasons = data.get("uniqueTournamentSeasons", [])
    if not unique_tournament_seasons:
        print("No uniqueTournamentSeasons found in the response.")
        return None

    first_uts = unique_tournament_seasons[0]
    unique_tournament = first_uts.get("uniqueTournament", {})
    unique_tournament_id = unique_tournament.get("id")

    seasons_list = first_uts.get("seasons", [])
    if not seasons_list:
        print("No seasons found for the first uniqueTournament.")
        return None

    first_season_id = seasons_list[0].get("id")

    if not unique_tournament_id or not first_season_id:
        print("Missing uniqueTournamentId or seasonId.")
        return None

    # 4) Fetch the statistics/overall data:
    stats_url = (f"https://www.sofascore.com/api/v1/player/{player_id}"
                 f"/unique-tournament/{unique_tournament_id}"
                 f"/season/{first_season_id}/statistics/overall")
    print(stats_url)
    resp_stats = requests.get(stats_url, headers=headers, verify=False)
    if resp_stats.status_code != 200:
        # Raise your custom exception if HTTP status is not 200
        raise CustomConnectionException(f"HTTP {resp.status_code} when fetching {stats_url}")


    stats_data = resp_stats.json()
    statistics = stats_data.get("statistics", {})
    print(statistics)
    rating = statistics.get("rating")
    print(rating)

    return rating


def get_players_data(
        write_file=True,
        file_name="sofascore_players_ratings",
        team_links=None,
        backup_files=True,
        force_scrape=False
):
    if not force_scrape:
        data = read_dict_data(file_name)
        if data:
            return data

    if not team_links:
        team_links = get_team_links_from_league(
            "https://www.sofascore.com/tournament/football/spain/laliga/8#52376",
            # "https://www.sofascore.com/tournament/football/europe/european-championship/1#id:56953",
            # "https://www.sofascore.com/tournament/football/south-america/copa-america/133#id:57114",
        )

    print()
    team_players_paths = dict()
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/91.0.4472.124 Safari/537.36"
        )
    }

    for key, value in team_links.items():
        team_name = value[0]
        team_url = value[1]
        player_paths_list = []

        # "Extracting %s player links..." from original code:
        print('Extracting %s player links...' % team_name)

        # GET the team page
        response = requests.get(team_url, headers=headers, verify=False)
        soup = BeautifulSoup(response.text, "html.parser")

        a_tags = soup.find_all("a", href=True)
        for a_tag in a_tags:
            href_val = a_tag["href"]
            if href_val.startswith("/player/"):
                # Construct absolute URL
                full_url = "https://www.sofascore.com" + href_val
                player_paths_list.append(full_url)

        player_paths_list = sorted(list(set(player_paths_list)))
        # player_paths_list = [path for path in player_paths_list if "unai-marrero" in path]
        # player_paths_list = [path for path in player_paths_list if "marc-bernal" in path]
        player_paths_list = [path for path in player_paths_list if "diakhaby" in path]
        print(player_paths_list)
        team_players_paths[team_name] = player_paths_list

    teams_with_players_ratings = dict()
    j = 0

    # Now we fetch each player's rating
    for team_name, player_paths in team_players_paths.items():
        players_ratings = {}
        for p in player_paths:
            # 1) Attempt rating with timeouts + fallback
            average_rating = float(6.0)
            timeout_retries = 3

            while timeout_retries > 0:
                def scrape_players_rating_task():
                    """
                    1) Try to find the <span role="meter" aria-valuenow="...">
                       (Summary last 12 months).
                    2) If not found, try to find "Average Sofascore Rating"
                       then look for the <span role="meter"> near it,
                       apply *0.95.
                    """
                    average_rating = float(6.0)
                    resp = requests.get(p, headers=headers, verify=False)
                    if resp.status_code != 200:
                        # Raise your custom exception if HTTP status is not 200
                        raise CustomConnectionException(f"HTTP {resp.status_code} when fetching {p}")

                    sp = BeautifulSoup(resp.text, "html.parser")

                    # Attempt #1: "Summary (last 12 months)"
                    rating_span = sp.find("span", {"role": "meter"})
                    if rating_span and rating_span.has_attr("aria-valuenow"):
                        try:
                            average_rating = float(rating_span["aria-valuenow"])
                            return average_rating
                        except:
                            pass

                    # Attempt #2: "Average Sofascore Rating" fallback
                    # Find the rating of the last tournament
                    try:
                        average_rating = float(get_player_statistics_rating(p))
                        return round(average_rating * 0.95, 4)
                    except:
                        pass

                    return average_rating  # If all fails, return 6.0

                try:
                    average_rating = run_with_timeout(MAX_WAIT_TIME, scrape_players_rating_task)
                    break  # Break if successful
                except (CustomTimeoutException, CustomConnectionException, ReadTimeout, ReadTimeoutError, RemoteDisconnected) as e:
                    timeout_retries -= 1
                    print(f"Retrying to fetch sofascore player rating ({p}) due to timeout/connection error... "
                          f"({timeout_retries} retry left)")
                    time.sleep(1)
                    if timeout_retries <= 0:
                        print("Failed to fetch rating after several attempts.")
                        break

            # 2) Attempt player name with timeouts
            timeout_retries = 3

            while timeout_retries > 0:
                def scrape_players_name_task():
                    """
                    Just tries to find an <h2> (like your Selenium code: "(//h2)[1]")
                    """
                    player_name = ""
                    resp = requests.get(p, headers=headers, verify=False)
                    if resp.status_code != 200:
                        # Raise your custom exception if HTTP status is not 200
                        raise CustomConnectionException(f"HTTP {resp.status_code} when fetching {p}")

                    sp = BeautifulSoup(resp.text, "html.parser")
                    h2_tag = sp.find("h2")
                    if h2_tag:
                        try:
                            player_name = h2_tag.get_text(strip=True)
                        except:
                            pass
                    return player_name

                try:
                    player_name = run_with_timeout(MAX_WAIT_TIME, scrape_players_name_task)
                    print('Extracting player data from %s ...' % player_name)
                    print(average_rating)
                    if player_name != "":
                        player_name = find_manual_similar_string(player_name)
                        players_ratings[player_name] = average_rating
                    break
                except (CustomTimeoutException, CustomConnectionException, ReadTimeout, ReadTimeoutError, RemoteDisconnected) as e:
                    timeout_retries -= 1
                    print(f"Retrying to fetch sofascore player name ({p}) due to timeout/connection error... "
                          f"({timeout_retries} retry left)")
                    time.sleep(1)
                    if timeout_retries <= 0:
                        print("Failed to fetch player name after several attempts.")
                        break
        teams_with_players_ratings[team_name] = players_ratings  # Add to main dict
        # print(teams_with_players_ratings)

        if backup_files:
            # write_dict_data(teams_with_players_ratings, file_name + "_" + str(j))
            overwrite_dict_data(teams_with_players_ratings, file_name + "_" + str(j), ignore_valid_file=True)
        j += 1

    if write_file:
        # write_dict_data(teams_with_players_ratings, file_name)
        overwrite_dict_data(teams_with_players_ratings, file_name)

    if backup_files:
        for k in range(j):
            delete_file(file_name + "_" + str(j))

    return teams_with_players_ratings

# team_links = get_team_links_from_league("https://www.sofascore.com/tournament/football/spain/laliga/8#52376")
# pprint(team_links)


# start_time = time.time()
#
# result = get_players_ratings_list(file_name="test", force_scrape=True)#, team_links=team_links)
# # result = get_players_ratings_list(file_name="test")#, team_links=team_links)
#
# end_time = time.time()
# elapsed_time = end_time - start_time
#
# print(f"Execution time: {elapsed_time} seconds")
#
# for p in result:
#     print(p)
#     print(p.sofascore_rating)
