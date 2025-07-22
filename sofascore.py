# Source: https://github.com/Urbistondo/sofa-score-scraper/blob/master/player_scraper.py

import os
import re
from collections import defaultdict
from urllib.parse import urljoin
import tls_requests
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
    run_with_timeout, CustomTimeoutException, CustomConnectionException, find_manual_similar_string, get_working_proxy

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))  # This is your Project Root

# Maximum wait time for player data (in seconds)
MAX_WAIT_TIME = 2 * 60  # 2 minutes (120 seconds)


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
    # response = requests.get(league_url, headers=headers, verify=False)
    response = tls_requests.get(league_url, headers=headers, verify=False)
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
    # OLD General
    # panels = soup.find_all("div", attrs={"data-panelid": "1"})
    # team_links = []
    # for panel in panels:
    #     team_links.extend(
    #         panel.find_all(
    #             "a",
    #             href=lambda u: u and u.startswith("/team/"),
    #             recursive=True
    #         )
    #     )
    # # if len(team_links) > 32:
    # #     half_len = len(team_links) // 2
    # #     team_links = team_links[:half_len]
    #
    # team_data = {}
    # seen_urls = set()
    # for idx, a in enumerate(team_links, start=1):
    #     href = a["href"]
    #     full_url = urljoin("https://www.sofascore.com", href)
    #     if full_url in seen_urls:
    #         continue
    #     seen_urls.add(full_url)
    #
    #     team_name = href.split("/")[-2]
    #     team_name = team_name.replace("-", " ").strip().title()
    #
    #     name_span = a.select_one("span")
    #     if name_span:
    #         team_name = name_span.get_text(strip=True)
    #
    #     team_data[str(idx)] = [team_name, full_url]

    # General
    script = soup.find("script", id="__NEXT_DATA__")
    data = json.loads(script.string)

    def find_teams(obj, out):
        if isinstance(obj, dict):
            if "team" in obj:
                t = obj["team"]
                if all(k in t for k in ("name", "slug", "id")):
                    out.append(t)
            for v in obj.values():
                find_teams(v, out)
        elif isinstance(obj, list):
            for item in obj:
                find_teams(item, out)

    all_teams = []
    find_teams(data, all_teams)

    team_data = {}
    base = "https://www.sofascore.com/team/football"
    for idx, t in enumerate(all_teams):
        name = t["name"]
        slug = t["slug"]
        tid = t["id"]
        url = urljoin(base + "/", f"{slug}/{tid}")
        team_data[str(idx)] = [name, url]

    return team_data


def get_player_average_rating_selenium(player_url):
    print("Fallback rating")
    driver = create_driver(keep_alive=False)
    wait = WebDriverWait(driver, 15)  # Reusable WebDriverWait
    driver.get(player_url)
    average_rating = float(wait.until(EC.presence_of_element_located((By.XPATH, "//span[contains(text(), 'Average Sofascore Rating')]/..//..//span[@role='meter']"))).get_attribute('aria-valuenow'))
    average_rating = round(average_rating * 0.95, 4)
    driver.quit()
    return average_rating


def normalize_year(year_raw):
    """
    Normalizes year strings like:
    - "2025" → "2025"
    - "24/25" → "2025"
    - "22/23" → "2023"
    """
    if not year_raw:
        return None
    if "/" in year_raw:
        last_part = year_raw.split("/")[-1]
        return f"20{last_part}"
    return year_raw


