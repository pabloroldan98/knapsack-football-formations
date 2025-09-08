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


class ScoutScraper:
    def __init__(self): #, competition: str = None):
        self.base_url = "https://www.fantasyfootballscout.co.uk"
        # self.competition =  (
        #     competition
        #     if competition is not None
        #     else ""
        # )
        self.session = requests.Session()
        # self.driver = create_driver()
        # self.wait = WebDriverWait(self.driver, 15)
        # self.small_wait = WebDriverWait(self.driver, 5)
        # Use this custom headers dict when making GET requests
        self.headers = {
            "User-Agent": (
                # 'Mozilla/5.0 (Platform; Security; OS-or-CPU; Localization; rv:1.4) Gecko/20030624 Netscape/7.1 (ax)'
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/91.0.4472.124 Safari/537.36"
            )
        }

    # def fetch_page(self, url):
    #     self.driver.get(url)

    def fetch_response(self, url):
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        response = self.session.get(url, headers=self.headers, verify=False)
        response.raise_for_status()
        return response.text

    def scrape_probabilities(self):
        """
        - Team blocks: elements with class "team-news-item"
        - Team name: text of element with class "team-badge"
        - Players:
            * Elements whose class contains "player-name" => prob = 0.8
            * <li> that contain a <span> with class containing "doubt-percent":
                - name = li text (minus the span text)
                - prob = span text like "75%" -> 0.75
        """
        teams_page = f"{self.base_url.rstrip('/')}/team-news"
        html = self.fetch_response(teams_page)
        soup = BeautifulSoup(html, "html.parser")

        def pct_to_float(txt):
            if not txt:
                return None
            m = re.search(r'(\d+(?:\.\d+)?)\s*%', txt)
            return float(m.group(1)) / 100.0 if m else None

        probabilities = {}

        for team_block in soup.select(".team-news-item"):
            badge_el = team_block.select_one(".team-badge")
            team_name = normalize_whitespace(badge_el.get_text(" ", strip=True)) if badge_el else ""
            if not team_name:
                continue

            team_players = {}

            # 1) Players with implicit 80% probability
            for name_el in team_block.select('[class*="player-name"]'):
                raw_name = name_el.get_text(" ", strip=True)
                player_name = normalize_whitespace(raw_name)
                player_name = re.sub(r'\([^)]*\)', '', player_name).strip()
                if not player_name:
                    continue
                player_name = find_manual_similar_string(player_name)
                team_players[player_name] = 0.8  # will be overridden if explicit % is found later

            # 2) Doubt list players with explicit percent
            for players_ul in team_block.select('ul.players'):
                for li in players_ul.find_all("li"):
                    span = li.select_one('[class="doubt-percent"]')
                    if not span:
                        continue

                    pct_text = span.get_text(strip=True)
                    prob = pct_to_float(pct_text)
                    if prob is None:
                        continue

                    li_text = li.get_text(" ", strip=True)
                    # Remove the percent text from the li text to leave just the name
                    name_text = normalize_whitespace(li_text.replace(pct_text, ""))
                    if not name_text:
                        continue

                    player_name = find_manual_similar_string(name_text)
                    player_name = re.sub(r'\([^)]*\)', '', player_name).strip()
                    team_players[player_name] = prob  # override 0.8 if already set

            if team_players:
                team_name = find_manual_similar_string(team_name)
                probabilities[team_name] = team_players

        return probabilities


    def scrape(self):

        # prices_dict, positions_dict, forms_dict, price_trends_dict = self.scrape_market()
        start_probabilities_data = self.scrape_probabilities()

        # return prices_dict, positions_dict, forms_dict, start_probabilities_data, price_trends_dict
        return start_probabilities_data


def get_scout_data(
        start_probability_file_name="scout_start_probabilities",
        force_scrape=False
):
    # If not forced to scrape, attempt to read from local file
    if not force_scrape:
        start_probabilities_data = read_dict_data(start_probability_file_name)

        if start_probabilities_data:
            return start_probabilities_data

    # Otherwise, scrape fresh data
    scraper = ScoutScraper()
    start_probabilities_data = scraper.scrape()

    # Save to file for next time
    overwrite_dict_data(start_probabilities_data, start_probability_file_name, ignore_old_data=True)

    # return prices_data, positions_data, forms_data, start_probabilities_data, price_trends_data
    return start_probabilities_data


def get_players_start_probabilities_dict_scout(
        file_name="scout_start_probabilities",
        force_scrape=False
):
    if not force_scrape:
        data = read_dict_data(file_name)
        if data:
            return data

    scraper = ScoutScraper()
    result = scraper.scrape_probabilities()

    overwrite_dict_data(result, file_name, ignore_old_data=True)

    return result


def normalize_whitespace(s: str) -> str:
    if not s:
        return ""
    space_class = r'[\u00A0\u1680\u2000-\u200A\u202F\u205F\u3000]'  # common Unicode spaces
    # remove soft hyphen and word joiner if they show up
    s = s.replace("\u00AD", "").replace("\u2060", "")
    # turn all special spaces into a normal space
    s = re.sub(space_class, " ", s)
    # collapse any runs of spaces/tabs/newlines
    s = re.sub(r"\s+", " ", s, flags=re.UNICODE).strip()
    return s


# Example usage:
start_probabilities = get_scout_data(
    start_probability_file_name="test_scout_premier_players_start_probabilities",
    force_scrape=True
)

print("\nStart Probabilities:")
for team, players in start_probabilities.items():
    print(team, players)
