import os

import time
import pytz
import requests
import urllib3
from bs4 import BeautifulSoup
import json

from datetime import datetime, timezone
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC

from useful_functions import read_dict_data, overwrite_dict_data, find_manual_similar_string, \
    create_driver  # same as before


class JornadaPerfectaScraper:
    def __init__(self):
        # self.base_url = "https://www.jornadaperfecta.com/la-liga/onces-posibles/"
        # self.base_url = "https://www.jornadaperfecta.com/onces-posibles/"
        self.base_url = "https://www.jornadaperfecta.com/mundial-de-clubes/onces-posibles/"
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
        self.fetch_page(self.base_url)

        # 2) figure out which round to pick based on Europe/Madrid time
        cet = pytz.timezone("Europe/Madrid")
        now = datetime.now(cet)

        # thresholds are (round_value, cutoff_datetime)
        thresholds = [
            ("1", datetime(2025, 6, 15, 2,  0, tzinfo=cet)),
            ("2", datetime(2025, 6, 19, 18, 0, tzinfo=cet)),
            ("3", datetime(2025, 6, 23, 21, 0, tzinfo=cet)),
            ("4", datetime(2025, 6, 28, 18, 0, tzinfo=cet)),
            ("5", datetime(2025, 7,  4, 21, 0, tzinfo=cet)),
            ("6", datetime(2025, 7,  8, 21, 0, tzinfo=cet)),
            ("7", datetime(2025, 7, 13, 21, 0, tzinfo=cet)),
        ]

        round_to_select = None
        for val, cutoff in thresholds:
            if now < cutoff:
                round_to_select = val
                break

        # 3) if we found one, click the dropdown and select it
        if round_to_select:
            select_el = self.wait.until(
                EC.element_to_be_clickable((By.ID, "roundSelect"))
            )
            select = Select(select_el)
            select.select_by_value(round_to_select)

            # wait for the new content to load (adjust timeout or condition as needed)
            self.wait.until(
                EC.presence_of_all_elements_located(
                    (By.CSS_SELECTOR, "a.clean-link.match-link.current-round-content")
                )
            )
        # else: no round selected, just use whatever initial page gave us

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
        for team_block in soup.find_all(class_="partido-posible-alineacion"):
            # Extract and clean team name
            full_text = team_block.get_text(separator=" ", strip=True)
            # Assumes text starts with "Alineación Posible <TeamName>"
            team_name = full_text.replace("Alineación Posible ", "").strip().title()
            team_name = find_manual_similar_string(team_name)

            players = {}
            # climb up two levels: h2 → div → div
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

        return lineup_data

    def scrape_probabilities(self):
        """
        1) Grab the main page, find all partido links.
        2) For each match link, parse the chance / team / player data.
        3) Merge them all into a single dictionary.
        """
        match_links = self.get_match_links()

        probabilities_dict = {}
        for url in match_links:
            match_data = self.parse_match_page(url)
            # Merge match_data into probabilities_dict
            for team_name, players in match_data.items():
                if team_name not in probabilities_dict:
                    probabilities_dict[team_name] = {}
                for player_name, chance_val in players.items():
                    probabilities_dict[team_name][player_name] = chance_val

        return probabilities_dict


def get_jornadaperfecta_data(
        start_probability_file_name="jornadaperfecta_start_probabilities",
        force_scrape=False
):
    # If not forced to scrape, attempt to read from local file
    if not force_scrape:
        start_probabilities_data = read_dict_data(start_probability_file_name)

        if start_probabilities_data:
            return start_probabilities_data

    # Otherwise, scrape fresh data
    scraper = JornadaPerfectaScraper()
    start_probabilities_data = scraper.scrape_probabilities()

    # Save to file for next time
    overwrite_dict_data(start_probabilities_data, start_probability_file_name)

    return start_probabilities_data


def get_players_start_probabilities_dict_jornadaperfecta(
        file_name="jornadaperfecta_start_probabilities",
        force_scrape=False
):
    if not force_scrape:
        data = read_dict_data(file_name)
        if data:
            return data

    scraper = JornadaPerfectaScraper()
    result = scraper.scrape_probabilities()

    overwrite_dict_data(result, file_name)

    return result


# # Example usage:
# data = get_jornadaperfecta_data(
#     start_probability_file_name="test_jornadaperfecta_mundialito_players_start_probabilities",
#     force_scrape=True
# )
#
# print("Probabilities:")
# for team, players in data.items():
#     print(f"Team: {team}")
#     for player, chance in players.items():
#         print(f"    {player}: {chance}")
