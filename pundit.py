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


class PunditScraper:
    def __init__(self): #, competition: str = None):
        self.base_url = "https://www.fantasyfootballpundit.com"
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
                'Mozilla/5.0 (Platform; Security; OS-or-CPU; Localization; rv:1.4) Gecko/20030624 Netscape/7.1 (ax)'
                # "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                # "AppleWebKit/537.36 (KHTML, like Gecko) "
                # "Chrome/91.0.4472.124 Safari/537.36"
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
        - Find every team block via h2[id$="-team-news"]
        - Team name = h2.text with "Predicted Lineup" removed (case-insensitive), stripped
        - Scope = the block (div>div>h2 -> first div)
        - Parse tables with class 'has-fixed-layout'
        - Each tbody>tr is a player row: first td = name; span inside class*="fpl-colored-percent" = probability
        - Probabilities stored as float (0.6 for "60%")
        """
        teams_page = f"{self.base_url.rstrip('/')}/fantasy-premier-league-team-news/"
        html = self.fetch_response(teams_page)
        soup = BeautifulSoup(html, "html.parser")

        def pct_to_float(txt):
            if not txt:
                return None
            m = re.search(r'(\d+(?:\.\d+)?)\s*%', txt)
            if not m:
                return None
            return float(m.group(1)) / 100.0

        probabilities = {}

        for h2 in soup.select('h2[id$="-team-news"]'):
            raw_team_name = h2.get_text(strip=True)
            # Remove "Predicted Lineup" (case insensitive)
            team_name = re.sub(r'predicted\s*lineup', '', raw_team_name, flags=re.I).strip()
            if not team_name:
                continue

            # Per structure: div>div>h2, we want the first div (two levels up)
            team_block = None
            if h2.parent and h2.parent.name == "div" and h2.parent.parent and h2.parent.parent.name == "div":
                team_block = h2.parent.parent
            else:
                team_block = h2.find_parent("div")

            if team_block is None:
                continue

            team_players = {}

            for tbl in team_block.select("table.has-fixed-layout"):
                tbody = tbl.find("tbody")
                if not tbody:
                    continue

                for tr in tbody.find_all("tr"):
                    tds = tr.find_all("td")
                    if not tds:
                        continue

                    # player_name = tds[0].get_text(strip=True)
                    raw_name = tds[0].get_text(" ", strip=True)  # join text nodes with a real space
                    player_name = normalize_whitespace(raw_name)
                    if not player_name:
                        continue

                    pct_el = tds[-1]#.find("span")
                    pct_text = pct_el.get_text(strip=True) if pct_el else ""
                    prob = pct_to_float(pct_text)

                    if prob is not None:
                        player_name = find_manual_similar_string(player_name)
                        team_players[player_name] = prob

            if team_players:
                probabilities[team_name] = team_players

        return probabilities


    def scrape(self):

        # prices_dict, positions_dict, forms_dict, price_trends_dict = self.scrape_market()
        start_probabilities_data = self.scrape_probabilities()

        # return prices_dict, positions_dict, forms_dict, start_probabilities_data, price_trends_dict
        return start_probabilities_data


def get_pundit_data(
        start_probability_file_name="pundit_start_probabilities",
        force_scrape=False
):
    # If not forced to scrape, attempt to read from local file
    if not force_scrape:
        start_probabilities_data = read_dict_data(start_probability_file_name)

        if start_probabilities_data:
            return start_probabilities_data

    # Otherwise, scrape fresh data
    scraper = PunditScraper()
    start_probabilities_data = scraper.scrape()

    # Save to file for next time
    overwrite_dict_data(start_probabilities_data, start_probability_file_name, ignore_old_data=True)

    # return prices_data, positions_data, forms_data, start_probabilities_data, price_trends_data
    return start_probabilities_data


def get_players_start_probabilities_dict_pundit(
        file_name="pundit_start_probabilities",
        force_scrape=False
):
    if not force_scrape:
        data = read_dict_data(file_name)
        if data:
            return data

    scraper = PunditScraper()
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


# # Example usage:
# start_probabilities = get_pundit_data(
#     start_probability_file_name="test_pundit_premier_players_start_probabilities",
#     force_scrape=True
# )
#
# print("\nStart Probabilities:")
# for team, players in start_probabilities.items():
#     print(team, players)
