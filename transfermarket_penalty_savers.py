import re
import requests
import tls_requests
from bs4 import BeautifulSoup
from datetime import datetime
import time
import os
import ast
from pprint import pprint

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
        soup = self.fetch_page(url, tries=5, pause=60.0)
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
                    # if team_name not in ["CA Osasuna", "Getafe CF", ]:
                    #     continue
                    team_link = a.get("href")
                    if team_name and team_link and "verein" in team_link:
                        team_links[team_name] = team_link
                idx += 1
        return team_links

    def get_goalkeeper_links(self, url):
        soup = self.fetch_page(url)
        player_links = {}
        if soup:
            players = soup.select("#yw1 table tbody tr td.posrela table tbody tr td a")
            if not players:
                players = soup.select("div.responsive-table div.grid-view table.items tbody tr td table.inline-table tr td.hauptlink a")
            positions = soup.select("#yw1 table tbody tr td.posrela table tbody tr td")
            if not positions:
                positions = soup.select("div.responsive-table div.grid-view table.items tbody tr td table.inline-table tr td")
            i = 0
            for player in players:
                player_name = player.text.strip()
                player_name = find_manual_similar_string(player_name)
                position_text = positions[i * 3 + 2].text.strip()
                url = player.get('href')
                if player_name and url and position_text:
                    if "Goalkeeper" in position_text:
                        player_links[player_name] = f"{self.base_url}{url}"
                i = i + 1
        return player_links

    def get_team_player_links(self, team_links):
        year = str(datetime.now().year - int(datetime.now() < datetime(datetime.now().year, 7, 1)))

        team_player_links = {}
        for team_name, team_suffix in team_links.items():
            # if team_name not in [
            #     "Chelsea FC",
            #     "CR Flamengo",
            #     "CF Monterrey",
            # ]:
            #     continue
            print('Extracting goalkeeper links from %s ...' % team_name)
            team_players_url = f"{self.base_url}/{team_suffix.split('/')[1]}/startseite/verein/{team_suffix.split('/')[4]}/plus/0?saison_id={year}"
            # team_players_url = f"{self.base_url}/{team_suffix.split('/')[1]}/kader/verein/{team_suffix.split('/')[4]}/saison_id/{year}/plus/1"
            team_player_links[team_name] = self.get_goalkeeper_links(team_players_url)
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

    def get_player_penalty_saves(self, url):
        penalty_saves_url = url.replace("/profil/", "/elfmeterstatistik/") + "/saison_id=2022//wettbewerb_id//plus/1#gehalten"
        soup = self.fetch_page(penalty_saves_url)
        penalty_saves = []
        if soup:
            for tr in soup.select("#yw1 table tbody tr"):
                is_penalty_saved = True
                minute_elem = tr.select_one("td:nth-of-type(8)")
                date_elem = tr.select_one("td:nth-of-type(4)")

                if minute_elem and date_elem:
                    minute_text = minute_elem.text.replace("'", "").strip()
                    if minute_text.isdigit():
                        # date_obj = datetime.strptime(date_elem.text.strip(), "%b %d, %Y")
                        date_obj = datetime.strptime(date_elem.text.strip(), "%d.%m.%Y")
                        penalty_saves.append({
                            'is_saved': is_penalty_saved,
                            'date': date_obj,
                            'minute': int(minute_text),
                        })
            for tr in soup.select("#yw2 table tbody tr"):
                is_penalty_saved = False
                minute_elem = tr.select_one("td:nth-of-type(8)")
                date_elem = tr.select_one("td:nth-of-type(4)")

                if minute_elem and date_elem:
                    minute_text = minute_elem.text.replace("'", "").strip()
                    if minute_text.isdigit():
                        # date_obj = datetime.strptime(date_elem.text.strip(), "%b %d, %Y")
                        date_obj = datetime.strptime(date_elem.text.strip(), "%d.%m.%Y")
                        penalty_saves.append({
                            'is_saved': is_penalty_saved,
                            'date': date_obj,
                            'minute': int(minute_text),
                        })
        penalty_saves.sort(key=lambda x: (x['date'], x['minute']), reverse=True)
        return penalty_saves

    def scrape(self):
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
                print('Extracting goalkeeper penalty saves from %s ...' % player_name)
                team_result[player_name] = self.get_player_penalty_saves(player_link)
                # break
            result[team_name] = team_result
        return result


