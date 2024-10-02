import requests
from bs4 import BeautifulSoup
from datetime import datetime
import os
import ast

from useful_functions import write_dict_to_csv, read_dict_from_csv, overwrite_dict_to_csv

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
                name = player.text.strip()
                position_text = positions[i * 3 + 2].text.strip()
                url = player.get('href')
                if name and url and position_text:
                    if "Goalkeeper" in position_text:
                        player_links[name] = f"{self.base_url}{url}"
                i = i + 1
        return player_links

    def get_team_player_links(self, team_links):
        year = str(datetime.now().year - int(datetime.now() < datetime(datetime.now().year, 7, 1)))

        team_player_links = {}
        for team_name, team_suffix in team_links.items():
            print('Extracting goalkeeper links from %s ...' % team_name)
            team_players_url = f"{self.base_url}/{team_suffix.split('/')[1]}/startseite/verein/{team_suffix.split('/')[4]}/plus/0?saison_id={year}"
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
                        date_obj = datetime.strptime(date_elem.text.strip(), "%b %d, %Y")
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
                        date_obj = datetime.strptime(date_elem.text.strip(), "%b %d, %Y")
                        penalty_saves.append({
                            'is_saved': is_penalty_saved,
                            'date': date_obj,
                            'minute': int(minute_text),
                        })
        penalty_saves.sort(key=lambda x: (x['date'], x['minute']), reverse=True)
        return penalty_saves

    def scrape(self):
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
                if player_name == "Alfonso Espino":
                    player_name = "Pacha Espino"
                if player_name == "Abderrahman Rebbach":
                    player_name = "Abde Rebbach"
                if player_name == "Peter González" or player_name == "Peter Gonzales":
                    player_name = "Peter Federico"
                if player_name == "Abde Ezzalzouli" or player_name == "Abdessamad Ezzalzouli":
                    player_name = "Ez Abde"
                if player_name == "Ismaila Ciss":
                    player_name = "Pathé Ciss"
                if player_name == "Chuky":
                    player_name = "Chuki"
                if player_name == "Malcom Ares":
                    player_name = "Adu Ares"
                if player_name == "William Carvalho":
                    player_name = "Carvalho"
                if player_name == "Fabio González":
                    player_name = "Fabio"
                if player_name == "Jonathan Montiel":
                    player_name = "Joni Montiel"
                if player_name == "Manuel Fuster" or player_name == "Manu Fuster":
                    player_name = "Fuster"
                if player_name == "Jon Magunazelaia":
                    player_name = "Magunacelaya"
                if player_name == "Álvaro Aguado":
                    player_name = "Aguado"
                print('Extracting goalkeeper penalty saves from %s ...' % player_name)
                team_result[player_name] = self.get_player_penalty_saves(player_link)
                # break
            result[team_name] = team_result
        return result


def get_penalty_savers_dict(
        write_file=True,
        file_name="transfermarket_laliga_penalty_savers",
        force_scrape=False
):
    if not force_scrape:
        if os.path.isfile(ROOT_DIR + '/csv_files/' + file_name + '.csv'):
            data = read_dict_from_csv(file_name)
            return data

    scraper = TransfermarktScraper()
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
        # write_dict_to_csv(filtered_penalty_saves_data, file_name):
        overwrite_dict_to_csv(filtered_penalty_saves_data, file_name, ignore_valid_file=True)

    return filtered_penalty_saves_data


# goalkeepers_penalty_saves = get_penalty_savers_dict(
#     file_name="transfermarket_laliga_penalty_savers",
#     force_scrape=True
# )
#
# print(goalkeepers_penalty_saves)
# for team, goalkeepers_penalties in goalkeepers_penalty_saves.items():
#     print()
#     print(team)
#     for goalkeeper, penalty_saves in goalkeepers_penalties.items():
#         print(goalkeeper, penalty_saves)
