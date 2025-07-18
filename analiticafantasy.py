import os
import requests
import urllib3
from bs4 import BeautifulSoup
import json

from useful_functions import read_dict_data, overwrite_dict_data, find_manual_similar_string  # same as before


class AnaliticaFantasyScraper:
    def __init__(self):
        self.base_url = "https://www.analiticafantasy.com/la-liga/alineaciones-probables"
        # self.base_url = "https://www.analiticafantasy.com/mundial-clubes/alineaciones-probables"
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

    def get_team_links(self, html):
        """
        From the Alineaciones Probables page, find all <a> with href
        that starts with '/equipo/', like '/equipo/real-madrid'.
        Return the full absolute URLs.
        """
        soup = BeautifulSoup(html, "html.parser")
        links = []
        for a_tag in soup.find_all("a", href=True):
            if a_tag["href"].startswith("/equipo/"):
                # Construct the full URL
                full_url = "https://www.analiticafantasy.com" + a_tag["href"]
                links.append(full_url)
        # # WE DO NOT USE THIS BECAUSE IT IS BETTER THE ORDER IT HAS IN THE HTML
        # links = sorted(
        #     list(set(links)),
        #     key=lambda u: int(u.split('/')[4])
        # )
        return links

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
        # # WE DO NOT USE THIS BECAUSE IT IS BETTER THE ORDER IT HAS IN THE HTML
        # links = sorted(
        #     list(set(links)),
        #     key=lambda u: int(u.split('/')[4])
        # )
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
            # .get("lineupsData", {})
            .get("lineupsResponse", {})
        )

        match_dict = {}
        match_dict["prices"] = {}
        match_dict["positions"] = {}
        match_dict["forms"] = {}
        match_dict["start_probabilities"] = {}
        match_dict["price_trends"] = {}

        # Safely extract home/away lineups
        for side_key in ["h", "a"]:
            team_data = lineups_data.get(side_key, {})
            team_name = team_data.get("n", None)
            team_name = find_manual_similar_string(team_name)
            players = team_data.get("l", [])

            for player in players:
                player_name = player.get("n", {}).strip().title()
                player_name = find_manual_similar_string(player_name)

                chance_int = player.get("c", None)  # e.g. 40
                chance_fraction = chance_int / 100.0 if chance_int else None  # Convert to fraction, e.g. 40 -> 0.40
                price = player.get("fmv", None)
                price_trend = player.get("fs", None)
                form = ((price / (price - price_trend)) - 1) * 100 if (price and price_trend and price != price_trend) else None
                position = None

                if team_name and player_name:
                    # Insert into dictionary
                    # if team_name not in match_dict:
                    #     match_dict[team_name] = {}
                    match_dict["prices"].setdefault(team_name, {})
                    match_dict["positions"].setdefault(team_name, {})
                    match_dict["forms"].setdefault(team_name, {})
                    match_dict["start_probabilities"].setdefault(team_name, {})
                    match_dict["price_trends"].setdefault(team_name, {})

                    # match_dict[team_name][player_name] = chance_fraction
                    match_dict["prices"][team_name][player_name] = price
                    match_dict["positions"][team_name][player_name] = position
                    match_dict["forms"][team_name][player_name] = form
                    match_dict["start_probabilities"][team_name][player_name] = chance_fraction
                    match_dict["price_trends"][team_name][player_name] = price_trend

        # home_players = lineups_data.get("homeLineup", {}).get("players", [])
        # away_players = lineups_data.get("awayLineup", {}).get("players", [])
        # all_chance_players = home_players + away_players
        #
        # match_dict = {}
        # for chance_player in all_chance_players:
        #     # Example: chance=40, team->"name"="Valencia", information->"name"="Diakhaby"
        #     team_name = chance_player.get("team", {}).get("name", "").strip().title()
        #     team_name = find_manual_similar_string(team_name)
        #     player_name = chance_player.get("information", {}).get("name", "").strip().title()
        #     player_name = find_manual_similar_string(player_name)
        #     chance_int = chance_player.get("chance", 0)  # e.g. 40
        #
        #     if team_name and player_name:
        #         # Convert to fraction, e.g. 40 -> 0.40
        #         chance_fraction = chance_int / 100.0
        #         # Insert into dictionary
        #         if team_name not in match_dict:
        #             match_dict[team_name] = {}
        #         match_dict[team_name][player_name] = chance_fraction

        return match_dict

    def scrape(self):
        """
        1) Grab the main page, find all partido links.
        2) For each match link, parse the chance / team / player data.
        3) Merge them all into a single dictionary.
        """
        main_html = self.fetch_page(self.base_url)

        prices_dict = {}
        positions_dict = {}
        forms_dict = {}
        price_trends_dict = {}
        probabilities_dict = {}

        team_links = self.get_team_links(main_html)
        for url in team_links:
            match_data = self.parse_match_page(url)
            # Merge match_data into probabilities_dict
            for team_name, players in match_data["prices"].items():
                if team_name not in prices_dict:
                    prices_dict[team_name] = {}
                for player_name, data_val in players.items():
                    prices_dict[team_name][player_name] = data_val
            for team_name, players in match_data["positions"].items():
                if team_name not in positions_dict:
                    positions_dict[team_name] = {}
                for player_name, data_val in players.items():
                    positions_dict[team_name][player_name] = data_val
            for team_name, players in match_data["forms"].items():
                if team_name not in forms_dict:
                    forms_dict[team_name] = {}
                for player_name, data_val in players.items():
                    forms_dict[team_name][player_name] = data_val
            for team_name, players in match_data["start_probabilities"].items():
                if team_name not in probabilities_dict:
                    probabilities_dict[team_name] = {}
                for player_name, data_val in players.items():
                    probabilities_dict[team_name][player_name] = data_val
            for team_name, players in match_data["price_trends"].items():
                if team_name not in price_trends_dict:
                    price_trends_dict[team_name] = {}
                for player_name, data_val in players.items():
                    price_trends_dict[team_name][player_name] = data_val

        match_links = self.get_match_links(main_html)
        for url in match_links:
            match_data = self.parse_match_page(url)
            # Merge match_data into probabilities_dict
            for team_name, players in match_data["prices"].items():
                if team_name not in prices_dict:
                    prices_dict[team_name] = {}
                for player_name, data_val in players.items():
                    prices_dict[team_name][player_name] = data_val
            for team_name, players in match_data["positions"].items():
                if team_name not in positions_dict:
                    positions_dict[team_name] = {}
                for player_name, data_val in players.items():
                    positions_dict[team_name][player_name] = data_val
            for team_name, players in match_data["forms"].items():
                if team_name not in forms_dict:
                    forms_dict[team_name] = {}
                for player_name, data_val in players.items():
                    forms_dict[team_name][player_name] = data_val
            for team_name, players in match_data["start_probabilities"].items():
                if team_name not in probabilities_dict:
                    probabilities_dict[team_name] = {}
                for player_name, data_val in players.items():
                    probabilities_dict[team_name][player_name] = data_val
            for team_name, players in match_data["price_trends"].items():
                if team_name not in price_trends_dict:
                    price_trends_dict[team_name] = {}
                for player_name, data_val in players.items():
                    price_trends_dict[team_name][player_name] = data_val

        return prices_dict, positions_dict, forms_dict, probabilities_dict, price_trends_dict