def get_player_last_year_rating(player_url):
    """
    Given a SofaScore player URL like:
        https://www.sofascore.com/player/unai-marrero/1094782
        get https://www.sofascore.com/api/v1/player/1094782/statistics/match-type/overall
    This function:
      1) Extracts the player_id (e.g. 1094782)
      2) Fetches the player's 'statistics/seasons' data
      3) Takes the totalRating and countRating of each seasson, does the sum and gets the average
      4) Return latest year
    """
    print("Fallback rating")
    # time.sleep(5)

    # 1) Extract the player ID from the URL via regex or string split
    match = re.search(r"/player/[^/]+/(\d+)$", player_url)
    if not match:
        print(f"Could not extract player_id from URL: {player_url}")
        return None
    player_id = match.group(1)

    # 2) Fetch seasons info: /api/v1/player/{player_id}/statistics/match-type/overall
    seasons_url = f"https://www.sofascore.com/api/v1/player/{player_id}/statistics/match-type/overall"
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/91.0.4472.124 Safari/537.36"
        )
    }
    # resp = requests.get(seasons_url, headers=headers, verify=False)
    resp = tls_requests.get(seasons_url, headers=headers, verify=False)
    if resp.status_code != 200:
        # Raise your custom exception if HTTP status is not 200
        raise CustomConnectionException(f"HTTP {resp.status_code} when fetching {seasons_url}")
    data = resp.json()

    # Step 1: Safely get seasons
    seasons = data.get("seasons", [])

    # Step 2: Aggregate totalRating and countRating per year
    ratings_by_year = defaultdict(lambda: {"total": 0.0, "count": 0})

    for season in seasons:
        statistics = season.get("statistics", {})
        year_raw = season.get("year")
        year = normalize_year(year_raw)

        total_rating = statistics.get("totalRating")
        count_rating = statistics.get("countRating")

        if total_rating is not None and count_rating:
            ratings_by_year[year]["total"] += total_rating
            ratings_by_year[year]["count"] += count_rating

    # Step 3: Compute average per year
    average_ratings = {
        year: vals["total"] / vals["count"]
        for year, vals in ratings_by_year.items()
        if vals["count"] > 0
    }

    # Step 4: Return latest year with its average
    if average_ratings:
        latest_year = sorted(average_ratings.keys(), reverse=True)[0]
        rating = average_ratings[latest_year]
        # print(f"Latest year: {latest_year} | Average Rating: {rating:.2f}")
    else:
        print("No valid rating data found.")

    average_rating = float(rating)
    average_rating = round(average_rating * 0.95, 4)
    return average_rating


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
        )
    }
    # resp = requests.get(seasons_url, headers=headers, verify=False)
    resp = tls_requests.get(seasons_url, headers=headers, verify=False)
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
    # resp_stats = requests.get(stats_url, headers=headers, verify=False)
    resp_stats = tls_requests.get(stats_url, headers=headers, verify=False)
    if resp_stats.status_code != 200:
        # Raise your custom exception if HTTP status is not 200
        raise CustomConnectionException(f"HTTP {resp.status_code} when fetching {stats_url}")

    stats_data = resp_stats.json()
    statistics = stats_data.get("statistics", {})
    rating = statistics.get("rating")

    average_rating = float(rating)
    average_rating = round(average_rating * 0.95, 4)
    return average_rating


def get_player_average_rating(player_url):
    """
    Given a SofaScore player URL like:
        https://www.sofascore.com/player/unai-marrero/1094782
        get https://www.sofascore.com/api/v1/player/1094782/last-year-summary
    This function:
      1) Extracts the player_id (e.g. 1094782)
      2) Fetches the player's 'last-year-summary' data
      3) Calculates average rating based on event type summary
    """
    # 1) Extract the player ID from the URL via regex or string split
    match = re.search(r"/player/[^/]+/(\d+)$", player_url)
    if not match:
        print(f"Could not extract player_id from URL: {player_url}")
        return None
    player_id = match.group(1)

    # 2) Fetch seasons info: /api/v1/player/{player_id}/last-year-summary
    seasons_url = f"https://www.sofascore.com/api/v1/player/{player_id}/last-year-summary"
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/91.0.4472.124 Safari/537.36"
        )
    }
    # resp = requests.get(seasons_url, headers=headers, verify=False)
    resp = tls_requests.get(seasons_url, headers=headers, verify=False)
    if resp.status_code != 200:
        # Raise your custom exception if HTTP status is not 200
        raise CustomConnectionException(f"HTTP {resp.status_code} when fetching {seasons_url}")
    data = resp.json()

    # Safely get the list of events from the summary
    summary = data.get("summary", [])

    # Extract float values where type == "event", using safe .get() access
    event_values = [
        float(item.get("value"))
        for item in summary
        if item.get("type") == "event" and item.get("value") is not None
    ]

    # Calculate average safely
    rating = sum(event_values) / len(event_values) if event_values else None

    average_rating = float(rating)
    average_rating = round(average_rating, 2)
    return average_rating


