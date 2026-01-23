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
import random

from player import Player
from useful_functions import write_dict_data, read_dict_data, overwrite_dict_data, delete_file, create_driver, \
    run_with_timeout, CustomTimeoutException, CustomConnectionException, CustomMissingException, \
    find_manual_similar_string, get_working_proxy


ROOT_DIR = os.path.dirname(os.path.abspath(__file__))  # This is your Project Root

# Maximum wait time for player data (in seconds)
MAX_WAIT_TIME = 2 * 60  # 2 minutes (120 seconds)

# random header pool
HEADER_POOL = [
    # Your current one (Chrome 91 / Windows)
    {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/91.0.4472.124 Safari/537.36"
        )
    },

    # Chrome / Windows (newer-ish)
    {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    },

    # Chrome / macOS
    {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    },

    # Chrome / Linux
    {
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    },

    # Firefox / Windows
    {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) "
            "Gecko/20100101 Firefox/121.0"
        )
    },

    # Safari / macOS
    {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_6) "
            "AppleWebKit/605.1.15 (KHTML, like Gecko) "
            "Version/17.1 Safari/605.1.15"
        )
    },
]


def pick_headers():
    # copy() so you don't accidentally mutate the pool entry later
    return random.choice(HEADER_POOL).copy()


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
    headers = pick_headers()
    # response = requests.get(league_url, headers=headers, verify=False)
    response = tls_requests.get(league_url, headers=headers, verify=False)
    html = response.text

    soup = BeautifulSoup(html, "html.parser")

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


def get_player_average_rating_selenium_short(player_url):
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


def get_player_last_year_rating(player_url, headers=None, use_proxies=False):
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
    if not headers:
        headers = pick_headers()
    # resp = requests.get(seasons_url, headers=headers, verify=False)
    if use_proxies:
        working_proxy = get_working_proxy(player_url)
        resp = tls_requests.get(seasons_url, headers=headers, verify=False, proxy=working_proxy)
    else:
        resp = tls_requests.get(seasons_url, headers=headers, verify=False)
    # if resp.status_code == 403: # If blocked by too many calls
    #     print(f"Status: {resp.status_code} , trying with no headers")
    #     time.sleep(30)
    #     return get_player_last_year_rating(player_url, headers=None)
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


def get_player_last_tournament_rating_selenium(player_url):
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
    headers = pick_headers()
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


def get_player_average_rating(player_url, headers=None, use_proxies=False):
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
    if not headers:
        headers = pick_headers()
    # resp = requests.get(seasons_url, headers=headers, verify=False)
    if use_proxies:
        working_proxy = get_working_proxy(player_url)
        resp = tls_requests.get(seasons_url, headers=headers, verify=False, proxy=working_proxy)
    else:
        resp = tls_requests.get(seasons_url, headers=headers, verify=False)
    # if resp.status_code == 403: # If blocked by too many calls
    #     print(f"Status: {resp.status_code} , trying with no headers")
    #     time.sleep(30)
    #     return get_player_average_rating(player_url, headers=None)
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


def get_player_average_rating_selenium(player_url):
    """
    Given a SofaScore player URL like:
        https://www.sofascore.com/player/unai-marrero/1094782
    This function:
      1) Try to find the <span role="meter" aria-valuenow="..."> (Summary last 12 months).
    """
    headers = pick_headers()
    # resp = requests.get(p, headers=headers, verify=False)
    resp = tls_requests.get(player_url, headers=headers, verify=False)
    if resp.status_code != 200:
        # Raise your custom exception if HTTP status is not 200
        raise CustomConnectionException(f"HTTP {resp.status_code} when fetching {player_url}")

    sp = BeautifulSoup(resp.text, "html.parser")

    # Attempt #1: "Summary (last 12 months)"
    rating_span = sp.find("span", {"role": "meter"})
    if rating_span and rating_span.has_attr("aria-valuenow"):
        average_rating = float(rating_span["aria-valuenow"])
        return average_rating

    return None


