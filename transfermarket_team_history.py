import re
import requests
import tls_requests
from bs4 import BeautifulSoup
from datetime import datetime
import time
import os
import ast

from useful_functions import write_dict_data, read_dict_data, overwrite_dict_data, find_manual_similar_string

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))  # This is your Project Root


class TransfermarktScraper:
    def __init__(self, competition: str = None):
        self.base_url = 'https://www.transfermarkt.com'
        self.competition =  (
            competition
            if competition is not None
            else "-/startseite/wettbewerb/ES1"
        )
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

    def fetch_page(self, url, tries: int = 3, pause: float = 20.0):
        """
        Fetch a URL, retrying up to `tries` times if the status is not 200.
        Sleeps `pause` seconds between attempts.
        Returns a BeautifulSoup on success, or None if all attempts fail.
        """
        # response = requests.get(url, headers=self.headers)
        for attempt in range(1, tries + 1):
            try:
                response = tls_requests.get(url, headers=self.headers)
            except Exception as e:
                # network-level error; count it as a failed attempt
                print(f"Attempt {attempt}/{tries} failed with exception: {e!r} ({url})")
            else:
                if response.status_code == 200:
                    return BeautifulSoup(response.content, 'html.parser')
                else:
                    print(f"Attempt {attempt}/{tries} returned status {response.status_code} ({url})")
            if attempt < tries:
                time.sleep(pause)
        # all attempts exhausted
        return None

    def get_team_links(self, url):
        soup = self.fetch_page(url)
        team_links = {}
        if soup:
            idx = 1
            while idx < 20:
                block_id = f"yw{idx}"
                selector = f"#{block_id} table tbody tr td a"
                teams = soup.select(selector)
                if not teams:
                    break
                for a in teams:
                    team_name = a.get("title")
                    team_name = find_manual_similar_string(team_name)
                    team_link = a.get("href")
                    if team_name and team_link and "verein" in team_link:
                        team_links[team_name] = team_link
                idx += 1
        return team_links

    def get_player_links(self, url):
        soup = self.fetch_page(url, pause=60.0)
        player_links = {}
        if soup:
            players = soup.select("#yw1 table tbody tr td.posrela a")
            if not players:
                players = soup.select("div.responsive-table div.grid-view table.items tbody tr td table.inline-table tr td.hauptlink a")
            for player in players:
                player_name = player.text.strip()
                player_name = find_manual_similar_string(player_name)
                url = player.get('href')
                if player_name and url:
                    player_links[player_name] = f"{self.base_url}{url}"
        return player_links

    def get_team_player_links(self, team_links):
        year = str(datetime.now().year - int(datetime.now() < datetime(datetime.now().year, 7, 1)))

        team_player_links = {}
        for team_name, team_suffix in team_links.items():
            # if team_name not in [
            #     'Inter',
            #     'Ulsan HD FC',
            #     'Juventus FC',
            #     'Al-Ain FC',
            #     'Wydad Casablanca',
            # ]:
            #     continue
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
                country = find_manual_similar_string(country)
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
                    team_name = find_manual_similar_string(team_name)
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
        # # league_url = f"{self.base_url}/fifa-club-world-cup/startseite/pokalwettbewerb/KLUB"
        # league_url = f"{self.base_url}/laliga/startseite/wettbewerb/ES1"
        # # league_url = "https://www.transfermarkt.com/europameisterschaft-2024/teilnehmer/pokalwettbewerb/EM24"
        # # league_url = f"{self.base_url}/copa-america-2024/teilnehmer/pokalwettbewerb/CAM4"
        league_url = f"{self.base_url}/{self.competition}"
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


def competition_from_filename(file_name: str) -> str:
    s = re.sub(r'[^a-z0-9]+', '-', file_name.lower())  # normalize to dashed tokens

    mapping = {
        ("mundialito", "club-world-cup", "clubworldcup", "mundial-clubes", "mundialclubes", ): "-/startseite/pokalwettbewerb/KLUB",
        ("champions", "championsleague", "champions-league"): "-/teilnehmer/pokalwettbewerb/CL",
        ("eurocopa", "euro", "europa", "europeo", ): "-/teilnehmer/pokalwettbewerb/EURO",
        ("copaamerica", "copa-america", ): "-/teilnehmer/pokalwettbewerb/COPA",
        ("mundial", "worldcup", "world-cup", ): "-/teilnehmer/pokalwettbewerb/FIWC",
        ("laliga", "la-liga", ): "-/startseite/wettbewerb/ES1",
        ('premier', 'premier-league', ): "-/startseite/wettbewerb/GB1",
        ('seriea', 'serie-a', ): "-/startseite/wettbewerb/IT1",
        ('bundesliga', 'bundes-liga', ): "-/startseite/wettbewerb/L1",
        ('ligueone', 'ligue-one', 'ligue1', 'ligue-1', 'ligue', ): "-/startseite/wettbewerb/FR1",
        ("segunda", "laliga2", "la-liga-2", "la-liga-hypermotion", "hypermotion", "laligahypermotion", ): "-/startseite/wettbewerb/ES2",
    }
    for keys, slug in mapping.items():
        for k in sorted(keys, key=len, reverse=True):  # longest first
            if k in s:
                return "/" + slug if slug else slug
    return "-/startseite/wettbewerb/ES1"


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

    competition = competition_from_filename(file_name)
    scraper = TransfermarktScraper(competition=competition)
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
#     file_name="test_transfermarket_laliga_team_history",
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