def get_player_page_average_rating(player_url):
    """
    Given a SofaScore player URL like:
        https://www.sofascore.com/player/unai-marrero/1094782
    This function:
      1) Try to find the <span role="meter" aria-valuenow="..."> (Summary last 12 months).
    """
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/91.0.4472.124 Safari/537.36"
        )
    }
    # resp = requests.get(p, headers=headers, verify=False)
    resp = tls_requests.get(player_url, headers=headers, verify=False)
    if resp.status_code != 200:
        # Raise your custom exception if HTTP status is not 200
        raise CustomConnectionException(f"HTTP {resp.status_code} when fetching {p}")

    sp = BeautifulSoup(resp.text, "html.parser")

    # Attempt #1: "Summary (last 12 months)"
    rating_span = sp.find("span", {"role": "meter"})
    if rating_span and rating_span.has_attr("aria-valuenow"):
        average_rating = float(rating_span["aria-valuenow"])
        return average_rating

    return None


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
            # "https://www.sofascore.com/tournament/football/world/club-world-championship/357#id:69619",
            "https://www.sofascore.com/tournament/football/spain/laliga/8#id:77559",
            # "https://www.sofascore.com/tournament/football/spain/laliga/8#52376",
            # "https://www.sofascore.com/tournament/football/europe/european-championship/1#id:56953",
            # "https://www.sofascore.com/tournament/football/south-america/copa-america/133#id:57114",
        )
    # team_links = {
    #     '0': ['León', 'https://www.sofascore.com/team/football/club-leon/36534'],
    # }

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
        team_name = find_manual_similar_string(team_name)
        team_url = value[1]
        player_paths_list = []

        # "Extracting %s player links..." from original code:
        print('Extracting %s player links...' % team_name)

        # GET the team page
        # response = requests.get(team_url, headers=headers, verify=False)
        response = tls_requests.get(team_url, headers=headers, verify=False)
        soup = BeautifulSoup(response.text, "html.parser")

        a_tags = soup.find_all("a", href=True)
        for a_tag in a_tags:
            href_val = a_tag["href"]
            # if href_val.startswith("/player/"):
            if "/player/" in href_val:
                # Construct absolute URL
                full_url = "https://www.sofascore.com" + href_val
                player_paths_list.append(full_url)

        player_paths_list = sorted(list(set(player_paths_list)))
        # player_paths_list = [path for path in player_paths_list if "unai-marrero" in path]
        # player_paths_list = [path for path in player_paths_list if "marc-bernal" in path]
        # player_paths_list = [path for path in player_paths_list if "diakhaby" in path]
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

                    # Attempt #1: "Summary (last 12 months)"
                    try:
                        average_rating = float(get_player_page_average_rating(p))
                        return average_rating
                    except:
                        pass

                    # Attempt #2: "last-year-summary" via api
                    try:
                        average_rating = float(get_player_average_rating(p))
                        return average_rating
                    except:
                        pass

                    # Attempt #3: "Average Sofascore Rating" fallback
                    # Find the rating of the last year he played
                    try:
                        average_rating = float(get_player_last_year_rating(p))
                        return average_rating
                    except:
                        pass

                    # # Attempt #4: "Average Sofascore Rating" fallback
                    # # Find the rating of the last tournament
                    # try:
                    #     average_rating = float(get_player_statistics_rating(p))
                    #     # average_rating = get_player_average_rating_selenium(p)
                    # except:
                    #     pass

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
                    # resp = requests.get(p, headers=headers, verify=False)
                    resp = tls_requests.get(p, headers=headers, verify=False)
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
                        # players_ratings[player_name] = average_rating
                        players_ratings[player_name] = average_rating if average_rating != 0 else float(6.0)
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

# # team_links = get_team_links_from_league("https://www.sofascore.com/tournament/football/world/club-world-championship/357#id:69619")
# team_links = get_team_links_from_league("https://www.sofascore.com/tournament/football/spain/laliga/8#id:77559")
# pprint(team_links)
#
#
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
