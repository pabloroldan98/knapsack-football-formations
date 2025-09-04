import os
import re

import time
import pytz
import requests
import urllib3
from bs4 import BeautifulSoup
import json
import copy

from datetime import datetime, timezone
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC

from useful_functions import read_dict_data, overwrite_dict_data, find_manual_similar_string, \
    create_driver  # same as before

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))  # This is your Project Root


class JornadaPerfectaScraper:
    def __init__(self, competition: str = None):
        self.base_url = "https://www.jornadaperfecta.com"
        # # self.base_url = "https://www.jornadaperfecta.com/la-liga/onces-posibles" # No existe, sin nada = laliga
        # self.base_url = "https://www.jornadaperfecta.com/onces-posibles"
        # # self.base_url = "https://www.jornadaperfecta.com/mundial-de-clubes/onces-posibles"
        self.competition =  (
            competition
            if competition is not None
            else ""
        )
        self.session = requests.Session()
        self.driver = create_driver()
        self.wait = WebDriverWait(self.driver, 15)
        self.small_wait = WebDriverWait(self.driver, 5)
        # Use this custom headers dict when making GET requests
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/91.0.4472.124 Safari/537.36"
            )
        }

    def fetch_page(self, url):
        self.driver.get(url)

    def fetch_response(self, url):
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        response = self.session.get(url, headers=self.headers, verify=False)
        response.raise_for_status()
        return response.text

    def get_match_links(self):
        # 1) load the page
        # self.fetch_page(self.base_url)
        self.fetch_page(f"{self.base_url}{self.competition}/onces-posibles")

        # # 2) figure out which round to pick based on Europe/Madrid time
        # cet = pytz.timezone("Europe/Madrid")
        # now = datetime.now(cet)
        #
        # # thresholds are (round_value, cutoff_datetime)
        # thresholds = [
        #     ("1", datetime(2025, 6, 15, 2,  0, tzinfo=cet)),
        #     ("2", datetime(2025, 6, 19, 18, 0, tzinfo=cet)),
        #     ("3", datetime(2025, 6, 23, 21, 0, tzinfo=cet)),
        #     ("4", datetime(2025, 6, 28, 18, 0, tzinfo=cet)),
        #     ("5", datetime(2025, 7,  4, 21, 0, tzinfo=cet)),
        #     ("6", datetime(2025, 7,  8, 21, 0, tzinfo=cet)),
        #     ("7", datetime(2025, 7, 13, 21, 0, tzinfo=cet)),
        # ]
        #
        # round_to_select = None
        # for val, cutoff in thresholds:
        #     if now < cutoff:
        #         round_to_select = val
        #         break
        #
        # # 3) if we found one, click the dropdown and select it
        # select_el = self.wait.until(
        #     EC.element_to_be_clickable((By.ID, "roundSelect"))
        # )
        # select = Select(select_el)
        # available_values = [option.get_attribute("value") for option in select.options]
        # if round_to_select and round_to_select in available_values:
        #     select.select_by_value(round_to_select)
        #
        #     # wait for the new content to load (adjust timeout or condition as needed)
        #     self.wait.until(
        #         EC.presence_of_all_elements_located(
        #             (By.CSS_SELECTOR, "a.clean-link.match-link.current-round-content")
        #         )
        #     )
        # # else: no round selected, just use whatever initial page gave us

        # 3) wait for the updated links to appear
        link_els = self.wait.until(
            EC.presence_of_all_elements_located(
                (By.CSS_SELECTOR, "a.clean-link.match-link.current-round-content")
            )
        )

        # 4) extract hrefs, preserving HTML order and de-duplicating
        links = []
        for el in link_els:
            href = el.get_attribute("href")
            links.append(href)
        links = list(set(links))
        # # WE DO NOT USE THIS BECAUSE IT IS BETTER THE ORDER IT HAS IN THE HTML
        # links = sorted(
        #     list(set(links)),
        #     key=lambda u: int(u.split('/')[3])
        # )
        return links

    def parse_match_page(self, match_url):
        """
        Returns a dict of the form:
          {
            "Team A": {
               "Starter 1": 0.60,
               "Alt Candidate": 0.25,
               ...
            },
            "Team B": { ... }
          }
        """
        html = self.fetch_response(match_url)
        soup = BeautifulSoup(html, "html.parser")

        lineup_data = {}

        # 1) Loop over each team block
        # for team_block in soup.find_all(class_="partido-posible-alineacion"):
        for team_block in soup.find_all(class_="escudo-equipo-alineacion"):
            try:
                # # Extract and clean team name
                # full_text = team_block.get_text(separator=" ", strip=True)
                # # Assumes text starts with "Alineación Posible <TeamName>"
                # team_name = full_text.replace("Alineación Posible ", "").strip().title()
                img_tag = team_block.find("img")
                team_name = img_tag["title"].strip().title() if img_tag and img_tag.has_attr("title") else None
                team_name = find_manual_similar_string(team_name)

                players = {}
                # climb up two levels: div → div → div
                team_container = team_block.parent.parent
                # 2) For each performer (possible starter)
                for performer in team_container.find_all(attrs={"itemprop": "performer"}):
                    # a) Starter name
                    name_tag = performer.find(attrs={"itemprop": "name"})
                    starter_name = name_tag.find("a").get_text(strip=True).strip().title()
                    starter_name = find_manual_similar_string(starter_name)

                    # b) Starter probability
                    pct = performer.find(class_="percent-budget")
                    alternatives = performer.find_all(class_="alternative")
                    status = performer.find(class_="status")
                    if pct and pct.get_text(strip=True).isdigit():
                        starter_prob = float(pct.get_text(strip=True)) / 100.0
                    else:
                        starter_prob = 0.7 if alternatives or status else 0.8

                    players[starter_name] = starter_prob

                    # 3) Check for alternative inside this performer
                    for alt in alternatives:
                        # e.g. "Player X 35%"
                        alt_text = alt.get_text(strip=True)
                        parts = alt_text.rsplit(" ", 1)
                        alt_name = parts[0].strip().title()
                        alt_name = find_manual_similar_string(alt_name)
                        alt_pct = parts[1].rstrip("%")
                        try:
                            alt_prob = float(alt_pct) / 100.0
                        except ValueError:
                            alt_prob = 0.2
                        players[alt_name] = alt_prob

                lineup_data[team_name] = players
            except:
                pass

        return lineup_data

    def scrape_teams_probabilities(self):
        """
        1) Grab the classification page and find all team links.
        2) For each team link, parse the lineup data.
        3) Merge them all into a single dictionary.
        """
        # # TEAMS_PAGE = "https://www.jornadaperfecta.com/mundial-de-clubes/clasificacion/"
        # TEAMS_PAGE = "https://www.jornadaperfecta.com/clasificacion/"
        TEAMS_PAGE = f"{self.base_url}{self.competition}/clasificacion/"
        html = self.fetch_response(TEAMS_PAGE)
        soup = BeautifulSoup(html, "html.parser")

        # 1) Find all <a> tags whose href begins with the team prefix
        # # prefix = "https://www.jornadaperfecta.com/mundial-de-clubes/equipo/"
        # prefix = "https://www.jornadaperfecta.com/equipo/"
        prefix = f"{self.base_url}{self.competition}/equipo/"
        team_links = {
            a["href"]
            for a in soup.find_all("a", href=True)
            if a["href"].startswith(prefix)
        }

        probabilities_dict = {}

        for url in team_links:
            match_data = self.parse_match_page(url)
            # Merge match_data into probabilities_dict
            for team_name, players in match_data.items():
                if team_name not in probabilities_dict:
                    probabilities_dict[team_name] = {}
                for player_name, chance_val in players.items():
                    probabilities_dict[team_name][player_name] = chance_val

        return probabilities_dict

    def scrape_matches_probabilities(self, probabilities_dict=None):
        """
        1) Grab the main page, find all partido links.
        2) For each match link, parse the chance / team / player data.
        3) Merge them all into a single dictionary.
        """
        if not probabilities_dict:
            probabilities_dict = {}

        match_links = self.get_match_links()

        for url in match_links:
            match_data = self.parse_match_page(url)
            # Merge match_data into probabilities_dict
            for team_name, players in match_data.items():
                if team_name not in probabilities_dict:
                    probabilities_dict[team_name] = {}
                for player_name, chance_val in players.items():
                    probabilities_dict[team_name][player_name] = chance_val

        return probabilities_dict

    def scrape_probabilities(self):
        """
        1) Get data from all teams
        2) Get data from all matches
        3) Merge them all into a single dictionary.
        """

        teams_probabilities_dict = self.scrape_teams_probabilities()
        matches_probabilities_dict = self.scrape_matches_probabilities(teams_probabilities_dict)
        probabilities_dict = copy.deepcopy(matches_probabilities_dict)

        return probabilities_dict

    def scrape_market(self):
        # self.fetch_page("https://www.jornadaperfecta.com/mercado/")
        self.fetch_page(f"{self.base_url}{self.competition}/mercado/")

        try:
            # 1. Wait for the select element to be present
            select_elem = self.wait.until(EC.presence_of_element_located((By.ID, "platformSelect")))
            select = Select(select_elem)
            # 2. Try to select "LaLiga Fantasy" by visible text
            try:
                select.select_by_visible_text("LaLiga Fantasy")
            except:
                # If not found, fallback to value=2
                select.select_by_value("2")
        except:
            pass

        # 3. Wait for the content to update (can wait for a known container of the market)
        self.wait.until(EC.presence_of_element_located((By.TAG_NAME, "script")))
        # 4. Get updated HTML and return
        html_page = self.driver.page_source
        soup = BeautifulSoup(html_page, "html.parser")

        script_tags = soup.find_all("script", {"type": "text/javascript"})
        market_data = None
        for script in script_tags:
            if script.string and "marketCaching=" in script.string:
                # Extract the JSON-like string
                match = re.search(r"marketCaching\s*=\s*(\[\{.*?\}\]);", script.string, re.DOTALL)
                if match:
                    json_str = match.group(1)
                    try:
                        market_data = json.loads(json_str)
                    except json.JSONDecodeError as e:
                        print("JSON decode error:", e)
                        return {}, {}, {}, {}
                break
        if not market_data:
            return {}, {}, {}, {}

        prices_dict = {}
        positions_dict = {}
        forms_dict = {}
        price_trends_dict = {}

        positions_normalize = {
            "portero": "GK",
            "defensa": "DEF",
            "mediocentro": "MID",
            "delantero": "ATT",
        }

        for player in market_data:
            team_name = player.get("team")
            team_name = team_name.strip().title() if team_name else team_name
            team_name = find_manual_similar_string(team_name)
            player_name = player.get("name").strip().title()
            player_name = player_name.strip().title() if player_name else player_name
            player_name = find_manual_similar_string(player_name)
            price = player.get("price")
            position = player.get("position")
            position_name = positions_normalize.get(position)
            price_trend = player.get("lastMarkets", {}).get("1")

            # Ensure price and price_trend are numeric
            try:
                price = float(price) if price is not None else None
                price_trend = float(price_trend) if price_trend is not None else None
            except ValueError:
                price = None
                price_trend = None

            # Initialize nested dicts if necessary
            if team_name and player_name:
                if team_name not in prices_dict:
                    prices_dict[team_name] = {}
                    positions_dict[team_name] = {}
                    forms_dict[team_name] = {}
                    price_trends_dict[team_name] = {}

                # Assign values
                prices_dict[team_name][player_name] = price
                positions_dict[team_name][player_name] = position_name
                price_trends_dict[team_name][player_name] = price_trend

                # Compute form
                if price and price_trend and price != price_trend:
                    try:
                        form = ((price / (price - price_trend)) - 1) * 100
                    except ZeroDivisionError:
                        form = None
                else:
                    form = None
                forms_dict[team_name][player_name] = form

        return prices_dict, positions_dict, forms_dict, price_trends_dict


    def scrape(self):

        prices_dict, positions_dict, forms_dict, price_trends_dict = self.scrape_market()
        start_probabilities_data = self.scrape_probabilities()

        return prices_dict, positions_dict, forms_dict, start_probabilities_data, price_trends_dict