def get_player_name(player_url, headers=None, use_proxies=False):
    """
    Given a SofaScore player URL like:
        https://www.sofascore.com/player/unai-marrero/1094782
        get https://www.sofascore.com/api/v1/player/1094782
    This function:
      1) Extracts the player_id (e.g. 1094782)
      2) Fetches the player's 'name' data
    """
    # 1) Extract the player ID from the URL via regex or string split
    match = re.search(r"/player/[^/]+/(\d+)$", player_url)
    if not match:
        print(f"Could not extract player_id from URL: {player_url}")
        return None
    player_id = match.group(1)

    # 2) Fetch seasons info: /api/v1/player/{player_id}/last-year-summary
    player_api_url = f"https://www.sofascore.com/api/v1/player/{player_id}"
    if not headers:
        headers = pick_headers()
    # resp = requests.get(player_api_url, headers=headers, verify=False)
    if use_proxies:
        working_proxy = get_working_proxy(player_url)
        resp = tls_requests.get(player_api_url, headers=headers, verify=False, proxy=working_proxy)
    else:
        resp = tls_requests.get(player_api_url, headers=headers, verify=False)
    # if resp.status_code == 403: # If blocked by too many calls
    #     print(f"Status: {resp.status_code} , trying with no headers")
    #     time.sleep(30)
    #     return get_player_average_rating(player_api_url, headers=None)
    if resp.status_code != 200:
        # print(resp.text)
        # Raise your custom exception if HTTP status is not 200
        raise CustomConnectionException(f"HTTP {resp.status_code} when fetching {player_api_url}")
    data = resp.json()

    # Safely get the player name (returns None if not found)
    player_name = (data.get("player") or {}).get("name")

    if not player_name:
        # Raise a CustomMissingException exception if no name was fetched
        raise CustomMissingException("No name was fetched")

    return player_name


def get_player_name_selenium(player_url, headers=None):
    """
    Just tries to find an <h2> (like your Selenium code: "(//h2)[1]")
    """
    print("Fallback name")
    if not headers:
        headers = pick_headers()
    # resp = requests.get(p, headers=headers, verify=False)
    resp = tls_requests.get(player_url, headers=headers, verify=False)
    if resp.status_code != 200:
        # print(resp.text)
        # Raise your custom exception if HTTP status is not 200
        raise CustomConnectionException(f"HTTP {resp.status_code} when fetching {player_url}")

    sp = BeautifulSoup(resp.text, "html.parser")
    h2_tag = sp.find("h2")
    if h2_tag:
        try:
            player_name = h2_tag.get_text(strip=True)
            return player_name
        except:
            pass

    # Raise a CustomMissingException exception if no name was fetched
    raise CustomMissingException("No name was fetched")


