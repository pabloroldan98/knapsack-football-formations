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


class SportsgamblerScraper:
    def __init__(self, competition: str = None):
        self.base_url = "https://www.sportsgambler.com/lineups"
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
        url = f"{self.base_url.rstrip('/')}/football/{self.competition}/"
        html = self.fetch_response(url)
        soup = BeautifulSoup(html, "html.parser")

        probabilities = {}

        # 1) container with all current matches
        container = soup.select_one(".content-block.team-news-container")
        if not container:
            return probabilities

        # 2) collect lineup IDs from lineup rows
        lineup_rows = container.select(".lineup-row")
        ids = []
        for row in lineup_rows:
            btn_wrap = row.select_one(".fxs-btn")
            if not btn_wrap:
                continue
            a = btn_wrap.select_one("a[id]")
            if not a:
                continue
            lid = a.get("id", "").strip()
            if lid:
                ids.append(lid)

        # 3) for each id, fetch the injected lineup fragment
        for lid in ids:
            match_url = f"{self.base_url}/lineups-load.php?id={lid}"
            frag_html = self.fetch_response(match_url)
            frag = BeautifulSoup(frag_html, "html.parser")

            # 4) team names & status from first/second h3
            h3s = frag.select("h3")
            home_h3 = h3s[0].get_text(strip=True) if len(h3s) >= 1 else ""
            away_h3 = h3s[1].get_text(strip=True) if len(h3s) >= 2 else ""

            def split_name_and_status(htext):
                if "Confirmed Lineup" in htext:
                    return htext.split("Confirmed Lineup", 1)[0].rstrip(), "Confirmed"
                if "Predicted Lineup" in htext:
                    return htext.split("Predicted Lineup", 1)[0].rstrip(), "Predicted"
                return htext, "Unknown"

            home_team, home_status = split_name_and_status(home_h3)
            away_team, away_status = split_name_and_status(away_h3)

            # strip trailing "Predicted Lineup" / "Confirmed Lineup" from team names
            for token in ("Predicted Lineup", "Confirmed Lineup"):
                if token in home_team:
                    home_team = home_team.split(token, 1)[0].rstrip()
                if token in away_team:
                    away_team = away_team.split(token, 1)[0].rstrip()

            # 5) main XI lists
            home_list = frag.select_one('[class*="lineups-home"]')
            away_list = frag.select_one('[class*="lineups-away"]')

            # collect starters (player-name texts)
            def add_starters(team_name, team_list, status):
                team_name = find_manual_similar_string(team_name)
                if not team_name or not team_list:
                    return
                team_dict = probabilities.setdefault(team_name, {})
                starters = team_list.select(".player-name")
                base_prob = 1.0 if status == "Confirmed" else (0.8 if status == "Predicted" else 0.8)
                for i, el in enumerate(starters):
                    if i < 11:
                        player_name = el.get_text(strip=True)
                        player_name = find_manual_similar_string(player_name)
                        team_dict[player_name] = base_prob

            add_starters(home_team, home_list, home_status)
            add_starters(away_team, away_list, away_status)

            # 6) bench lists (teams-item -> first = home, second = away)
            teams_items = frag.select(".teams-item")
            if teams_items:
                # home bench
                home_bench = teams_items[0] if len(teams_items) >= 1 else None
                if home_bench and home_team:
                    team_dict = probabilities.setdefault(home_team, {})
                    for sp in home_bench.select(".sub-player"):
                        player_name = sp.get_text(strip=True)
                        sp_no = sp.select_one(".sub-player-no")
                        if sp_no:
                            no_txt = sp_no.get_text(strip=True)
                            # delete only the first instance
                            if no_txt and no_txt in player_name:
                                player_name = player_name.replace(no_txt, "", 1).strip()
                        # bench → 0
                        player_name = find_manual_similar_string(player_name)
                        team_dict.setdefault(player_name, 0.0)

                # away bench
                away_bench = teams_items[1] if len(teams_items) >= 2 else None
                if away_bench and away_team:
                    team_dict = probabilities.setdefault(away_team, {})
                    for sp in away_bench.select(".sub-player"):
                        player_name = sp.get_text(strip=True)
                        sp_no = sp.select_one(".sub-player-no")
                        if sp_no:
                            no_txt = sp_no.get_text(strip=True)
                            if no_txt and no_txt in player_name:
                                player_name = player_name.replace(no_txt, "", 1).strip()
                        player_name = find_manual_similar_string(player_name)
                        team_dict.setdefault(player_name, 0.0)

        return probabilities


    def scrape(self):

        # prices_dict, positions_dict, forms_dict, price_trends_dict = self.scrape_market()
        start_probabilities_data = self.scrape_probabilities()

        # return prices_dict, positions_dict, forms_dict, start_probabilities_data, price_trends_dict
        return start_probabilities_data