def competition_from_filename(file_name: str) -> str:
    s = re.sub(r'[^a-z0-9]+', '-', file_name.lower())  # normalize to dashed tokens

    mapping = {
        ("mundialito", "club-world-cup", "clubworldcup", "mundial-clubes", "mundialclubes", ): "mundial-de-clubes",
        ("champions", "championsleague", "champions-league"): "champions-league",
        ('europaleague', 'europa-league', ): "europa-league",
        ('conference', 'conferenceleague', 'conference-league', ): "conference-league",
        ("eurocopa", "euro", "europa", "europeo", ): "eurocopa",
        ("copaamerica", "copa-america", ): "copa-america",
        ("mundial", "worldcup", "world-cup", ): "mundial",
        ("laliga", "la-liga", ): "",
        ('premier', 'premier-league', 'premierleague', ): "premier",
        ('seriea', 'serie-a', ): "seriea",
        ('bundesliga', 'bundes-liga', 'bundes', ): "bundesliga",
        ('ligueone', 'ligue-one', 'ligue1', 'ligue-1', 'ligue', ): "ligue-1",
        ('segundadivision', 'segunda-division', 'segunda', 'laliga2', 'la-liga2', 'la-liga-2', 'hypermotion', 'la-liga-hypermotion', 'laligahypermotion', ): "segunda",
    }
    for keys, slug in mapping.items():
        for k in sorted(keys, key=len, reverse=True):  # longest first
            if k in s:
                return "/" + slug if slug else slug
    return ""


