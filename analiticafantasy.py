import os
import requests
import urllib3
from bs4 import BeautifulSoup
import json

from useful_functions import read_dict_data, overwrite_dict_data, find_manual_similar_string  # same as before


class AnaliticaFantasyScraper:
    def __init__(self):
        self.base_url = "https://www.analiticafantasy.com/la-liga/alineaciones-probables"
        self.session = requests.Session()
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/91.0.4472.124 Safari/537.36"
            )
        }

    def fetch_page(self, url):
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        response = self.session.get(url, headers=self.headers, timeout=15, verify=False)
        response.raise_for_status()
        return response.text

    def get_match_links(self, html):
        """
        From the Alineaciones Probables page, find all <a> with href
        that starts with '/partido/', like '/partido/1208772/alineaciones-probables'.
        Return the full absolute URLs.
        """
        soup = BeautifulSoup(html, "html.parser")
        links = []
        for a_tag in soup.find_all("a", href=True):
            if a_tag["href"].startswith("/partido/"):
                # Construct the full URL
                full_url = "https://www.analiticafantasy.com" + a_tag["href"]
                links.append(full_url)
        return links

    def parse_match_page(self, match_url):
        """
        Example logic: parse the match page’s JSON or HTML to extract the chance/team/player data.
        The actual parsing details depend on how the data appears in the HTML.
        """
        page_html = self.fetch_page(match_url)
        # For illustration: suppose a <script id="__NEXT_DATA__"> tag contains a JSON
        # structure with the players’ data. We find and parse it:
        soup = BeautifulSoup(page_html, "html.parser")
        script_tag = soup.find("script", id="__NEXT_DATA__")
        if not script_tag:
            return {}

        try:
            data_obj = json.loads(script_tag.string)
        except (json.JSONDecodeError, TypeError):
            return {}
        # print(data_obj)

        # Adjust this path depending on your actual JSON structure.
        # Suppose each player entry looks like:
        # {
        #   "team": { "name": "Valencia" },
        #   "information": { "name": "Player X" },
        #   "chance": 88,
        #   ...
        # }

        # Go into data_obj["props"]["pageProps"]["lineupsData"]
        lineups_data = (
            data_obj
            .get("props", {})
            .get("pageProps", {})
            .get("lineupsData", {})
        )

        # Safely extract home/away lineups
        home_players = lineups_data.get("homeLineup", {}).get("players", [])
        away_players = lineups_data.get("awayLineup", {}).get("players", [])
        all_chance_players = home_players + away_players

        match_dict = {}
        for chance_player in all_chance_players:
            # Example: chance=40, team->"name"="Valencia", information->"name"="Diakhaby"
            team_name = chance_player.get("team", {}).get("name", "").strip().title()
            team_name = find_manual_similar_string(team_name)
            player_name = chance_player.get("information", {}).get("name", "").strip().title()
            player_name = find_manual_similar_string(player_name)
            chance_int = chance_player.get("chance", 0)  # e.g. 40
    
            if team_name and player_name:
                # Convert to fraction, e.g. 40 -> 0.40
                chance_fraction = chance_int / 100.0
                # Insert into dictionary
                if team_name not in match_dict:
                    match_dict[team_name] = {}
                match_dict[team_name][player_name] = chance_fraction

        return match_dict

    def scrape_probabilities(self):
        """
        1) Grab the main page, find all partido links.
        2) For each match link, parse the chance / team / player data.
        3) Merge them all into a single dictionary.
        """
        main_html = self.fetch_page(self.base_url)
        match_links = self.get_match_links(main_html)

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


def get_analiticafantasy_data(
        start_probability_file_name="analiticafantasy_start_probabilities",
        force_scrape=False
):
    # If not forced to scrape, attempt to read from local file
    if not force_scrape:
        start_probabilities_data = read_dict_data(start_probability_file_name)

        if start_probabilities_data:
            return start_probabilities_data

    # Otherwise, scrape fresh data
    scraper = AnaliticaFantasyScraper()
    start_probabilities_data = scraper.scrape_probabilities()

    # Save to file for next time
    overwrite_dict_data(start_probabilities_data, start_probability_file_name)

    return start_probabilities_data


def get_players_start_probabilities_dict_extra(
        file_name="analiticafantasy_start_probabilities",
        force_scrape=False
):
    if not force_scrape:
        data = read_dict_data(file_name)
        if data:
            return data

    scraper = AnaliticaFantasyScraper()
    result = scraper.scrape_probabilities()

    overwrite_dict_data(result, file_name)

    return result


# # Example usage:
# data = get_analiticafantasy_data(
#     start_probability_file_name="test_analiticafantasy_laliga_players_start_probabilities",
#     force_scrape=False
# )
#
# print("Probabilities:")
# for team, players in data.items():
#     print(f"Team: {team}")
#     for player, chance in players.items():
#         print(f"    {player}: {chance}")