def competition_from_filename(file_name: str) -> str:
    s = re.sub(r'[^a-z0-9]+', '-', file_name.lower())  # normalize to dashed tokens

    mapping = {
        ("mundialito", "club-world-cup", "clubworldcup", "mundial-clubes", "mundialclubes", ): "-/startseite/pokalwettbewerb/KLUB",
        ("champions", "championsleague", "champions-league"): "-/teilnehmer/pokalwettbewerb/CL",
        ('europaleague', 'europa-league', ): "-/teilnehmer/pokalwettbewerb/EL",
        ('conference', 'conferenceleague', 'conference-league', ): "-/teilnehmer/pokalwettbewerb/UCOL",
        ("eurocopa", "euro", "europa", "europeo", ): "-/teilnehmer/pokalwettbewerb/EURO",
        ("copaamerica", "copa-america", ): "-/teilnehmer/pokalwettbewerb/COPA",
        ("mundial", "worldcup", "world-cup", ): "-/teilnehmer/pokalwettbewerb/FIWC",
        ("laliga", "la-liga", ): "-/startseite/wettbewerb/ES1",
        ('premier', 'premier-league', 'premierleague', ): "-/startseite/wettbewerb/GB1",
        ('seriea', 'serie-a', ): "-/startseite/wettbewerb/IT1",
        ('bundesliga', 'bundes-liga', 'bundes', ): "-/startseite/wettbewerb/L1",
        ('ligueone', 'ligue-one', 'ligue1', 'ligue-1', 'ligue', ): "-/startseite/wettbewerb/FR1",
        ("segunda", "laliga2", "la-liga-2", "la-liga-hypermotion", "hypermotion", "laligahypermotion", ): "-/startseite/wettbewerb/ES2",
    }
    for keys, slug in mapping.items():
        for k in sorted(keys, key=len, reverse=True):  # longest first
            if k in s:
                return slug
    return "-/startseite/wettbewerb/ES1"


def get_penalty_savers_dict(
        write_file=True,
        file_name="transfermarket_laliga_penalty_savers",
        force_scrape=False
):
    if not force_scrape:
        data = read_dict_data(file_name)
        if data:
            return data

    competition = competition_from_filename(file_name)
    scraper = TransfermarktScraper(competition=competition)
    penalty_saves_data = scraper.scrape()

    filtered_penalty_saves_data = {}
    for team, player_data in penalty_saves_data.items():
        filtered_player_penalty_saves = {}
        for player_name, penalty_saves in player_data.items():
            filtered_penalty_saves = [team["is_saved"] for team in penalty_saves][:11]
            filtered_penalty_saves += [False] * (11 - len(filtered_penalty_saves))
            filtered_player_penalty_saves[player_name] = filtered_penalty_saves
        filtered_penalty_saves_data[team] = filtered_player_penalty_saves

    if write_file:
        # write_dict_data(filtered_penalty_saves_data, file_name):
        overwrite_dict_data(filtered_penalty_saves_data, file_name, ignore_valid_file=True)

    return filtered_penalty_saves_data


# goalkeepers_penalty_saves = get_penalty_savers_dict(
#     file_name="test_transfermarket_laliga_penalty_savers",
#     force_scrape=True
# )
#
# print(goalkeepers_penalty_saves)
# for team, goalkeepers_penalties in goalkeepers_penalty_saves.items():
#     print()
#     print(team)
#     for goalkeeper, penalty_saves in goalkeepers_penalties.items():
#         print(goalkeeper, penalty_saves)