def get_jornadaperfecta_data(
        price_file_name="jornadaperfecta_prices",
        positions_file_name="jornadaperfecta_positions",
        forms_file_name="jornadaperfecta_forms",
        start_probability_file_name="jornadaperfecta_start_probabilities",
        price_trends_file_name="jornadaperfecta_price_trends",
        force_scrape=False
):
    # If not forced to scrape, attempt to read from local file
    if not force_scrape:
        prices_data = read_dict_data(price_file_name)
        positions_data = read_dict_data(positions_file_name)
        forms_data = read_dict_data(forms_file_name)
        start_probabilities_data = read_dict_data(start_probability_file_name)
        price_trends_data = read_dict_data(price_trends_file_name)

        if prices_data and positions_data and forms_data and start_probabilities_data and price_trends_data:
            return prices_data, positions_data, forms_data, start_probabilities_data, price_trends_data

    # Otherwise, scrape fresh data
    competition = competition_from_filename(start_probability_file_name)
    scraper = JornadaPerfectaScraper(competition=competition)
    prices_data, positions_data, forms_data, start_probabilities_data, price_trends_data = scraper.scrape()

    # Save to file for next time
    overwrite_dict_data(prices_data, price_file_name)
    overwrite_dict_data(positions_data, positions_file_name)
    overwrite_dict_data(forms_data, forms_file_name)
    overwrite_dict_data(start_probabilities_data, start_probability_file_name, ignore_old_data=True)
    overwrite_dict_data(price_trends_data, price_trends_file_name)

    return prices_data, positions_data, forms_data, start_probabilities_data, price_trends_data


