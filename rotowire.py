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


class RotowireScraper:
    def __init__(self, competition: str = None):
        self.base_url = "https://www.rotowire.com/soccer/lineups.php?"
        self.competition =  (
            competition
            if competition is not None
            else ""
        )
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
        Returns:
        {
          "Team A": {"Player 1": 1.0/0.8/0.2/0.0, ...},
          "Team B": {...},
          ...
        }
        """
        url = f"{self.base_url.rstrip('/')}league={self.competition}"
        html = self.fetch_response(url)
        soup = BeautifulSoup(html, "html.parser")

        probabilities = {}

        # 1) iterate matches by box
        for match in soup.select(".lineup__box"):
            # 2) team names
            home_team_el = match.select_one(".lineup__mteam.is-home")
            away_team_el = match.select_one(".lineup__mteam.is-visit")
            home_team = (home_team_el.get_text(strip=True) if home_team_el else "").strip()
            away_team = (away_team_el.get_text(strip=True) if away_team_el else "").strip()
            if not home_team and not away_team:
                continue

            # 3) get team player containers
            home_list = match.select_one(".lineup__list.is-home")
            away_list = match.select_one(".lineup__list.is-visit")

            # 4) lineup status (default predicted)
            def status_from_scope(team_el):
                # Get status from team_el; default Predicted
                txt = ""
                if team_el:
                    el = team_el.select_one('[class*="lineup__status"]')
                    if el:
                        txt = el.get_text(strip=True)
                if "Predicted" in txt:
                    return "Predicted Lineup"
                if "Confirmed" in txt:
                    return "Confirmed Lineup"
                if "Unknown" in txt:
                    return "Unknown Lineup"
                return "Predicted Lineup"

            home_status = status_from_scope(home_list)
            away_status = status_from_scope(away_list)

            # helper (inline logic, no extra functions): extract player nodes from a list container
            def player_nodes(list_el):
                return list_el.select(".lineup__player") if list_el else []

            home_players = player_nodes(home_list)
            away_players = player_nodes(away_list)

            # 5) scoring rules
            # First handle bench (players after first 11), then starters (first 11) so starters overwrite
            def assign_team_probs(team_name, nodes, team_status):
                team_name = find_manual_similar_string(team_name)
                if not team_name:
                    return
                team_dict = probabilities.setdefault(team_name, {})

                # bench first
                for node in nodes[11:]:
                    a = node.select_one("a")
                    player_name = (a.get("title", "").strip() if a else "").strip() or (a.get_text(strip=True) if a else node.get_text(strip=True))
                    player_name = find_manual_similar_string(player_name)
                    inj_el = node.select_one(".lineup__inj")
                    inj = (inj_el.get_text(strip=True) if inj_el else "").strip().upper()
                    # base 0.2
                    prob = 0.2
                    if inj == "OUT":
                        prob = 0.0
                    elif inj == "SUS":
                        prob = 0.0
                    elif inj == "QUES":
                        prob = 0.2
                    team_dict.setdefault(player_name, prob)

                # starters last (first 11)
                for node in nodes[:11]:
                    a = node.select_one("a")
                    player_name = (a.get("title", "").strip() if a else "").strip() or (a.get_text(strip=True) if a else node.get_text(strip=True))
                    player_name = find_manual_similar_string(player_name)
                    inj_el = node.select_one(".lineup__inj")
                    inj = (inj_el.get_text(strip=True) if inj_el else "").strip().upper()

                    if team_status == "Confirmed Lineup":
                        prob = 1.0
                    elif team_status == "Unknown Lineup":
                        # treat starters as bench rules
                        prob = 0.2
                        if inj == "OUT":
                            prob = 0.0
                        elif inj == "SUS":
                            prob = 0.0
                        elif inj == "QUES":
                            prob = 0.2
                    else:
                        # Predicted Lineup
                        prob = 0.8
                        if inj == "OUT":
                            prob = 0.4
                        elif inj == "QUES":
                            prob = 0.5

                    team_dict[player_name] = prob  # overwrite any bench default

            assign_team_probs(home_team, home_players, home_status)
            assign_team_probs(away_team, away_players, away_status)

        return probabilities


    def scrape(self):

        # prices_dict, positions_dict, forms_dict, price_trends_dict = self.scrape_market()
        start_probabilities_data = self.scrape_probabilities()

        # return prices_dict, positions_dict, forms_dict, start_probabilities_data, price_trends_dict
        return start_probabilities_data


def competition_from_filename(file_name: str) -> str:
    s = re.sub(r'[^a-z0-9]+', '-', file_name.lower())  # normalize to dashed tokens

    mapping = {
        ("mundialito", "club-world-cup", "clubworldcup", "mundial-clubes", "mundialclubes", ): "FCWC",
        ("champions", "championsleague", "champions-league"): "UCL",
        ('europaleague', 'europa-league', ): "UEL",
        ('conference', 'conferenceleague', 'conference-league', ): "UECL",
        ("eurocopa", "euro", "europa", "europeo", ): "UEC",
        ("copaamerica", "copa-america", ): "CCA",
        ("mundial", "worldcup", "world-cup", ): "FWC",
        ("laliga", "la-liga", ): "LIGA",
        ('premier', 'premier-league', 'premierleague', ): "EPL",
        ('seriea', 'serie-a', ): "SERI",
        ('bundesliga', 'bundes-liga', 'bundes', ): "BUND",
        ('ligueone', 'ligue-one', 'ligue1', 'ligue-1', 'ligue', ): "FRAN",
        ('segunda', 'segundadivision', 'segunda-division', 'laliga2', 'la-liga2', 'la-liga-2', 'hypermotion', 'la-liga-hypermotion', 'laligahypermotion', ): "LIGA2",
    }
    for keys, slug in mapping.items():
        for k in sorted(keys, key=len, reverse=True):  # longest first
            if k in s:
                return slug
    return ""


def get_rotowire_data(
        start_probability_file_name="rotowire_start_probabilities",
        force_scrape=False
):
    # If not forced to scrape, attempt to read from local file
    if not force_scrape:
        start_probabilities_data = read_dict_data(start_probability_file_name)

        if start_probabilities_data:
            return start_probabilities_data

    # Otherwise, scrape fresh data
    competition = competition_from_filename(start_probability_file_name)
    scraper = RotowireScraper(competition=competition)
    start_probabilities_data = scraper.scrape()

    # Save to file for next time
    overwrite_dict_data(start_probabilities_data, start_probability_file_name, ignore_old_data=True)

    # return prices_data, positions_data, forms_data, start_probabilities_data, price_trends_data
    return start_probabilities_data


def get_players_start_probabilities_dict_rotowire(
        file_name="rotowire_start_probabilities",
        force_scrape=False
):
    if not force_scrape:
        data = read_dict_data(file_name)
        if data:
            return data

    competition = competition_from_filename(file_name)
    scraper = RotowireScraper(competition=competition)
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
# start_probabilities = get_rotowire_data(
#     start_probability_file_name="test_rotowire_champions_players_start_probabilities",
#     force_scrape=True
# )
#
# print("\nStart Probabilities:")
# for team, players in start_probabilities.items():
#     print(team, players)
