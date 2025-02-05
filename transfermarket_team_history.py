import requests
from bs4 import BeautifulSoup
from datetime import datetime
import os
import ast

from useful_functions import write_dict_data, read_dict_data, overwrite_dict_data, find_manual_similar_string

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))  # This is your Project Root


class TransfermarktScraper:
    def __init__(self):
        self.base_url = 'https://www.transfermarkt.com'
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

    def fetch_page(self, url):
        response = requests.get(url, headers=self.headers)
        if response.status_code == 200:
            return BeautifulSoup(response.content, 'html.parser')
        else:
            return None

    def get_team_links(self, url):
        soup = self.fetch_page(url)
        team_links = {}
        if soup:
            teams = soup.select("#yw1 table tbody tr td a")
            for team in teams:
                link = team.get('href')
                title = team.get('title')
                if title and link:
                    team_links[title] = link
        return team_links

    def get_player_links(self, url):
        soup = self.fetch_page(url)
        player_links = {}
        if soup:
            players = soup.select("#yw1 table tbody tr td.posrela a")
            if not players:
                players = soup.select("div.responsive-table div.grid-view table.items tbody tr td table.inline-table tr td.hauptlink a")
            for player in players:
                name = player.text.strip()
                url = player.get('href')
                if name and url:
                    player_links[name] = f"{self.base_url}{url}"
        return player_links

    def get_team_player_links(self, team_links):
        year = str(datetime.now().year - int(datetime.now() < datetime(datetime.now().year, 7, 1)))

        team_player_links = {}
        for team_name, team_suffix in team_links.items():
            print('Extracting players links from %s ...' % team_name)
            team_players_url = f"{self.base_url}/{team_suffix.split('/')[1]}/startseite/verein/{team_suffix.split('/')[4]}/plus/0?saison_id={year}"
            team_player_links[team_name] = self.get_player_links(team_players_url)
            # break

        return team_player_links

    def get_team_country(self, url):
        soup = self.fetch_page(url)
        if soup:
            meta_tag = soup.find('meta', attrs={'name': 'keywords'})
            if meta_tag:
                content = meta_tag.get('content', '')
                country = content.split(',')[-1].strip()
                return country
        return None

    def get_player_team_history(self, url, use_country_as_team=False):
        transfers_url = url.replace("/profil/", "/leistungsdatenverein/")
        soup = self.fetch_page(transfers_url)
        team_history = []
        if soup:
            team_entries = soup.select("#yw1 table tbody tr")
            for entry in team_entries:
                team_data = entry.select("td")
                if team_data:
                    team_name = team_data[1].text.strip()
                    team_url = f"{self.base_url}{team_data[1].find('a')['href']}"
                    if use_country_as_team:
                        team_country = self.get_team_country(team_url)
                        team_name = team_country
                    appearances = team_data[2].text.replace("-", "0").strip()
                    goals = team_data[4].text.replace("-", "0").strip()
                    minutes = team_data[-1].text.replace("-", "0").replace("'", "").replace(".", "").strip()

                    if team_name:# and minutes:
                        team_info = {
                            "name": team_name,
                            "url": team_url,
                            # "country": team_country,
                            "appearances": int(appearances),
                            "goals": int(goals),
                            "minutes": int(minutes),
                        }
                        team_history.append(team_info)
        return team_history

    def scrape(self, use_country_as_team=False):
        result = {}
        league_url = "https://www.transfermarkt.com/laliga/startseite/wettbewerb/ES1"
        # league_url = "https://www.transfermarkt.com/europameisterschaft-2024/teilnehmer/pokalwettbewerb/EM24/saison_id/2023"
        # league_url = "https://www.transfermarkt.com/copa-america-2024/teilnehmer/pokalwettbewerb/CAM4/saison_id/2023"
        team_links = self.get_team_links(league_url)
        team_player_links = self.get_team_player_links(team_links)
        print()
        for team_name, player_links in team_player_links.items():
            team_result = {}
            for player_name, player_link in player_links.items():
                player_name = find_manual_similar_string(player_name)
                print('Extracting player team history from %s ...' % player_name)
                team_result[player_name] = self.get_player_team_history(player_link, use_country_as_team)
                # break
            result[team_name] = team_result
        return result


def get_players_team_history_dict(
        write_file=True,
        file_name="transfermarket_laliga_team_history",
        use_country_as_team=False,
        force_scrape=False
):
    if not force_scrape:
        data = read_dict_data(file_name)
        if data:
            return data

    scraper = TransfermarktScraper()
    team_history_data = scraper.scrape(use_country_as_team)

    filtered_team_history_data = {}
    for team, player_data in team_history_data.items():
        filtered_player_team_history = {}
        for player_name, team_history in player_data.items():
            filtered_team_history = [team["name"] for team in team_history] # if team["minutes"] > 0]
            filtered_player_team_history[player_name] = filtered_team_history
        filtered_team_history_data[team] = filtered_player_team_history

    if write_file:
        # write_dict_data(filtered_team_history_data, file_name):
        overwrite_dict_data(filtered_team_history_data, file_name)

    return filtered_team_history_data


# players_team_history = get_players_team_history_dict(
#     file_name="transfermarket_laliga_team_history",
#     use_country_as_team=False,
#     force_scrape=True
# )
#
# print(players_team_history)
# for team, players in players_team_history.items():
#     print()
#     print(team)
#     for player, team_history in players.items():
#         print(player, team_history)