def competition_from_filename(file_name: str) -> str:
    s = re.sub(r'[^a-z0-9]+', '-', file_name.lower())  # normalize to dashed tokens

    mapping = {
        ("mundialito", "club-world-cup", "clubworldcup", "mundial-clubes", "mundialclubes", ): "fifa-club-world-cup",
        ("champions", "championsleague", "champions-league"): "uefa-champions-league",
        ('europaleague', 'europa-league', ): "uefa-europa-league",
        ('conference', 'conferenceleague', 'conference-league', ): "uefa-europa-conference-league",
        ("eurocopa", "euro", "europa", "europeo", ): "uefa-european-championship",
        ("copaamerica", "copa-america", ): "conmebol-copa-america",
        ("mundial", "worldcup", "world-cup", ): "fifa-world-cup",
        ("laliga", "la-liga", ): "spain-la-liga",
        ('premier', 'premier-league', 'premierleague', ): "england-premier-league",
        ('seriea', 'serie-a', ): "italy-serie-a",
        ('bundesliga', 'bundes-liga', 'bundes', ): "germany-bundesliga",
        ('ligueone', 'ligue-one', 'ligue1', 'ligue-1', 'ligue', ): "france-ligue-1",
        ('segunda', 'segundadivision', 'segunda-division', 'laliga2', 'la-liga2', 'la-liga-2', 'hypermotion', 'la-liga-hypermotion', 'laligahypermotion', ): "spain-la-liga-2",
    }
    for keys, slug in mapping.items():
        for k in sorted(keys, key=len, reverse=True):  # longest first
            if k in s:
                return slug
    return ""


def get_sportsgambler_data(
        start_probability_file_name="sportsgambler_start_probabilities",
        force_scrape=False
):
    # If not forced to scrape, attempt to read from local file
    if not force_scrape:
        start_probabilities_data = read_dict_data(start_probability_file_name)

        if start_probabilities_data:
            return start_probabilities_data

    # Otherwise, scrape fresh data
    competition = competition_from_filename(start_probability_file_name)
    scraper = SportsgamblerScraper(competition=competition)
    start_probabilities_data = scraper.scrape()

    # Save to file for next time
    overwrite_dict_data(start_probabilities_data, start_probability_file_name, ignore_old_data=True)

    # return prices_data, positions_data, forms_data, start_probabilities_data, price_trends_data
    return start_probabilities_data


def get_players_start_probabilities_dict_sportsgambler(
        file_name="sportsgambler_start_probabilities",
        force_scrape=False
):
    if not force_scrape:
        data = read_dict_data(file_name)
        if data:
            return data

    competition = competition_from_filename(file_name)
    scraper = SportsgamblerScraper(competition=competition)
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
# start_probabilities = get_sportsgambler_data(
#     start_probability_file_name="test_sportsgambler_champions_players_start_probabilities",
#     force_scrape=True
# )
#
# print("\nStart Probabilities:")
# for team, players in start_probabilities.items():
#     print(team, players)