def get_players_prices_dict_jornadaperfecta(
        file_name="jornadaperfecta_prices",
        force_scrape=False
):
    if not force_scrape:
        data = read_dict_data(file_name)
        if data:
            return data

    competition = competition_from_filename(file_name)
    scraper = JornadaPerfectaScraper(competition=competition)
    result, _, _, _, _ = scraper.scrape()

    overwrite_dict_data(result, file_name)

    return result


def get_players_positions_dict_jornadaperfecta(
        file_name="jornadaperfecta_positions",
        force_scrape=False
):
    if not force_scrape:
        data = read_dict_data(file_name)
        # if data:
        return data

    competition = competition_from_filename(file_name)
    scraper = JornadaPerfectaScraper(competition=competition)
    _, result, _, _, _ = scraper.scrape()

    overwrite_dict_data(result, file_name)

    return result


def get_players_forms_dict_jornadaperfecta(
        file_name="jornadaperfecta_forms",
        force_scrape=False
):
    if not force_scrape:
        data = read_dict_data(file_name)
        if data:
            return data

    competition = competition_from_filename(file_name)
    scraper = JornadaPerfectaScraper(competition=competition)
    _, _, result, _, _ = scraper.scrape()

    overwrite_dict_data(result, file_name)

    return result


def get_players_start_probabilities_dict_jornadaperfecta(
        file_name="jornadaperfecta_start_probabilities",
        force_scrape=False
):
    if not force_scrape:
        data = read_dict_data(file_name)
        if data:
            return data

    competition = competition_from_filename(file_name)
    scraper = JornadaPerfectaScraper(competition=competition)
    # _, _, _, result, _ = scraper.scrape()
    result = scraper.scrape_probabilities()

    overwrite_dict_data(result, file_name, ignore_old_data=True)

    return result


def get_players_price_trends_dict_jornadaperfecta(
        file_name="jornadaperfecta_price_trends",
        force_scrape=False
):
    if not force_scrape:
        data = read_dict_data(file_name)
        if data:
            return data

    competition = competition_from_filename(file_name)
    scraper = JornadaPerfectaScraper(competition=competition)
    _, _, _, _, result = scraper.scrape()

    overwrite_dict_data(result, file_name)

    return result


# # Example usage:
# prices, positions, forms, start_probabilities, price_trends = get_jornadaperfecta_data(
#     price_file_name="test_jornadaperfecta_laliga_players_prices",
#     positions_file_name="test_jornadaperfecta_laliga_players_positions",
#     forms_file_name="test_jornadaperfecta_laliga_players_forms",
#     start_probability_file_name="test_jornadaperfecta_laliga_players_start_probabilities",
#     price_trends_file_name="test_jornadaperfecta_laliga_players_price_trends",
#     force_scrape=True
# )
#
# print("Prices:")
# for team, players in prices.items():
#     print(team, players)
# print("\nPositions:")
# for team, players in positions.items():
#     print(team, players)
# print("\nForms:")
# for team, players in forms.items():
#     print(team, players)
# print("\nStart Probabilities:")
# for team, players in start_probabilities.items():
#     print(team, players)
# print("\nPrice Trends:")
# for team, players in price_trends.items():
#     print(team, players)