def competition_from_filename(file_name: str) -> str:
    s = re.sub(r'[^a-z0-9]+', '-', file_name.lower())  # normalize to dashed tokens

    mapping = {
        ("mundialito", "club-world-cup", "clubworldcup", "mundial-clubes", "mundialclubes", ): "world/club-world-championship/357#id:69619",
        ("champions", "championsleague", "champions-league"): "europe/uefa-champions-league/7#id:76953",
        ('europaleague', 'europa-league', ): "europe/uefa-europa-league/679#id:76984",
        ('conference', 'conferenceleague', 'conference-league', ): "europe/uefa-europa-conference-league/17015#id:76960",
        ("eurocopa", "euro", "europa", "europeo", ): "europe/european-championship/1#id:56953",
        ("copaamerica", "copa-america", ): "south-america/copa-america/133#id:57114",
        ("mundial", "worldcup", "world-cup", ): "world/world-championship/16#id:58210",
        ("laliga", "la-liga", ): "spain/laliga/8#id:77559",
        ('premier', 'premier-league', 'premierleague', ): "england/premier-league/17#id:76986",
        ('seriea', 'serie-a', ): "italy/serie-a/23#id:76457",
        ('bundesliga', 'bundes-liga', 'bundes', ): "germany/bundesliga/35#id:77333",
        ('ligueone', 'ligue-one', 'ligue1', 'ligue-1', 'ligue', ): "france/ligue-1/34#id:77356",
        ("segunda", "segundadivision", "segunda-division", "laliga2", "la-liga-2", "la-liga-hypermotion", "hypermotion", "laligahypermotion", ): "spain/laliga-2/54#id:77558",
    }
    for keys, slug in mapping.items():
        for k in sorted(keys, key=len, reverse=True):  # longest first
            if k in s:
                return slug
    return "spain/laliga/8#id:77559"


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
        competition = competition_from_filename(file_name)
        competition_url = f"https://www.sofascore.com/tournament/football/{competition}"
        team_links = get_team_links_from_league(competition_url)
        # team_links = get_team_links_from_league(
        #     # "https://www.sofascore.com/tournament/football/world/club-world-championship/357#id:69619",
        #     "https://www.sofascore.com/tournament/football/spain/laliga/8#id:77559",
        #     # "https://www.sofascore.com/tournament/football/spain/laliga/8#52376",
        #     # "https://www.sofascore.com/tournament/football/europe/european-championship/1#id:56953",
        #     # "https://www.sofascore.com/tournament/football/south-america/copa-america/133#id:57114",
        # )
    # team_links = {
    #     '0': ['León', 'https://www.sofascore.com/team/football/club-leon/36534'],
    # }

    print()
    team_players_paths = dict()
    headers = pick_headers()

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

        # Try to parse JSON blob first
        script = soup.find("script", id="__NEXT_DATA__")
        if script and script.string:
            try:
                data = json.loads(script.string)
                players_list = (
                    data["props"]["pageProps"]["initialProps"]["players"]["players"]
                )
                for item in players_list:
                    p = item.get("player", {})
                    slug = p.get("slug")
                    pid = p.get("id")
                    if slug and pid:
                        player_paths_list.append(
                            f"https://www.sofascore.com/football/player/{slug}/{pid}"
                        )
            except (json.JSONDecodeError, KeyError, TypeError):
                pass

        # Fallback: scan <a> tags if JSON not found
        if not player_paths_list:
            for a_tag in soup.find_all("a", href=True):
                href_val = a_tag["href"]
                # if href_val.startswith("/player/"):
                if "/player/" in href_val:
                    # Construct absolute URL
                    full_url = href_val if href_val.startswith("http") else "https://www.sofascore.com" + href_val
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
            use_selenium = False
            use_proxies = False
            print('Extracting player data from: %s ...' % p)
            # 1) Attempt player name with timeouts + fallbacks
            timeout_retries = 3

            while timeout_retries > 0:
                def scrape_players_name_task(use_buffer=False):
                    """
                    1) Try to find the player > name via API.
                    2) If not found, try to find an <h2> (like your Selenium code: "(//h2)[1]").
                    """
                    if use_buffer:
                        time.sleep(0.25)
                    # player_name = ""

                    # Attempt #1: "player_name" via api
                    try:
                        player_name = get_player_name(p)
                        return player_name
                    except:
                        pass

                    # Attempt #2: "player_name" via Selenium
                    if use_selenium:
                        try:
                            player_name = get_player_name_selenium(p, use_proxies=use_proxies)
                            return player_name
                        except:
                            pass

                    # return player_name  # If all fails, return ""
                    # Raise a CustomMissingException exception if no name was fetched
                    raise CustomMissingException("No name was fetched")

                try:
                    player_name = run_with_timeout(MAX_WAIT_TIME, scrape_players_name_task)
                    print(player_name)
                    break
                except (CustomMissingException, CustomTimeoutException, CustomConnectionException, ReadTimeout, ReadTimeoutError, RemoteDisconnected) as e:
                    timeout_retries -= 1
                    if timeout_retries <= 0:
                        print("Failed to fetch name after several attempts.")
                        break
                    # Different behavior depending on the exception
                    if isinstance(e, CustomMissingException):
                        sleep_s = 0
                        reason = "element not found"
                        extra = ""
                        # use_selenium = True
                        use_proxies = True
                    elif isinstance(e, CustomTimeoutException):
                        sleep_s = 1
                        reason = "timeout"
                        extra = f"(waited {MAX_WAIT_TIME}s)"
                    else:
                        sleep_s = 2
                        reason = "connection"
                        extra = f"({type(e).__name__})"
                    print(
                        f"Retrying to fetch sofascore player rating ({p}) due to {reason} error {extra} "
                        f"({timeout_retries} retry left, waiting {sleep_s}s before next retry)"
                    )
                    time.sleep(sleep_s)

            if player_name != "":
                # 2) Attempt rating with timeouts + fallback
                average_rating = float(6.0)
                timeout_retries = 3

                while timeout_retries > 0:
                    def scrape_players_rating_task(use_buffer=False):
                        """
                        1) Try to find the <span role="meter" aria-valuenow="...">
                           (Summary last 12 months).
                        2) If not found, try to find "Average Sofascore Rating"
                           then look for the <span role="meter"> near it,
                           apply *0.95.
                        """
                        if use_buffer:
                            time.sleep(0.25)
                        average_rating = float(6.0)

                        # Attempt #1: "last-year-summary" via api
                        try:
                            average_rating = float(get_player_average_rating(p, use_proxies=use_proxies))
                            return average_rating
                        except:
                            pass

                        # # Attempt #2: "Summary (last 12 months)" via Selenium
                        # try:
                        #     average_rating = float(get_player_average_rating_selenium(p))
                        #     return average_rating
                        # except:
                        #     pass

                        # Attempt #3: "Average Sofascore Rating" fallback
                        # Find the rating of the last year he played
                        try:
                            average_rating = float(get_player_last_year_rating(p, use_proxies=use_proxies))
                            return average_rating
                        except:
                            pass

                        # # Attempt #4: "Average Sofascore Rating" fallback
                        # # Find the rating of the last tournament
                        # try:
                        #     average_rating = float(get_player_last_tournament_rating_selenium(p))
                        #     # average_rating = get_player_average_rating_selenium_short(p)
                        # except Exception as e:
                        #     # print(f"Error while getting average rating for player {p}: {e}")
                        #     # print(f"Exception type: {type(e).__name__}")
                        #     # import traceback
                        #     # traceback.print_exc()
                        #     pass

                        return average_rating  # If all fails, return 6.0

                    try:
                        average_rating = run_with_timeout(MAX_WAIT_TIME, scrape_players_rating_task)
                        print(average_rating)
                        break  # Break if successful
                    except (CustomMissingException, CustomTimeoutException, CustomConnectionException, ReadTimeout, ReadTimeoutError, RemoteDisconnected) as e:
                        timeout_retries -= 1
                        if timeout_retries <= 0:
                            print("Failed to fetch rating after several attempts.")
                            break
                        # Different behavior depending on the exception
                        if isinstance(e, CustomMissingException):
                            sleep_s = 0
                            reason = "element not found"
                            extra = ""
                            # use_selenium = True
                            use_proxies = True
                        elif isinstance(e, CustomTimeoutException):
                            sleep_s = 1
                            reason = "timeout"
                            extra = f"(waited {MAX_WAIT_TIME}s)"
                        else:
                            sleep_s = 2
                            reason = "connection"
                            extra = f"({type(e).__name__})"
                        print(
                            f"Retrying to fetch sofascore player rating ({p}) due to {reason} error {extra} "
                            f"({timeout_retries} retry left, waiting {sleep_s}s before next retry)"
                        )
                        time.sleep(sleep_s)
                if player_name != "":
                    player_name = find_manual_similar_string(player_name)
                    # players_ratings[player_name] = average_rating
                    players_ratings[player_name] = average_rating if average_rating != 0 else float(6.0)

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

# print(get_player_name("https://www.sofascore.com/es/football/player/vinicius-junior/868812"))