def get_analiticafantasy_data(
        price_file_name="analiticafantasy_prices",
        positions_file_name="analiticafantasy_positions",
        forms_file_name="analiticafantasy_forms",
        start_probability_file_name="analiticafantasy_start_probabilities",
        price_trends_file_name="analiticafantasy_price_trends",
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
    scraper = AnaliticaFantasyScraper()
    prices_data, positions_data, forms_data, start_probabilities_data, price_trends_data = scraper.scrape()

    # Save to file for next time
    overwrite_dict_data(prices_data, price_file_name)
    overwrite_dict_data(positions_data, positions_file_name)
    overwrite_dict_data(forms_data, forms_file_name)
    overwrite_dict_data(start_probabilities_data, start_probability_file_name)
    overwrite_dict_data(price_trends_data, price_trends_file_name)

    return prices_data, positions_data, forms_data, start_probabilities_data, price_trends_data


def get_players_prices_dict_analiticafantasy(
        file_name="analiticafantasy_prices",
        force_scrape=False
):
    if not force_scrape:
        data = read_dict_data(file_name)
        if data:
            return data

    scraper = AnaliticaFantasyScraper()
    result, _, _, _, _ = scraper.scrape()

    overwrite_dict_data(result, file_name)

    return result


def get_players_positions_dict_analiticafantasy(
        file_name="analiticafantasy_positions",
        force_scrape=False
):
    if not force_scrape:
        data = read_dict_data(file_name)
        # if data:
        return data

    scraper = AnaliticaFantasyScraper()
    _, result, _, _, _ = scraper.scrape()

    overwrite_dict_data(result, file_name)

    return result


def get_players_forms_dict_analiticafantasy(
        file_name="analiticafantasy_forms",
        force_scrape=False
):
    if not force_scrape:
        data = read_dict_data(file_name)
        if data:
            return data

    scraper = AnaliticaFantasyScraper()
    _, _, result, _, _ = scraper.scrape()

    overwrite_dict_data(result, file_name)

    return result


def get_players_start_probabilities_dict_analiticafantasy(
        file_name="analiticafantasy_start_probabilities",
        force_scrape=False
):
    if not force_scrape:
        data = read_dict_data(file_name)
        if data:
            return data

    scraper = AnaliticaFantasyScraper()
    _, _, _, result, _ = scraper.scrape()

    overwrite_dict_data(result, file_name)

    return result


def get_players_price_trends_dict_analiticafantasy(
        file_name="analiticafantasy_price_trends",
        force_scrape=False
):
    if not force_scrape:
        data = read_dict_data(file_name)
        if data:
            return data

    scraper = AnaliticaFantasyScraper()
    _, _, _, _, result = scraper.scrape()

    overwrite_dict_data(result, file_name)

    return result


# # Example usage:
# prices, positions, forms, start_probabilities, price_trends = get_analiticafantasy_data(
#     price_file_name="test_analiticafantasy_laliga_players_prices",
#     positions_file_name="test_analiticafantasy_laliga_players_positions",
#     forms_file_name="test_analiticafantasy_laliga_players_forms",
#     start_probability_file_name="test_analiticafantasy_laliga_players_start_probabilities",
#     price_trends_file_name="test_analiticafantasy_laliga_players_price_trends",
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
